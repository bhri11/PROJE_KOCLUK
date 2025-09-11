# --- path bootstrap (pages klasöründeyiz) ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- imports ---
import streamlit as st
import pandas as pd

from core.resource_features import (
    load_resource_features,   # DF: resource_id,name,subject,type,difficulty,tags,bullets,notes
    get_feature,
    render_feature_card,
)

# --- küçük stil (chip'ler vb.) ---
st.markdown("""
<style>
.goal-chip {
  background:#111827; border:1px solid #2a2f3a;
  padding:.35rem .55rem; border-radius:.6rem;
  display:inline-block; margin:.12rem .22rem;
}
.card { border:1px solid #2a2f3a; border-radius:12px; padding:12px 16px; margin:8px 0; }
.help-meta { opacity:.85; }
</style>
""", unsafe_allow_html=True)

st.title("🔎 Kaynak Özellikleri")

# --- veriyi yükle ---
df = load_resource_features()  # columns: resource_id,name,subject,type,difficulty,tags,bullets,notes
if df.empty:
    st.info("Henüz özellik verisi yok. `data/resource_features.csv` dosyasını doldurun.")
    st.stop()

# -----------------------------
# 1) DERS seçimi
# -----------------------------
subjects = sorted(df["subject"].dropna().astype(str).unique().tolist())
default_subj = subjects.index("Matematik") if "Matematik" in subjects else 0
subject = st.selectbox("Ders", subjects, index=default_subj, key="feat_subj")

sub_df = df[df["subject"] == subject].copy()

# -----------------------------
# 2) ZORLUK filtresi (dinamik)
# -----------------------------
order = {"Başlangıç": 0, "Orta": 1, "İleri": 2}
levels_seen = (
    sub_df["difficulty"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

# varsa görülen seviyeleri güzel sırada göster
levels_sorted = sorted(levels_seen, key=lambda x: order.get(x, 99))
level_options = ["(Tümü)"] + levels_sorted
level_choice = st.selectbox("Seviye", level_options, index=0, key="feat_level")

if level_choice != "(Tümü)":
    sub_df = sub_df[sub_df["difficulty"] == level_choice]

# -----------------------------
# 3) KAYNAK seçimi
# -----------------------------
if sub_df.empty:
    st.info("Bu filtrelerle eşleşen kaynak bulunamadı.")
    st.stop()

names = sub_df["name"].tolist()
# var ise önce birini seçili getir (alfabetik tutuluyor)
pick = st.selectbox("Kaynak", names, index=0, key="feat_pick")

feat = get_feature(subject=subject, name=pick)
if feat is not None:
    st.markdown(render_feature_card(feat), unsafe_allow_html=True)
else:
    # çok düşük ihtimal: features'ta satır var ama format bozuk
    row = sub_df[sub_df["name"] == pick].iloc[0].to_dict()
    st.markdown(render_feature_card(row), unsafe_allow_html=True)

# --- bilgi kutusu ---
with st.expander("CSV Hakkında"):
    st.write(
        "Bu sayfa `data/resource_features.csv` dosyasından beslenir. "
        "Beklenen kolonlar: "
        "`resource_id,name,subject,type,difficulty,tags,bullets,notes`.\n\n"
        "- `tags` alanında etiketleri `;` ile ayırın (ör. `video çözümlü; seçici`).\n"
        "- `bullets` alanında madde işaretlerini `|` ile ayırın."
    )
