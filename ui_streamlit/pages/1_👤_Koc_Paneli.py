# --- Path bootstrap (pages klasöründeyiz) ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports ---
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from core.dataio import (
    load_settings, level_to_col, load_topics,
    load_students, add_student
)
from core.assignments import (
    week_start_of, get_assignments, add_assignments, update_status
)
from core.resources import get_resources

# --- Stil ---
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }
section[data-testid="stSidebar"] .stButton>button { width: 100%; }
.stProgress > div > div { transition: width .25s ease; }
.goal-chip { background:#111827; border:1px solid #2a2f3a; padding:.35rem .55rem; border-radius:.6rem; display:inline-block; margin:.12rem .22rem; }
.card { border:1px solid #2a2f3a; border-radius:12px; padding:12px 16px; margin:8px 0; }
.card .title { font-weight:600; font-size:1.05rem; margin-bottom:4px; }
.card .meta { opacity:.85; margin-bottom:6px; }
.group-head { font-weight:600; margin:4px 0 2px; }
.help-meta { opacity:.85; font-size:.92rem; margin-bottom:6px; }
.item-meta { opacity:.85; font-size:.92rem; }
</style>
""", unsafe_allow_html=True)

st.title("👤 Koç Paneli")

# ---- Flash mesajı ----
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# -----------------------------
# Sol kenar: Öğrenci
# -----------------------------
st.sidebar.header("Öğrenciler")
with st.sidebar.expander("➕ Yeni Öğrenci Ekle"):
    new_name = st.text_input("Ad Soyad", key="new_student_name")
    if st.button("Ekle", key="btn_add_student"):
        try:
            sid = add_student(new_name)
            st.session_state["flash"] = f"Öğrenci eklendi: {new_name} (ID: {sid})"
            st.rerun()
        except Exception as e:
            st.error(str(e))

students = load_students()
students = students[students["active"] == True].copy()
if students.empty:
    st.warning("Aktif öğrenci yok. Lütfen **Öğrenci Yönetimi** sayfasından öğrenci ekleyin/aktif edin.")
    st.stop()

student_name_to_id = {row.student_name: int(row.student_id) for _, row in students.iterrows()}
student_name = st.sidebar.selectbox("Öğrenci seç", list(student_name_to_id.keys()))
student_id = student_name_to_id[student_name]

# -----------------------------
# Tarih / Hafta
# -----------------------------
bugun = date.today()
secili_tarih = st.date_input("Tarih", value=bugun)      # bugün gelir
hafta_baslangic = week_start_of(secili_tarih)           # seçilen tarihin haftası
hafta_bitis = hafta_baslangic + timedelta(days=6)
st.caption(f"Hafta aralığı: {hafta_baslangic} — {hafta_bitis}")

# -----------------------------
# Yardımcı formatlayıcılar
# -----------------------------
TYPE_ORDER = {"Video": 0, "Dakika": 1, "Soru": 2}   # Video üstte, Soru en altta
TYPE_ICON  = {"Video": "🎬", "Dakika": "⏱️", "Soru": "📝"}

def fmt_minutes(m: int) -> str:
    m = int(m)
    h = m // 60
    r = m % 60
    if h and r:  return f"{h}s {r}dk"
    if h and not r: return f"{h}s"
    return f"{r}dk"

def fmt_amount(birim: str, miktar: int) -> str:
    if birim == "Dakika":
        return fmt_minutes(miktar)
    if birim == "Soru":
        return f"{int(miktar)} Soru"
    if birim == "Video":
        return f"{int(miktar)} Video"
    return str(miktar)

# -----------------------------
# BU HAFTANIN HEDEFLERİ
# -----------------------------
st.subheader("✅ Bu Haftanın Hedefleri")

df_assign = get_assignments(student_id, hafta_baslangic).sort_values(["ders","birim","konu","kaynak"])

if df_assign.empty:
    st.info("Bu hafta için hedef atanmadı. Aşağıdan **Yeni Hedef Ekle** kısmını kullan.")
else:
    # Ders bazında
    for ders_ad, df_ders in df_assign.groupby("ders", sort=False):
        toplam = len(df_ders)
        tamam = int(df_ders["durum"].sum())
        pct = int(round(100 * (tamam / toplam))) if toplam else 0

        with st.expander(f"{ders_ad} — {tamam}/{toplam} (%{pct})", expanded=True):
            # Tür bazında sıralı gösterim: Video → Dakika → Soru
            for tur, df_tur in sorted(df_ders.groupby("birim"), key=lambda kv: TYPE_ORDER.get(kv[0], 99)):
                icon = TYPE_ICON.get(tur, "📌")
                t_toplam = len(df_tur)
                t_tamam = int(df_tur["durum"].sum())
                t_pct = int(round(100 * (t_tamam / t_toplam))) if t_toplam else 0

                st.markdown(f"<div class='group-head'>{icon} {tur}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='help-meta'>{t_tamam}/{t_toplam} (%{t_pct})</div>", unsafe_allow_html=True)
                st.progress(t_pct)

                # Öğeler
                for idx, row in df_tur.iterrows():
                    key = f"chk|{student_id}|{hafta_baslangic}|{ders_ad}|{row.konu}|{row.birim}|{row.kaynak}|{idx}"
                    # Etiket iki satır: 1) Konu  2) hedef + kaynak
                    hedef_str = fmt_amount(row.birim, row.miktar)
                    alt = f"🎯 hedef: {hedef_str}"
                    if str(row.kaynak).strip():
                        alt += f"  •  📚 {row.kaynak}"

                    cols = st.columns([0.08, 0.92])
                    with cols[0]:
                        done = st.checkbox("", value=bool(row.durum), key=key)
                    with cols[1]:
                        st.markdown(f"**{row.konu}**  \n<span class='item-meta'>{alt}</span>",
                                    unsafe_allow_html=True)

                    if done != bool(row.durum):
                        update_status(student_id, hafta_baslangic, ders_ad, row.konu, done,
                                      birim=row.birim, kaynak=row.kaynak)
                        # anında görsel güncelleme + rerun
                        mask = (
                            (df_assign["ders"] == ders_ad) &
                            (df_assign["konu"] == row.konu) &
                            (df_assign["birim"] == row.birim) &
                            (df_assign["kaynak"].fillna("") ==
                             (row.kaynak if pd.notna(row.kaynak) else ""))
                        )
                        df_assign.loc[mask, "durum"] = bool(done)
                        st.session_state["flash"] = f"Güncellendi: {ders_ad} / {row.konu} [{row.birim}] → {'✓' if done else '✗'}"
                        st.rerun()

        st.progress(pct)

    # küçük ders özeti chip'leri
    st.caption("Bu haftanın ders bazında görev sayıları")
    chips = []
    for d, sub in df_assign.groupby("ders"):
        count = len(sub)
        chips.append(f"<span class='goal-chip'>{d}: {count} görev</span>")
    st.markdown(" ".join(chips), unsafe_allow_html=True)

# -----------------------------
# YENİ HEDEF EKLE
# -----------------------------
st.subheader("➕ Yeni Hedef Ekle")

settings = load_settings()
level_col = level_to_col(settings["level"])
topics = load_topics(level_col)

dersler_list = topics["subject"].unique().tolist()
ders = st.selectbox("Ders", dersler_list)
konular = st.multiselect("Konular", topics[topics["subject"] == ders]["topic"].tolist())

col_a, col_b = st.columns(2)
with col_a:
    birim = st.selectbox("Görev türü", ["Dakika", "Soru", "Video"], index=0)
with col_b:
    if birim == "Dakika":
        miktar = st.number_input("Dakika", min_value=5, max_value=600, value=90, step=5)
    elif birim == "Soru":
        miktar = st.number_input("Soru sayısı", min_value=1, max_value=2000, value=20, step=5)
    else:
        miktar = st.number_input("Video adedi", min_value=1, max_value=200, value=1, step=1)

kaynak = ""
if birim in ("Soru", "Video"):
    res_df = get_resources(subject=ders, type_=birim)
    names = ["(Seçiniz)"] + (res_df["name"].tolist() if not res_df.empty else []) + ["(Elle yaz)"]
    choice = st.selectbox("Kaynak", names, index=0)
    if choice == "(Elle yaz)":
        kaynak = st.text_input("Kaynak adı", placeholder="Örn: X Yayınları TYT Türkçe SB")
    elif choice != "(Seçiniz)":
        kaynak = choice

if st.button("Hedefleri Ekle", type="primary"):
    if not konular:
        st.warning("En az bir konu seç.")
    else:
        add_assignments(
            student_id=student_id,
            week_start=hafta_baslangic,
            ders=ders,
            konular=konular,
            birim=birim,
            miktar=int(miktar),
            kaynak=kaynak
        )
        st.session_state["flash"] = "Hedef(ler) eklendi."
        st.rerun()

# -----------------------------
# ÖNERİLEN KAYNAKLAR – hızlı ödevlendirme
# -----------------------------
st.subheader("📚 Önerilen Kaynaklar")

areas = ["Genel", "Paragraf", "Dil Bilgisi"]
levels = ["Başlangıç", "Orta", "İleri"]

colr1, colr2 = st.columns(2)
with colr1:
    oner_kat = st.selectbox("Kategori", areas, index=0, key="rec_area")
with colr2:
    oner_sev = st.selectbox("Seviye", levels, index=1, key="rec_level")

rec_df = get_resources(subject=ders, area=oner_kat, difficulty=oner_sev)
if rec_df.empty:
    st.info("Bu filtreyle eşleşen kaynak bulunamadı.")
else:
    names = rec_df["name"].tolist()
    secilen_idx = st.selectbox("Kaynak seç", options=list(range(len(names))),
                               format_func=lambda i: names[i], key="rec_pick")
    secilen = rec_df.iloc[secilen_idx]

    st.markdown(
        f"<div class='card'><div class='title'>{secilen['name']}</div>"
        f"<div class='meta'>Tür: <b>{secilen['type']}</b> • Kategori: <b>{secilen['area']}</b> • "
        f"Seviye: <b>{secilen['difficulty']}</b></div>"
        f"<div>{secilen['notes']}</div></div>",
        unsafe_allow_html=True
    )

    # kategoriye göre varsayılan konu önerileri
    all_topics = topics[topics["subject"] == ders]["topic"].tolist()
    if oner_kat == "Paragraf":
        default_topics = [t for t in all_topics if "Paragraf" in t][:1]
    elif oner_kat == "Dil Bilgisi":
        grammar_keys = ["Ses Bilgisi","Yazım Kuralları","Noktalama","Sözcük Yapısı",
                        "İsim Soylu","Fiiller","Cümlenin Ögeleri","Cümle Çeşitleri","Anlatım Bozukluğu"]
        default_topics = [t for t in all_topics if any(k in t for k in grammar_keys)]
    else:
        default_topics = all_topics

    hedef_konular = st.multiselect(
        "Bu kaynaktan ödevlenecek konular",
        all_topics,
        default=default_topics[:3],
        key="rec_topics"
    )

    if secilen["type"] == "Soru":
        rec_miktar = st.number_input("Soru sayısı", min_value=5, max_value=500, value=40, step=5, key="rec_qty")
        rec_birim = "Soru"
    else:
        rec_miktar = st.number_input("Video adedi", min_value=1, max_value=50, value=1, step=1, key="rec_qty")
        rec_birim = "Video"

    if st.button("➕ Bu kaynaktan hedef oluştur", type="primary", key="rec_add_btn"):
        if not hedef_konular:
            st.warning("En az bir konu seç.")
        else:
            add_assignments(
                student_id=student_id,
                week_start=hafta_baslangic,
                ders=ders,
                konular=hedef_konular,
                birim=rec_birim,
                miktar=int(rec_miktar),
                kaynak=str(secilen["name"])
            )
            st.success("Hedef(ler) eklendi.")
            st.rerun()

with st.expander("ℹ️ Notlar"):
    st.write("""
- Görevler **ders → tür (🎬 Video → ⏱️ Dakika → 📝 Soru)** şeklinde gruplanır.
- Dakika miktarları saat/dakika biçiminde gösterilir (örn. 150 dk → 2s 30dk).
- Önerilen Kaynaklar bölümünden kategori/seviye filtreleriyle **tek tıkla** hedef atayabilirsin.
""")
