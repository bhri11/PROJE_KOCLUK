# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from core.exam_reviews import load_exam_reviews, recommend_exams, render_exam_card

st.title("🧪 Deneme Önerileri")

df = load_exam_reviews()
if df.empty:
    st.info("Henüz deneme verisi yok. data/exam_reviews.csv dosyasına satır ekleyerek başlayın.")
    st.stop()

# üst filtreler
subjects = sorted(df["subject"].dropna().unique().tolist())
col1, col2, col3 = st.columns([1,1,1])
with col1:
    subject = st.selectbox("Ders / Kategori", subjects, index=subjects.index("Türkçe Genel") if "Türkçe Genel" in subjects else 0)
with col2:
    level = st.selectbox("Seviye", ["Başlangıç","Orta","İleri"], index=1)
with col3:
    min_exams = st.number_input("En az deneme sayısı", min_value=0, max_value=30, value=0, step=1)

rec = recommend_exams(subject, level=level, min_exams=int(min_exams))

st.markdown(f"**{subject}** için öneriler — **Seviye:** {level}  \n"
            f"Listede **{len(rec)}** yayın var, skor yüksekten düşüğe sıralanır.")

if rec.empty:
    st.warning("Eşleşme yok. Filtreleri genişletmeyi deneyin.")
else:
    # tablo görünümü
    tbl = rec.rename(columns={
        "name":"Kaynak",
        "exam_count":"Deneme",
        "difficulty":"Zorluk",
        "osym_fit":"ÖSYM Yakınlık",
        "solution_clarity":"Video Çözüm",
        "layout":"Mizanpaj",
        "match":"Öneri Skoru"
    })
    st.dataframe(tbl[["Kaynak","Deneme","Zorluk","ÖSYM Yakınlık","Video Çözüm","Mizanpaj","Öneri Skoru"]],
                 hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("Kart Görünümü")
    for _, r in rec.iterrows():
        st.markdown(render_exam_card(r), unsafe_allow_html=True)

with st.expander("Nasıl hesaplıyoruz?"):
    st.write("""
- Puan aralığı **0–100**. Seçilen seviyeye göre **Zorluk** hedefi değişir:
  - *Başlangıç* → zorluk ~6 civarı
  - *Orta* → zorluk ~7.5
  - *İleri* → zorluk ~9
- Skor, **ÖSYM Yakınlık**, **Video Çözüm açıklığı** ve **Mizanpaj** ile birlikte ağırlıklı hesaplanır.
- İstersen ağırlıkları özelleştirebiliriz.
""")
