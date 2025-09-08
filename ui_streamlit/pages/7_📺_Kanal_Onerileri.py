# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from core.channel_features import load_channels, list_by_subject, render_channel_card

st.title("📺 Kanal Önerileri")

df = load_channels()
if df.empty:
    st.info("Henüz kanal eklenmemiş. data/channel_features.csv dosyasına satır ekleyerek başlayın.")
    st.stop()

dersler = sorted(df["subject"].dropna().unique().tolist())
ders = st.selectbox("Ders / Kategori", dersler)

sub = list_by_subject(ders)
for _, row in sub.iterrows():
    st.markdown(render_channel_card(row), unsafe_allow_html=True)

with st.expander("CSV Yapısı"):
    st.write("""
Alanlar: **channel_id**, **name**, **subject**, **difficulty**, **tags**(`;` ile), 
**avg_duration** (dk), **video_count** (yaklaşık), **playlists**(`;` ile), **notes**.
Yeni ders/kanal için **satır ekleyin** – başka kod değişikliği gerekmez.
""")
