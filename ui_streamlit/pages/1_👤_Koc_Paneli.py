# --- Path bootstrap (pages içinde olduğumuz için parent.parent) ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date
import pandas as pd
import streamlit as st

from core.dataio import load_settings, level_to_col, load_topics, load_students, add_student
from core.assignments import week_start_of, get_assignments, add_assignments, update_status
from core.resources import get_resources

# --- Basit stil dokunuşları (set_page_config ANA sayfada) ---
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }
section[data-testid="stSidebar"] .stButton>button { width: 100%; }
.stProgress > div > div { transition: width .25s ease; }
.goal-chip { background:#111827; border:1px solid #2a2f3a; padding:.35rem .55rem; border-radius:.6rem; display:inline-block; margin:.12rem .22rem; }
</style>
""", unsafe_allow_html=True)

st.title("👤 Koç Paneli")

# ---- Flash (işlem sonrası kısa mesaj) ----
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# ---- Sol kenar: Öğrenci seç + Hızlı ekle ----
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

# ---- Hafta seçimi ----
today = date.today()
hafta_baslangic_input = st.date_input("Hafta başlangıcı (Pazartesi)", value=week_start_of(today))
hafta_baslangic = week_start_of(hafta_baslangic_input)  # güvence: Pazartesi

# ---- Yardımcı: satır etiketi ---
def _format_row_label(row) -> str:
    src = f" (kaynak: {row.kaynak})" if str(row.kaynak).strip() else ""
    return f"{row.konu} — hedef: {row.miktar} {row.birim}{src}"

# ---- Bu haftanın hedefleri ----
st.subheader("✅ Bu Haftanın Hedefleri")

df_assign = get_assignments(student_id, hafta_baslangic).sort_values(
    ["ders","konu","birim","kaynak"]
)

if df_assign.empty:
    st.info("Bu hafta için hedef atanmadı. Aşağıdan **Yeni Hedef Ekle** kısmını kullan.")
else:
    dersler = df_assign["ders"].unique().tolist()
    for d in dersler:
        sub = df_assign[df_assign["ders"] == d].copy()
        toplam = len(sub)
        tamam = int(sub["durum"].sum())
        pct = int(round(100 * (tamam / toplam))) if toplam else 0

        with st.expander(f"{d}  —  {tamam}/{toplam}  (%{pct})", expanded=True):
            for idx, row in sub.iterrows():
                # BENZERSİZ KEY: ders+konu+birim+kaynak+idx
                key = f"chk|{student_id}|{hafta_baslangic}|{d}|{row.konu}|{row.birim}|{row.kaynak}|{idx}"
                done = st.checkbox(_format_row_label(row), value=bool(row.durum), key=key)
                if done != bool(row.durum):
                    # 1) Dosyada yalnızca ilgili satırı güncelle
                    update_status(
                        student_id, hafta_baslangic, d, row.konu, done,
                        birim=row.birim, kaynak=row.kaynak
                    )
                    # 2) Ekrandaki tabloyu anında güncelle + rerun
                    mask = (
                        (df_assign["ders"] == d) &
                        (df_assign["konu"] == row.konu) &
                        (df_assign["birim"] == row.birim) &
                        (df_assign["kaynak"].fillna("") ==
                         (row.kaynak if pd.notna(row.kaynak) else ""))
                    )
                    df_assign.loc[mask, "durum"] = bool(done)
                    st.session_state["flash"] = f"Güncellendi: {d} / {row.konu} [{row.birim}] → {'✓' if done else '✗'}"
                    st.rerun()
        st.progress(pct)

    # hızlı özet chip'leri
    st.caption("Bu haftanın görev sayıları")
    chips = []
    for d in dersler:
        count = int((df_assign["ders"] == d).sum())
        chips.append(f"<span class='goal-chip'>{d}: {count} görev</span>")
    st.markdown(" ".join(chips), unsafe_allow_html=True)

# ---- Yeni hedef ekle (Dakika / Soru / Video + kaynak) ----
st.subheader("➕ Yeni Hedef Ekle")

settings = load_settings()
level_col = level_to_col(settings["level"])
topics = load_topics(level_col)   # subject -> ders, topic -> konu

dersler_list = topics["subject"].unique().tolist()
ders = st.selectbox("Ders", dersler_list)
konular = st.multiselect("Konular", topics[topics["subject"] == ders]["topic"].tolist())

col_a, col_b = st.columns(2)
with col_a:
    birim = st.selectbox("Görev türü", ["Dakika","Soru","Video"], index=0)
with col_b:
    if birim == "Dakika":
        miktar = st.number_input("Dakika", min_value=5, max_value=600, value=90, step=5)
    elif birim == "Soru":
        miktar = st.number_input("Soru sayısı", min_value=1, max_value=2000, value=20, step=5)
    else:
        miktar = st.number_input("Video adedi", min_value=1, max_value=200, value=1, step=1)

kaynak = ""
if birim in ("Soru","Video"):
    res_df = get_resources(subject=ders, type_=birim)
    names = ["(Seçiniz)"] + (res_df["name"].tolist() if not res_df.empty else []) + ["(Elle yaz)"]
    choice = st.selectbox("Kaynak", names, index=0)
    if choice == "(Elle yaz)":
        kaynak = st.text_input("Kaynak adı", placeholder="Örn: X Yayınları TYT Matematik SB")
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

with st.expander("ℹ️ Notlar"):
    st.write("""
- Görev türleri: **Dakika**, **Soru**, **Video**.  
- *Soru/Video* için **Kaynak** seçmen önerilir (örn. *X Yayınları Soru Bankası*, *Mehmet Hoca Video Serisi*).  
- Yüzde, o derse atanmış görevlerin **adet olarak** tamamlanma oranıdır.
""")
