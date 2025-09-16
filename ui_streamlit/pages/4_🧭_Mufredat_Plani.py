# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports ---
import streamlit as st
import pandas as pd

from core.dataio import load_students, load_settings, level_to_col, load_topics
from core.curriculum import generate_from_topics, get_curriculum

st.set_page_config(page_title="Müfredat Planı", page_icon="📒", layout="wide")
st.title("📒 Müfredat Planı")

# -----------------------------
# Öğrenci & Ders seçimi
# -----------------------------
students = load_students()
students = students[students["active"] == True].copy()
if students.empty:
    st.warning("Aktif öğrenci yok. Öğrenci Yönetimi sayfasından ekleyin/aktif edin.")
    st.stop()

name_to_id = {r.student_name: int(r.student_id) for _, r in students.iterrows()}
col1, col2, col3 = st.columns([1,1,1])

with col1:
    student_name = st.selectbox("Öğrenci", list(name_to_id.keys()))
sid = name_to_id[student_name]

settings = load_settings()
default_level_col = level_to_col(settings["level"])   # 'beginner_min' | 'intermediate_min' | 'advanced_min'
topics_all = load_topics(default_level_col)

subjects = topics_all["subject"].unique().tolist()
with col2:
    subject = st.selectbox("Ders", subjects)

# Seviye seçimi (ayarlar varsayılan, istersen değiştir)
level_map = {
    "Başlangıç": "beginner_min",
    "Orta": "intermediate_min",
    "İleri": "advanced_min",
}
with col3:
    level_label = st.selectbox("Seviye", list(level_map.keys()),
                               index=list(level_map.keys()).index(settings["level"])
                               if settings.get("level") in level_map else 1)
level_col = level_map[level_label]

# Bu dersin konu listesi
sub = topics_all[topics_all["subject"] == subject].copy()
if sub.empty:
    st.info("Bu ders için topics.csv içinde konu bulunamadı.")
    st.stop()

# Dakika kolonu adayları (load_topics farklı dönebilir; güvenli tarama)
minute_col_candidates = ["minutes", level_col, "beginner_min", "intermediate_min", "advanced_min"]
minute_col = next((c for c in minute_col_candidates if c in sub.columns), None)
if minute_col is None:
    # dakika kolonu hiç yoksa, her konuya sabit dakika sor
    fixed_minutes = st.number_input("Her konu için hedef dakika", min_value=30, max_value=1200, value=180, step=15)
else:
    fixed_minutes = None

st.markdown(f"**{subject}** dersi için konu sayısı: **{len(sub)}**")

# Mevcut plan özeti
cur = get_curriculum(sid, subject)
if cur.empty:
    st.caption("Bu ders için oluşturulmuş bir plan yok.")
else:
    tot = int(cur["target_min"].sum()); done = int(cur["done_min"].sum())
    st.caption(f"Mevcut plan: Hedef **{tot} dk**, Yapılan **{done} dk**")

st.divider()

# -----------------------------
# Planı oluştur / güncelle
# -----------------------------
st.subheader("Plan oluştur / güncelle")

def _iter_topic_min_pairs(df: pd.DataFrame):
    """
    Konu adlarını trim'ler, boş olanları atar. Sabit dakika seçildiyse onu,
    yoksa seçilen seviye kolonundaki dakikayı kullanır.
    """
    # Dakika kaynağı "minute_col" ya da sabit "fixed_minutes" dış kapsamda set ediliyor
    if minute_col:
        for _, r in df.iterrows():
            t = str(r["topic"]).strip()
            if not t:
                continue
            m = int(pd.to_numeric(r[minute_col], errors="coerce"))
            if m <= 0:
                continue
            yield t, m
    else:
        for t in df["topic"].astype(str).str.strip():
            if not t:
                continue
            yield t, int(fixed_minutes)


if st.button("📌 Bu ders için planı oluştur/güncelle", type="primary"):
    try:
        # Tek tek ekle (generate_from_topics idempotent; varsa dokunmaz)
        for t, m in _iter_topic_min_pairs(sub):
            generate_from_topics(student_id=sid, subject=subject, topics=[t], minutes_each=m)

        st.success("Plan güncellendi. İzleme sayfasından ilerleyişi görebilirsiniz.")
        st.rerun()
    except Exception as e:
        st.error(f"Plan oluşturma hatası: {e}")

# İsteğe bağlı: Mevcut konu listesi önizleme
with st.expander("Konuları göster"):
    preview = sub[["order", "topic"]].copy() if "order" in sub.columns else sub[["topic"]].copy()
    if minute_col:
        preview["hedef_dk"] = pd.to_numeric(sub[minute_col], errors="coerce").fillna(0).astype(int)
    else:
        preview["hedef_dk"] = int(fixed_minutes)
    st.dataframe(preview, hide_index=True)
