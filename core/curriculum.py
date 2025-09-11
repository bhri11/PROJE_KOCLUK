# core/curriculum.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURR = DATA / "curriculum.csv"
CURR_LOG = DATA / "curriculum_progress.csv"

_CURR_COLS = ["student_id", "subject", "topic", "target_min"]
_LOG_COLS  = ["ts", "student_id", "subject", "topic", "minutes"]

def _ensure():
    DATA.mkdir(parents=True, exist_ok=True)
    if not CURR.exists():
        pd.DataFrame(columns=_CURR_COLS).to_csv(CURR, index=False, encoding="utf-8")
    if not CURR_LOG.exists():
        pd.DataFrame(columns=_LOG_COLS).to_csv(CURR_LOG, index=False, encoding="utf-8")

def _read_curr() -> pd.DataFrame:
    _ensure()
    df = pd.read_csv(CURR, encoding="utf-8") if CURR.stat().st_size else pd.DataFrame(columns=_CURR_COLS)
    for c in _CURR_COLS:
        if c not in df.columns:
            df[c] = 0 if c == "target_min" else ""
    df["student_id"] = df["student_id"].astype(str)
    df["target_min"] = pd.to_numeric(df["target_min"], errors="coerce").fillna(0).astype(int)
    return df[_CURR_COLS]

def _read_log() -> pd.DataFrame:
    _ensure()
    df = pd.read_csv(CURR_LOG, encoding="utf-8") if CURR_LOG.stat().st_size else pd.DataFrame(columns=_LOG_COLS)
    for c in _LOG_COLS:
        if c not in df.columns: df[c] = 0 if c == "minutes" else ""
    df["student_id"] = df["student_id"].astype(str)
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    return df[_LOG_COLS]

def _write_curr(df: pd.DataFrame): df[_CURR_COLS].to_csv(CURR, index=False, encoding="utf-8")
def _append_log(row: dict):
    df = _read_log()
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df2[_LOG_COLS].to_csv(CURR_LOG, index=False, encoding="utf-8")

# ---------- PUBLIC API ----------

def generate_from_topics(student_id: str, subject: str, topics: list[str], minutes_each: int = 180):
    """
    Verilen konu listesi için hedef dakika satırlarını oluşturur.
    Varsa dokunmaz; yoksa ekler (idempotent).
    """
    if not topics: return
    cur = _read_curr()
    student_id = str(student_id)
    new_rows = []
    for t in topics:
        mask = (cur["student_id"] == student_id) & (cur["subject"] == subject) & (cur["topic"] == t)
        if not mask.any():
            new_rows.append({"student_id": student_id, "subject": subject, "topic": t, "target_min": int(minutes_each)})
    if new_rows:
        cur = pd.concat([cur, pd.DataFrame(new_rows)], ignore_index=True)
        _write_curr(cur)

def log_minutes(student_id: str, subject: str, topic: str, minutes: int):
    """ İlerleme ekler (dakika). Negatif gönderirsen geri alır. """
    mins = int(minutes)
    if mins == 0: return
    _append_log({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "student_id": str(student_id), "subject": subject, "topic": topic, "minutes": mins
    })

def set_done(student_id: str, subject: str, topic: str):
    """ Konuyu BİTMİŞ işaretlemek için kalan dakikayı otomatik ekler. """
    df = get_curriculum(student_id, subject)
    row = df[df["topic"] == topic].head(1)
    if row.empty: return
    remain = int(row.iloc[0]["remain_min"])
    if remain > 0:
        log_minutes(student_id, subject, topic, remain)

def get_curriculum(student_id: str, subject: str | None = None) -> pd.DataFrame:
    """ Müfredat + yapılan dakika + kalan + yüzde """
    cur = _read_curr()
    lg  = _read_log()
    cur = cur[cur["student_id"] == str(student_id)].copy()
    if subject: cur = cur[cur["subject"] == subject].copy()

    done = (lg.groupby(["student_id","subject","topic"], as_index=False)["minutes"]
              .sum().rename(columns={"minutes":"done_min"})) if not lg.empty else \
           pd.DataFrame(columns=["student_id","subject","topic","done_min"])

    m = cur.merge(done, how="left", on=["student_id","subject","topic"])
    m["done_min"] = pd.to_numeric(m["done_min"], errors="coerce").fillna(0).astype(int)
    m["remain_min"] = (m["target_min"] - m["done_min"]).clip(lower=0).astype(int)
    m["pct"] = (100 * m["done_min"] / m["target_min"].replace(0, pd.NA)).fillna(0).round(1)
    return m.sort_values(["subject","topic"]).reset_index(drop=True)

def summarize_progress(student_id: str, subject: str | None = None) -> dict:
    df = get_curriculum(student_id, subject)
    tot  = int(df["target_min"].sum()) if not df.empty else 0
    done = int(df["done_min"].sum()) if not df.empty else 0
    remain = max(tot - done, 0)
    pct = int(round(100 * done / tot)) if tot else 0
    return {"total": tot, "done": done, "remain": remain, "pct": pct}

def pick_for_student(student_id: str, subject: str, n: int = 5) -> pd.DataFrame:
    """ En az ilerleyen n konuyu getir. """
    df = get_curriculum(student_id, subject)
    return df.sort_values(["pct", "remain_min"], ascending=[True, False]).head(n).reset_index(drop=True)
