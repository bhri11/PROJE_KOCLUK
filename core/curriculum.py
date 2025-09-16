# core/curriculum.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import uuid
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURR = DATA / "curriculum.csv"
CURR_LOG = DATA / "curriculum_progress.csv"

# Şema
_CURR_COLS = ["student_id", "subject", "topic", "target_min"]
# log_id ekledik → tekil silme/düzeltme mümkün
_LOG_COLS  = ["log_id", "ts", "student_id", "subject", "topic", "minutes"]

# ----------------- low level -----------------

def _ensure():
    DATA.mkdir(parents=True, exist_ok=True)
    if not CURR.exists():
        pd.DataFrame(columns=_CURR_COLS).to_csv(CURR, index=False, encoding="utf-8")
    if not CURR_LOG.exists():
        pd.DataFrame(columns=_LOG_COLS).to_csv(CURR_LOG, index=False, encoding="utf-8")

def _read_curr() -> pd.DataFrame:
    _ensure()
    if CURR.stat().st_size:
        df = pd.read_csv(CURR, encoding="utf-8")
    else:
        df = pd.DataFrame(columns=_CURR_COLS)

    for c in _CURR_COLS:
        if c not in df.columns:
            df[c] = 0 if c == "target_min" else ""
    df["student_id"] = df["student_id"].astype(str)
    df["target_min"] = pd.to_numeric(df["target_min"], errors="coerce").fillna(0).astype(int)
    return df[_CURR_COLS]

def _read_log() -> pd.DataFrame:
    _ensure()
    if CURR_LOG.stat().st_size:
        df = pd.read_csv(CURR_LOG, encoding="utf-8")
    else:
        df = pd.DataFrame(columns=_LOG_COLS)

    # Şema migrate: log_id yoksa üret
    if "log_id" not in df.columns:
        df["log_id"] = [uuid.uuid4().hex for _ in range(len(df))]

    for c in _LOG_COLS:
        if c not in df.columns:
            df[c] = 0 if c == "minutes" else ""
    df["student_id"] = df["student_id"].astype(str)
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    # ts ISO string; sıralama için yeterli
    return df[_LOG_COLS]

def _write_curr(df: pd.DataFrame):
    df[_CURR_COLS].to_csv(CURR, index=False, encoding="utf-8")

def _write_log(df: pd.DataFrame):
    df[_LOG_COLS].to_csv(CURR_LOG, index=False, encoding="utf-8")

# ----------------- public api -----------------

def generate_from_topics(student_id: str, subject: str, topics: list[str], minutes_each: int = 180):
    """topics listesindeki her konu için hedef oluşturur; varsa dokunmaz."""
    if not topics:
        return
    cur = _read_curr()
    student_id = str(student_id)
    new_rows = []
    for t in topics:
        t = str(t)
        mask = (cur["student_id"] == student_id) & (cur["subject"] == subject) & (cur["topic"] == t)
        if not mask.any():
            new_rows.append({
                "student_id": student_id, "subject": subject, "topic": t, "target_min": int(minutes_each)
            })
    if new_rows:
        cur = pd.concat([cur, pd.DataFrame(new_rows)], ignore_index=True)
        _write_curr(cur)

def log_minutes(student_id: str, subject: str, topic: str, minutes: int):
    """İlerleme ekler (dakika). Negatif gönderirsen geri alır."""
    mins = int(minutes)
    if mins == 0:
        return
    df = _read_log()
    row = {
        "log_id": uuid.uuid4().hex,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "student_id": str(student_id),
        "subject": subject,
        "topic": str(topic),
        "minutes": mins,
    }
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write_log(df2)

def set_done(student_id: str, subject: str, topic: str):
    """Kalan dakikayı otomatik ekler ve konuyu tamamlar."""
    df = get_curriculum(student_id, subject)
    row = df[df["topic"] == str(topic)].head(1)
    if row.empty:
        return
    remain = int(row.iloc[0]["remain_min"])
    if remain > 0:
        log_minutes(student_id, subject, topic, remain)

def get_curriculum(student_id: str, subject: str | None = None) -> pd.DataFrame:
    """Plan + yapılan + kalan + yüzde."""
    cur = _read_curr()
    lg  = _read_log()

    cur = cur[cur["student_id"] == str(student_id)].copy()
    if subject:
        cur = cur[cur["subject"] == subject].copy()

    if lg.empty:
        done = pd.DataFrame(columns=["student_id","subject","topic","done_min"])
    else:
        done = (lg.groupby(["student_id","subject","topic"], as_index=False)["minutes"]
                  .sum().rename(columns={"minutes":"done_min"}))

    m = cur.merge(done, how="left", on=["student_id","subject","topic"])
    m["done_min"] = pd.to_numeric(m["done_min"], errors="coerce").fillna(0).astype(int)
    m["remain_min"] = (m["target_min"] - m["done_min"]).clip(lower=0).astype(int)
    m["pct"] = (100 * m["done_min"] / m["target_min"].replace(0, pd.NA)).fillna(0).round(1)
    # 'order' varsa dışarıda sıralarsın; burada sade döndürüyoruz
    return m.sort_values(["subject","topic"]).reset_index(drop=True)

def summarize_progress(student_id: str, subject: str | None = None) -> dict:
    df = get_curriculum(student_id, subject)
    tot  = int(df["target_min"].sum()) if not df.empty else 0
    done = int(df["done_min"].sum()) if not df.empty else 0
    remain = max(tot - done, 0)
    pct = int(round(100 * done / tot)) if tot else 0
    return {"total": tot, "done": done, "remain": remain, "pct": pct}

def pick_for_student(student_id: str, subject: str, n: int = 5) -> pd.DataFrame:
    df = get_curriculum(student_id, subject)
    return df.sort_values(["pct", "remain_min"], ascending=[True, False]).head(n).reset_index(drop=True)

# -------- yeni: ilerleme geçmişi yönetimi --------

def list_progress(student_id: str, subject: str | None = None,
                  topic: str | None = None, limit: int = 50) -> pd.DataFrame:
    """Son girişleri getirir (yeni → eski)."""
    df = _read_log()
    df = df[df["student_id"] == str(student_id)].copy()
    if subject:
        df = df[df["subject"] == subject]
    if topic:
        df = df[df["topic"] == str(topic)]
    if df.empty:
        return df[_LOG_COLS]
    df = df.sort_values("ts", ascending=False)
    if limit:
        df = df.head(limit)
    return df[_LOG_COLS].reset_index(drop=True)

def undo_last(student_id: str, subject: str, topic: str) -> bool:
    """Bu konu için en son logu siler."""
    df = _read_log()
    mask = (df["student_id"] == str(student_id)) & (df["subject"] == subject) & (df["topic"] == str(topic))
    if not mask.any():
        return False
    idx = df[mask].sort_values("ts", ascending=False).index
    df = df.drop(idx[0])
    _write_log(df)
    return True

def delete_logs(log_ids: list[str]) -> int:
    """Verilen log_id listesini siler; kaç satır sildiğini döndürür."""
    if not log_ids:
        return 0
    df = _read_log()
    before = len(df)
    df = df[~df["log_id"].isin(set(log_ids))].copy()
    _write_log(df)
    return before - len(df)

def edit_log(log_id: str, new_minutes: int) -> bool:
    """Tek bir log satırının dakika değerini değiştirir."""
    df = _read_log()
    mask = df["log_id"] == log_id
    if not mask.any():
        return False
    df.loc[mask, "minutes"] = int(new_minutes)
    _write_log(df)
    return True

def reset_topic(student_id: str, subject: str, topic: str) -> int:
    """Bu konuya ait TÜM logları siler (temiz başlangıç)."""
    df = _read_log()
    mask = (df["student_id"] == str(student_id)) & (df["subject"] == subject) & (df["topic"] == str(topic))
    n = int(mask.sum())
    if n:
        df = df[~mask].copy()
        _write_log(df)
    return n


# --- PLAN SİLME ----
def delete_topic_plan(student_id: str, subject: str, topic: str, also_logs: bool = True) -> dict:
    """
    Seçili konunun plan satırını siler; also_logs=True ise aynı konunun tüm loglarını da temizler.
    Dönüş: {"plan_deleted": N, "logs_deleted": M}
    """
    cur = _read_curr()
    m = (cur["student_id"] == str(student_id)) & (cur["subject"] == subject) & (cur["topic"] == str(topic))
    n_plan = int(m.sum())
    if n_plan:
        _write_curr(cur[~m].copy())

    n_logs = 0
    if also_logs:
        lg = _read_log()
        lm = (lg["student_id"] == str(student_id)) & (lg["subject"] == subject) & (lg["topic"] == str(topic))
        n_logs = int(lm.sum())
        if n_logs:
            _write_log(lg[~lm].copy())

    return {"plan_deleted": n_plan, "logs_deleted": n_logs}


def delete_subject_plan(student_id: str, subject: str, also_logs: bool = True) -> dict:
    """
    Bir dersin TÜM planını siler; also_logs=True ise o derse ait TÜM logları da temizler.
    Dönüş: {"plan_deleted": N, "logs_deleted": M}
    """
    cur = _read_curr()
    m = (cur["student_id"] == str(student_id)) & (cur["subject"] == subject)
    n_plan = int(m.sum())
    if n_plan:
        _write_curr(cur[~m].copy())

    n_logs = 0
    if also_logs:
        lg = _read_log()
        lm = (lg["student_id"] == str(student_id)) & (lg["subject"] == subject)
        n_logs = int(lm.sum())
        if n_logs:
            _write_log(lg[~lm].copy())

    return {"plan_deleted": n_plan, "logs_deleted": n_logs}
