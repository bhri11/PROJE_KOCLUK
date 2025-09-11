# --- Path bootstrap (pages klasöründeyiz) ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from core.resources import (
    load_resources, save_resources, add_resource, get_resources
)
from core.resource_features import (
    load_resource_features, upsert_resource_feature
)

st.title("📚 Kaynak Yönetimi")

st.markdown("""
<style>
.block-container { padding-top: 1rem; }
.stDataFrame { border: 1px solid #2a2f3a; border-radius: 12px; }
.goal-chip { background:#111827; border:1px solid #2a2f3a; padding:.3rem .5rem; border-radius:.6rem; display:inline-block; margin:.12rem .20rem; }
.card { border:1px solid #2a2f3a; border-radius:12px; padding:12px 16px; margin:8px 0; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# Form: Kaynak Ekle (resources.csv + resource_features.csv)
# ------------------------------------------------
with st.expander("➕ Kaynak Ekle", expanded=True):
    name = st.text_input("Ad (örn. X Yayınları TYT Matematik Soru Bankası)")
    type_ = st.selectbox("Tür", ["Soru", "Video"])

    # Ders listesi (mevcutlardan + önerilen)
    existing_subjects = sorted(load_resources()["subject"].dropna().unique().tolist())
    defaults = ["Türkçe","Paragraf","Dil Bilgisi","Matematik","Problemler","Geometri",
                "Fizik","Kimya","Biyoloji","Tarih","Coğrafya"]
    subjects = sorted(set(existing_subjects) | set(defaults))
    subject = st.selectbox("Ders", subjects)

    # area (kategori) – derse göre öneri
    area_options = {
        "Türkçe": ["Genel","Paragraf","Dil Bilgisi"],
        "Matematik": ["Genel","Problemler","Geometri"],
        "Problemler": ["Genel"],
        "Geometri": ["Genel"],
    }
    areas_for_subject = area_options.get(subject, ["Genel"])
    area = st.selectbox("Kategori (area)", areas_for_subject)

    difficulty = st.selectbox("Seviye", ["Başlangıç","Orta","İleri"])
    total_items = st.number_input("Toplam adet (opsiyonel)", min_value=0, max_value=5000, value=0, step=10)
    notes = st.text_input("Not (opsiyonel)")

    st.markdown("**Etiketler (opsiyonel)** — örn: `video çözümlü; yeni nesil; analizli`")
    tags = st.text_input("Etiketler", value="")

    st.markdown("**Öne çıkan maddeler (opsiyonel)** — her satır bir madde olacak")
    bullets_lines = st.text_area("Madde listesi", value="", height=120)
    bullets = [l.strip() for l in bullets_lines.splitlines() if l.strip()]

    if st.button("Ekle", type="primary"):
        if not name.strip():
            st.warning("Ad alanı boş olamaz.")
        else:
            rid = add_resource(
                name=name, type_=type_, subject=subject,
                total_items=int(total_items), notes=notes,
                area=area, difficulty=difficulty
            )
            upsert_resource_feature(
                resource_id=rid,
                name=name,
                subject=subject,
                type_=type_,
                difficulty=difficulty,
                tags=tags,                # “;” ile ayrılmış
                bullets=bullets,          # liste → '|' ile yazılacak
                notes=notes
            )
            st.success(f"Kaynak eklendi (ID: {rid}).")

# ------------------------------------------------
# Liste + Filtreler
# ------------------------------------------------
st.subheader("🔍 Liste")

df_all = load_resources()
type_filter = st.selectbox("Tür filtre", ["(Tümü)"] + sorted(df_all["type"].dropna().unique().tolist()))
subject_filter = st.selectbox("Ders filtre", ["(Tümü)"] + sorted(df_all["subject"].dropna().unique().tolist()))
difficulty_filter = st.selectbox("Seviye filtre", ["(Tümü)", "Başlangıç", "Orta", "İleri"])

df = df_all.copy()
if type_filter != "(Tümü)":
    df = df[df["type"] == type_filter]
if subject_filter != "(Tümü)":
    df = df[df["subject"] == subject_filter]
if difficulty_filter != "(Tümü)":
    df = df[df["difficulty"] == difficulty_filter]

# Sütun adlarını Türkçeleştirilmiş başlıklarla gösterelim
view = df.rename(columns={
    "resource_id": "ID",
    "name": "Kaynak",
    "type": "Tür",
    "subject": "Ders",
    "area": "Kategori",
    "difficulty": "Seviye",
    "total_items": "Toplam",
    "notes": "Not"
})[["ID","Kaynak","Tür","Ders","Kategori","Seviye","Toplam","Not"]]

st.dataframe(view, use_container_width=True, hide_index=True)
