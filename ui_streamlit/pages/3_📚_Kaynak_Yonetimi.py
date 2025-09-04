# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from core.dataio import load_settings, level_to_col, load_topics
from core.resources import get_resources, add_resource, delete_resource

st.title("📚 Kaynak Yönetimi")

# Ders listesi (topics'ten)
settings = load_settings()
subjects = sorted(load_topics(level_to_col(settings["level"]))["subject"].unique().tolist())

# ➕ Ekle
with st.form("add_res"):
    st.subheader("➕ Kaynak Ekle")
    name = st.text_input("Ad (örn. X Yayınları TYT Matematik Soru Bankası)")
    type_ = st.selectbox("Tür", ["Soru","Video"], index=0)
    subject = st.selectbox("Ders", subjects)
    total = st.number_input("Toplam adet (opsiyonel)", min_value=0, max_value=10000, value=0, step=10)
    notes = st.text_input("Not (opsiyonel)")
    ok = st.form_submit_button("Ekle")
    if ok:
        try:
            add_resource(name=name, type_=type_, subject=subject, total_items=int(total), notes=notes)
            st.success("Kaynak eklendi.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

# 🔎 Liste & filtre
st.subheader("🔎 Liste")
colf1, colf2 = st.columns(2)
with colf1:
    f_type = st.selectbox("Tür filtre", ["(Tümü)","Soru","Video"], index=0)
with colf2:
    f_subj = st.selectbox("Ders filtre", ["(Tümü)"] + subjects, index=0)

df = get_resources(
    subject=None if f_subj == "(Tümü)" else f_subj,
    type_=None if f_type == "(Tümü)" else f_type
)

# Türkçe başlıklar
df_display = df.rename(columns={
    "resource_id": "ID",
    "name": "Kaynak",
    "type": "Tür",
    "subject": "Ders",
    "total_items": "Toplam",
    "notes": "Not"
})
st.dataframe(df_display, hide_index=True, use_container_width=True)

# 🗑 Sil (sadece adları göster)
st.subheader("🗑 Sil")
if df.empty:
    st.info("Silinecek kaynak yok.")
else:
    names_only = df["name"].tolist()
    idx = st.selectbox("Silinecek kaynak", options=list(range(len(names_only))),
                       format_func=lambda i: names_only[i])
    chosen_row = df.iloc[idx]
    if st.button("Sil", type="primary"):
        delete_resource(int(chosen_row["resource_id"]))
        st.success(f"Silindi: {chosen_row['name']}")
        st.rerun()
