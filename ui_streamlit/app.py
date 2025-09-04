import streamlit as st

st.set_page_config(page_title="Koç Asistan", layout="centered")

st.title("🎯 Koç Asistan – Ana Sayfa")
st.write("Aşağıdan ihtiyaç duyduğun sayfayı açabilirsin:")

# Modern çoklu sayfa navigasyonu
st.page_link("pages/1_👤_Koc_Paneli.py", label="Koç Paneli", icon="👤")
st.page_link("pages/2_🧑‍🎓_Ogrenci_Yonetimi.py", label="Öğrenci Yönetimi", icon="🧑‍🎓")
st.page_link("pages/3_📚_Kaynak_Yonetimi.py", label="Kaynak Yönetimi", icon="📚")
st.page_link("pages/4_🧭_Mufredat_Plani.py", label="Müfredat Planı", icon="🧭")

with st.expander("📌 İpucu"):
    st.markdown("""
- **Koç Paneli**: Haftalık görevleri gör / ✓✗ işaretle / yeni görev ata.  
- **Öğrenci Yönetimi**: Ekle, yeniden adlandır, aktif–pasif yap.  
- **Kaynak Yönetimi**: Soru/Video kaynaklarını ekle ve düzenle.  
- **Müfredat Planı**: Seviyeye göre tüm konuları tek tıkla oluştur; haftaya aktar.
""")
