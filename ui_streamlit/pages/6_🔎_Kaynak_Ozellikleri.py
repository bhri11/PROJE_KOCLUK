# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from core.resource_features import load_resource_features, list_by_subject, get_feature, render_feature_card

st.title("🔎 Kaynak Özellikleri")

df = load_resource_features()
if df.empty:
    st.info("Henüz özellik eklenmemiş. data/resource_features.csv dosyasına satır ekleyerek başlayabilirsin.")
    st.stop()

dersler = sorted(df["subject"].dropna().unique().tolist())
ders = st.selectbox("Ders", dersler)

sub = list_by_subject(ders)
names = sub["name"].tolist()
idx = st.selectbox("Kaynak", options=list(range(len(names))), format_func=lambda i: names[i])

row = sub.iloc[idx]
st.markdown(render_feature_card(row), unsafe_allow_html=True)

with st.expander("CSV Hakkında"):
    st.write("""
`resource_features.csv` alanları:
- **resource_id** *(opsiyonel)*: resources.csv ile bağlamak için
- **name, subject, type, difficulty**: ana bilgiler
- **tags**: `;` ile ayrılmış etiketler
- **bullets**: `|` ile ayrılmış kısa maddeler
- **notes**: serbest açıklama
Yeni ders/kitap eklemek için **satır eklemen** yeterli.
""")
