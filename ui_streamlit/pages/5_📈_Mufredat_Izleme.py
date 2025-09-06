# --- Path bootstrap ---
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from core.dataio import load_students
from core.curriculum import get_with_progress, set_done

st.title("📈 Müfredat İzleme")

# Öğrenci seç
students = load_students()
students = students[students["active"] == True].copy()
if students.empty:
    st.warning("Aktif öğrenci yok.")
    st.stop()
name_to_id = {r.student_name: int(r.student_id) for _, r in students.iterrows()}
student_name = st.selectbox("Öğrenci", list(name_to_id.keys()))
student_id = name_to_id[student_name]

# Ders seç
df_all = get_with_progress(student_id)
dersler = sorted(df_all["ders"].dropna().unique().tolist()) if not df_all.empty else []
if not dersler:
    st.info("Bu öğrenci için müfredat oluşturulmamış. '🧭 Müfredat Planı' sayfasından oluştur.")
    st.stop()
ders = st.selectbox("Ders", dersler)

# Filtreler
colf1, colf2 = st.columns(2)
with colf1:
    show_only_open = st.checkbox("Sadece tamamlanmayanlar", value=False)
with colf2:
    sort_by_pct = st.checkbox("En az ilerleyenden başla", value=True)

# Veriyi çek
df = get_with_progress(student_id, ders=ders)
if show_only_open:
    df = df[~df["shown_done"]].copy()

# Özet (manuel tamam da özetlere yansır)
target_total = int(df["miktar"].sum())
done_total = int(df["done_effective"].sum())
pct_total = int(round((done_total / target_total) * 100)) if target_total > 0 else 0
st.subheader(f"Özet — {ders}")
st.write(f"Hedef dakika: **{target_total}**, Yapılan: **{done_total}**, Kalan: **{max(target_total-done_total,0)}**")
st.progress(pct_total)

# Sıralama
if sort_by_pct:
    df = df.sort_values(["shown_done","pct","order"], ascending=[True, True, True])
else:
    df = df.sort_values(["order"])

# Liste: konu bazında ilerleme + tik
st.subheader("Konular")
for _, r in df.iterrows():
    left, right = st.columns([4,1])
    with left:
        st.markdown(f"**{r.konu}**")
        if r.birim == "Dakika":
            st.caption(f"Hedef: {int(r.miktar)} dk • Yapılan: {int(r.done_effective)} dk • Kalan: {int(r.remaining_min)} dk")
            st.progress(int(r.pct))
        else:
            st.caption(f"Birim: {r.birim} • Hedef: {int(r.miktar)} • (Dakika dışı birimler yüzde hesabına dahil edilmez)")
    with right:
        key = f"curdone|{student_id}|{ders}|{r.konu}"
        new_val = st.checkbox("Bitti", value=bool(r.shown_done), key=key)
        # yalnızca manuel alan değiştirilsin
        if new_val != bool(r.tamam):
            set_done(student_id, ders, r.konu, new_val)
            st.rerun()

with st.expander("Notlar"):
    st.write("""
- Özet ve çubuklar **dakika** bazlıdır. *Bitti* işaretlediğinde, yapılan dakika hedefe eşit kabul edilir.
- Otomatik tamam (yapılan ≥ hedef) yine %100 gösterilir.
- Soru/Video türleri şu an yüzdeye dahil edilmez; istersek ayrı metrik ekleyebiliriz.
""")
