# --- Path bootstrap ---
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports ---
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from core.dataio import load_students, load_settings, level_to_col, load_topics
from core.curriculum import get_curriculum, log_minutes

# --- Page config ---
st.set_page_config(page_title="Müfredat İzleme", page_icon="📈", layout="wide")
st.title("📈 Müfredat İzleme")

# -----------------------------
# Öğrenci ve ders seçimi
# -----------------------------
students = load_students()
students = students[students["active"] == True].copy()
if students.empty:
    st.warning("Aktif öğrenci yok. Lütfen Öğrenci Yönetimi sayfasından öğrenci ekleyin/aktif edin.")
    st.stop()

name_to_id = {r.student_name: int(r.student_id) for _, r in students.iterrows()}

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    student_name = st.selectbox("Öğrenci", list(name_to_id.keys()))
sid = name_to_id[student_name]

# Dersleri topics.csv'den
level_col = level_to_col(load_settings()["level"])
topics_all = load_topics(level_col)
subjects = topics_all["subject"].unique().tolist()

with col2:
    subject = st.selectbox("Ders", subjects)

with col3:
    only_open = st.checkbox("Sadece tamamlanmayanlar", value=False)

# -----------------------------
# Müfredatı yükle
# -----------------------------
cur = get_curriculum(sid, subject).copy()
if cur.empty:
    st.info("Bu ders için müfredat yok. **Müfredat Planı** sayfasından oluşturabilirsiniz.")
    st.stop()

# Beklenen kolonları garanti altına al
for c in ["topic", "target_min", "done_min"]:
    if c not in cur.columns:
        cur[c] = 0

cur["target_min"] = pd.to_numeric(cur["target_min"], errors="coerce").fillna(0).astype(int)
cur["done_min"]  = pd.to_numeric(cur["done_min"],  errors="coerce").fillna(0).astype(int)
cur["remain_min"] = (cur["target_min"] - cur["done_min"]).clip(lower=0).astype(int)
cur["pct"] = (100 * cur["done_min"] / cur["target_min"].replace({0: pd.NA})).fillna(0).round(1)

if only_open:
    cur = cur[cur["remain_min"] > 0].copy()

# -----------------------------
# Özet & Donut grafik
# -----------------------------
total_target = int(cur["target_min"].sum())
total_done   = int(cur["done_min"].sum())
total_rem    = max(total_target - total_done, 0)
pct_total    = round(100 * total_done / total_target, 1) if total_target else 0.0

st.subheader(f"Özet — {subject}")
st.caption(f"Hedef: **{total_target} dk**, Yapılan: **{total_done} dk**, Kalan: **{total_rem} dk**")

fig, ax = plt.subplots(figsize=(2.8, 2.8))
ax.pie([total_done, max(total_target-total_done, 0)], startangle=90, wedgeprops=dict(width=0.35))
ax.text(0, 0, f"%{pct_total}", ha="center", va="center", fontsize=14, weight="bold")
ax.set(aspect="equal")
st.pyplot(fig, use_container_width=False)

st.divider()

# -----------------------------
# Yardımcı
# -----------------------------
def fmt_min(m: int) -> str:
    m = int(m)
    h, r = divmod(m, 60)
    return f"{h}s {r}dk" if h else f"{r}dk"

# -----------------------------
# Konu kartları (UNIQUE KEY FIX)
# -----------------------------
# Sıralama
if "order" in cur.columns:
    cur = cur.sort_values(["order", "topic"]).reset_index(drop=True)
else:
    cur = cur.sort_values(["remain_min", "topic"], ascending=[False, True]).reset_index(drop=True)

# Her satır için benzersiz anahtar üretmek için index'i kullanıyoruz
for i, row in cur.reset_index(drop=True).iterrows():
    konu   = str(row["topic"])
    hedef  = int(row["target_min"])
    yapilan= int(row["done_min"])
    kalan  = int(row["remain_min"])
    pct    = float(row["pct"]) if hedef else 0.0

    # Her widget için benzersiz ve stabil key tabanı
    kbase = f"{sid}-{subject}-{i}"

    st.markdown(f"### {konu}")
    st.progress(min(int(pct), 100))
    st.caption(f"Hedef: {fmt_min(hedef)} • Yapılan: {fmt_min(yapilan)} • Kalan: {fmt_min(kalan)}")

    col_a, col_b, col_c = st.columns([0.42, 0.28, 0.30])

    with col_a:
        delta = st.number_input(
            "Dakika ekle/çıkar",
            min_value=-600, max_value=600, value=30, step=5,
            key=f"delta__{kbase}",
            help="Pozitif: ekle • Negatif: çıkar (düzeltme)"
        )

    with col_b:
        if st.button("➕ Ekle", key=f"add__{kbase}"):
            if int(delta) != 0:
                try:
                    log_minutes(sid, subject, konu, int(delta))
                    st.success(f"“{konu}” için {int(delta)} dk işlendi.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydetme hatası: {e}")

    with col_c:
        if st.button("✓ Bitir", key=f"done__{kbase}",
                     help="Kalan dakikayı otomatik ekler ve konuyu tamamlar."):
            try:
                if kalan > 0:
                    log_minutes(sid, subject, konu, int(kalan))
                st.success(f"“{konu}” tamamlandı.")
                st.rerun()
            except Exception as e:
                st.error(f"Kaydetme hatası: {e}")

    st.caption("İpucu: Hatalı girişleri düzeltmek için **negatif** dakika girebilirsiniz.")
    st.divider()
