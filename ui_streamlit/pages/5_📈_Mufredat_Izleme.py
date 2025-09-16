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
from core.curriculum import (
    get_curriculum, log_minutes, list_progress, undo_last, reset_topic,
    delete_topic_plan, delete_subject_plan
)

st.set_page_config(page_title="Müfredat İzleme", page_icon="📈", layout="wide")
st.title("📈 Müfredat İzleme")

# -----------------------------
# Öğrenci & Ders
# -----------------------------
students = load_students()
students = students[students["active"] == True].copy()
if students.empty:
    st.warning("Aktif öğrenci yok.")
    st.stop()

name_to_id = {r.student_name: int(r.student_id) for _, r in students.iterrows()}
col1, col2, col3 = st.columns([1,1,1])
with col1:
    student_name = st.selectbox("Öğrenci", list(name_to_id.keys()))
sid = name_to_id[student_name]

level_col = level_to_col(load_settings()["level"])
subjects = load_topics(level_col)["subject"].unique().tolist()
with col2:
    subject = st.selectbox("Ders", subjects)

with col3:
    only_open = st.checkbox("Sadece tamamlanmayanlar", value=False)

cur = get_curriculum(sid, subject).copy()
if cur.empty:
    st.info("Bu ders için müfredat yok. **Müfredat Planı** sayfasından oluşturabilirsiniz.")
    st.stop()

for c in ["topic","target_min","done_min"]:
    if c not in cur.columns: cur[c] = 0
cur["target_min"] = pd.to_numeric(cur["target_min"], errors="coerce").fillna(0).astype(int)
cur["done_min"] = pd.to_numeric(cur["done_min"], errors="coerce").fillna(0).astype(int)
cur["remain_min"] = (cur["target_min"] - cur["done_min"]).clip(lower=0).astype(int)
cur["pct"] = (100 * cur["done_min"] / cur["target_min"].replace({0: pd.NA})).fillna(0).round(1)

if only_open:
    cur = cur[cur["remain_min"] > 0].copy()

# -----------------------------
# Özet (donut)
# -----------------------------
def _fmt(m: int) -> str:
    m = int(m); h, r = divmod(m, 60)
    return f"{h}s {r}dk" if h else f"{r}dk"

total_target = int(cur["target_min"].sum())
total_done   = int(cur["done_min"].sum())
total_rem    = max(total_target - total_done, 0)
pct_total    = round(100 * total_done / total_target, 1) if total_target else 0.0

st.subheader(f"Özet — {subject}")
st.caption(f"Hedef: **{_fmt(total_target)}**, Yapılan: **{_fmt(total_done)}**, Kalan: **{_fmt(total_rem)}**")

fig, ax = plt.subplots(figsize=(2.8, 2.8))
ax.pie([total_done, max(total_target-total_done, 0)], startangle=90, wedgeprops=dict(width=0.35))
ax.text(0, 0, f"%{pct_total}", ha="center", va="center", fontsize=14, weight="bold")
ax.set(aspect="equal")
st.pyplot(fig, use_container_width=False)

st.divider()

with st.expander("🚮 Bu dersin planını kaldır", expanded=False):
    st.warning("Bu işlem seçili ders için müfredat planını siler. İstersen ilerleme geçmişini de temizler.")
    colx1, colx2 = st.columns([0.7, 0.3])
    with colx1:
        also_logs = st.checkbox("İlerleme loglarını da sil", value=True)
    with colx2:
        if st.button("Ders planını sil", type="secondary"):
            info = delete_subject_plan(sid, subject, also_logs=also_logs)
            st.success(f"{subject} planı silindi → {info['plan_deleted']} konu, {info['logs_deleted']} log.")
            st.rerun()

# Sıralama (order varsa ona göre)
if "order" in cur.columns:
    cur = cur.sort_values(["order", "topic"]).reset_index(drop=True)
else:
    cur = cur.sort_values(["remain_min", "topic"], ascending=[False, True]).reset_index(drop=True)

# -----------------------------
# Konu kartları
# -----------------------------
for i, row in cur.reset_index(drop=True).iterrows():
    topic  = str(row["topic"])
    hedef  = int(row["target_min"])
    done   = int(row["done_min"])
    remain = int(row["remain_min"])
    pct    = float(row["pct"]) if hedef else 0.0

    kbase = f"{sid}-{subject}-{i}"

    st.markdown(f"### {topic}")
    st.progress(min(int(pct), 100))
    st.caption(f"Hedef: {_fmt(hedef)} • Yapılan: {_fmt(done)} • Kalan: {_fmt(remain)}")

    c1, c2, c3 = st.columns([0.44, 0.28, 0.28])

    # Dakika ekle/çıkar
    with c1:
        delta = st.number_input(
            "Dakika ekle/çıkar",
            min_value=-600, max_value=600, value=30, step=5,
            key=f"delta__{kbase}",
            help="Pozitif: ekle • Negatif: çıkar"
        )
    with c2:
        if st.button("➕ Ekle", key=f"add__{kbase}"):
            if int(delta) != 0:
                try:
                    log_minutes(sid, subject, topic, int(delta))
                    st.success(f"“{topic}” için {int(delta)} dk işlendi.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kaydetme hatası: {e}")
    with c3:
        if st.button("✓ Bitir", key=f"done__{kbase}",
                     help="Kalan dakikayı otomatik ekler."):
            try:
                if remain > 0:
                    log_minutes(sid, subject, topic, int(remain))
                st.success(f"“{topic}” tamamlandı.")
                st.rerun()
            except Exception as e:
                st.error(f"Kaydetme hatası: {e}")

    # --- Geçmiş & Düzelt ---
    with st.expander("🕓 Geçmiş ve düzeltme", expanded=False):
        logs = list_progress(sid, subject, topic, limit=5)
        if logs.empty:
            st.caption("Bu konu için kayıt yok.")
        else:
            show = logs[["ts","minutes"]].rename(columns={"ts":"Zaman", "minutes":"Dakika"})
            st.table(show)

            d1, d2, d3 = st.columns([0.33, 0.33, 0.34])

            with d1:
                if st.button("↩︎ Son girişi geri al", key=f"undo__{kbase}"):
                    if undo_last(sid, subject, topic):
                        st.success("Son giriş geri alındı.")
                        st.rerun()
                    else:
                        st.warning("Geri alınacak giriş bulunamadı.")

            with d2:
                if st.button("🧹 Bu konuyu sıfırla", key=f"wipe__{kbase}"):
                    n = reset_topic(sid, subject, topic)
                    st.success(f"{n} kayıt silindi. Konu sıfırlandı.")
                    st.rerun()

            with d3:
                new_total = st.number_input(
                    "Toplam yapılanı ayarla", min_value=0, max_value=10000,
                    value=done, step=5, key=f"settot__{kbase}"
                )
                if st.button("Kaydet", key=f"setbtn__{kbase}"):
                    delta_set = int(new_total) - done
                    if delta_set != 0:
                        log_minutes(sid, subject, topic, delta_set)
                    st.success("Toplam yapılan güncellendi.")
                    st.rerun()

    
    # --- Bu konuyu planımdan tamamen kaldır ---
delcol1, delcol2 = st.columns([0.65, 0.35])
with delcol2:
    if st.button("🗑️ Bu konuyu planımdan sil", key=f"delplan__{kbase}",
                 help="Plan satırını ve tüm logları siler."):
        info = delete_topic_plan(sid, subject, topic, also_logs=True)
        st.success(f"Silindi: “{topic}” → {info['plan_deleted']} plan, {info['logs_deleted']} log.")
        st.rerun()

    

    st.caption("İpucu: Hatalı girişleri düzeltmek için **negatif** dakika girebilir, "
               "en son girişi **geri alabilir**, gerekirse konuyu **sıfırlayabilirsiniz**.")
    st.divider()
