# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from core.dataio import load_students, add_student, rename_student, deactivate_student, reactivate_student

st.title("🧑‍🎓 Öğrenci Yönetimi")

# ➕ Ekle
with st.form("add_student"):
    st.subheader("➕ Yeni Öğrenci Ekle")
    name = st.text_input("Ad Soyad")
    ok = st.form_submit_button("Ekle")
    if ok:
        try:
            sid = add_student(name)
            st.success(f"Eklendi: {name} (ID: {sid})")
            st.rerun()
        except Exception as e:
            st.error(str(e))

students = load_students()

# ✏️ Yeniden adlandır
with st.form("rename_student"):
    st.subheader("✏️ Yeniden Adlandır")
    if students.empty:
        st.caption("Kayıtlı öğrenci yok.")
    else:
        options = {int(r.student_id): f"{r.student_name} (ID:{int(r.student_id)})" for _, r in students.iterrows()}
        sid = st.selectbox("Öğrenci", options=list(options.keys()),
                           format_func=lambda k: options[k])
        newn = st.text_input("Yeni ad")
        ok2 = st.form_submit_button("Kaydet")
        if ok2:
            try:
                rename_student(int(sid), newn)
                st.success("Ad güncellendi.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ⏸ Aktif/Pasif
st.subheader("⏸ Aktif / Pasif")
col1, col2 = st.columns(2)

with col1:
    actives = students[students["active"] == True]
    if actives.empty:
        st.caption("Aktif öğrenci yok.")
    else:
        labels_a = {int(r.student_id): r.student_name for _, r in actives.iterrows()}
        sid_deact = st.selectbox("Pasif yapılacak öğrenci", options=list(labels_a.keys()),
                                  format_func=lambda k: labels_a[k], key="deact_box")
        if st.button("Pasif Yap"):
            deactivate_student(int(sid_deact))
            st.success("Pasif yapıldı (arşivlendi).")
            st.rerun()

with col2:
    inactives = students[students["active"] == False]
    if inactives.empty:
        st.caption("Pasif öğrenci yok.")
    else:
        labels_i = {int(r.student_id): r.student_name for _, r in inactives.iterrows()}
        sid_act = st.selectbox("Aktif yapılacak öğrenci", options=list(labels_i.keys()),
                               format_func=lambda k: labels_i[k], key="act_box")
        if st.button("Aktif Yap"):
            reactivate_student(int(sid_act))
            st.success("Aktif yapıldı.")
            st.rerun()

# 📋 Tüm Öğrenciler (Türkçe başlıklar)
st.subheader("📋 Tüm Öğrenciler")
df_disp = students.rename(columns={
    "student_id": "ID",
    "student_name": "Öğrenci",
    "active": "Durum",
    "created_at": "Kayıt Tarihi"
}).copy()
df_disp["Durum"] = df_disp["Durum"].map({True: "Aktif", False: "Pasif"})
st.dataframe(df_disp, hide_index=True, use_container_width=True)

with st.expander("Açıklama"):
    st.write("**Pasif** = mezun/ayrılmış/ara vermiş. Veriler silinmez; Koç Paneli seçiminde görünmez. İstenirse tekrar **Aktif** yapılır.")
