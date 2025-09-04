# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date
import streamlit as st
import pandas as pd

from core.dataio import load_students, load_settings, level_to_col, load_topics
from core.curriculum import get_curriculum, generate_from_topics, pick_for_week
from core.assignments import add_bulk, week_start_of

st.title("🧭 Müfredat Planı")

# Öğrenci seç
students = load_students()
students = students[students["active"] == True].copy()
name_to_id = {r.student_name: int(r.student_id) for _, r in students.iterrows()}
student_name = st.selectbox("Öğrenci", list(name_to_id.keys()))
student_id = name_to_id[student_name]

# Ders ve seviye
settings = load_settings()
topics_all = load_topics(level_to_col(settings["level"]))
dersler = topics_all["subject"].unique().tolist()
ders = st.selectbox("Ders", dersler)

seviye_map = {"Başlangıç":"beginner", "Orta Düzey":"intermediate", "İleri Düzey":"advanced"}
seviye_label = st.selectbox("Seviye", list(seviye_map.keys()),
                            index=["beginner","intermediate","advanced"].index(settings.get("level","beginner")))
seviye = seviye_map[seviye_label]

colg1, colg2 = st.columns([1,1])
with colg1:
    overwrite = st.checkbox("Aynı ders için mevcut müfredatı sıfırla", value=True)
with colg2:
    if st.button("📥 Tüm konuları seviyeye göre oluştur"):
        generate_from_topics(student_id=student_id, level=seviye, ders=ders, overwrite=overwrite)
        st.success("Müfredat oluşturuldu / güncellendi.")
        st.rerun()

# Görünüm
st.subheader("📋 Bu öğrencinin müfredatı")
cur = get_curriculum(student_id, ders=ders)
cur_disp = cur.rename(columns={"order":"Sıra","konu":"Konu","birim":"Birim","miktar":"Miktar","kaynak":"Kaynak"})
st.dataframe(cur_disp, hide_index=True, use_container_width=True)

# Bu haftaya aktar (opsiyonel)
st.subheader("📅 Müfredattan bu haftaya aktar (opsiyonel)")
hafta_baslangic = week_start_of(st.date_input("Hafta başlangıcı (Pzt)", value=week_start_of(date.today())))
if cur.empty:
    st.caption("Önce müfredat oluştur.")
else:
    # seçim
    konu_list = cur["konu"].tolist()
    secili_konular = st.multiselect("Aktarılacak konular", konu_list)
    colb1, colb2 = st.columns([1,1])
    with colb1:
        if st.button("Seçilenleri aktar"):
            rows = []
            for _, r in cur[cur["konu"].isin(secili_konular)].iterrows():
                rows += pick_for_week(student_id, hafta_baslangic, ders, [{
                    "konu": r.konu, "birim": r.birim, "miktar": r.miktar, "kaynak": r.kaynak
                }])
            add_bulk(rows)
            st.success("Seçilen konular bu haftaya atandı.")
    with colb2:
        if st.button("TÜMÜNÜ aktar"):
            rows = []
            for _, r in cur.iterrows():
                rows += pick_for_week(student_id, hafta_baslangic, ders, [{
                    "konu": r.konu, "birim": r.birim, "miktar": r.miktar, "kaynak": r.kaynak
                }])
            add_bulk(rows)
            st.success("Tüm müfredat bu haftaya atandı.")
