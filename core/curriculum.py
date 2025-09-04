# core/curriculum.py
from pathlib import Path
import pandas as pd
from .dataio import load_topics, level_to_col

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURR = DATA / "curriculum.csv"

_COLS = ["student_id","ders","order","konu","birim","miktar","kaynak"]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLS)

def load_curriculum() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    if not CURR.exists() or CURR.stat().st_size == 0:
        _empty_df().to_csv(CURR, index=False, encoding="utf-8")
        return _empty_df()
    df = pd.read_csv(CURR, encoding="utf-8")
    # tip düzeltmeleri
    for c in ["student_id","order","miktar"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in _COLS:
        if c not in df.columns:
            df[c] = "" if c in ("ders","konu","birim","kaynak") else 0
    return df[_COLS]

def save_curriculum(df: pd.DataFrame):
    df[_COLS].to_csv(CURR, index=False, encoding="utf-8")

def get_curriculum(student_id: int, ders: str | None = None) -> pd.DataFrame:
    df = load_curriculum()
    sub = df[df["student_id"] == int(student_id)].copy()
    if ders:
        sub = sub[sub["ders"] == ders]
    return sub.sort_values(["ders","order","konu"]).reset_index(drop=True)

def clear_curriculum(student_id: int, ders: str | None = None):
    df = load_curriculum()
    mask = df["student_id"] == int(student_id)
    if ders:
        mask = mask & (df["ders"] == ders)
    save_curriculum(df[~mask])

def generate_from_topics(student_id: int, level: str, ders: str | None = None, overwrite: bool = False):
    """
    topics.csv'den, seçilen 'level' sütununa göre curriculum oluşturur.
    level: 'beginner' | 'intermediate' | 'advanced'
    """
    level_col = level_to_col(level)
    topics = load_topics(level_col)
    if ders:
        topics = topics[topics["subject"] == ders]
    rows = []
    for _, r in topics.iterrows():
        rows.append({
            "student_id": int(student_id),
            "ders": r["subject"],
            "order": int(r["order"]),
            "konu": r["topic"],
            "birim": "Dakika",
            "miktar": int(r["target_min"]),
            "kaynak": ""
        })
    cur = load_curriculum()
    if overwrite:
        clear_curriculum(student_id, ders)
        cur = load_curriculum()
    out = pd.concat([cur, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
        subset=["student_id","ders","order","konu","birim","kaynak"], keep="last"
    )
    save_curriculum(out)

def pick_for_week(student_id: int, week_start, ders: str | None, konu_list: list[dict]) -> list[dict]:
    """
    Curriculum satırlarını 'assignments' için satırlara dönüştürür.
    konu_list: [{'konu': '...', 'miktar': 90, 'birim': 'Dakika', 'kaynak': ''}, ...]
    """
    rows = []
    for item in konu_list:
        rows.append({
            "week_start": week_start,
            "student_id": int(student_id),
            "ders": ders if ders else "",
            "konu": item["konu"],
            "birim": item.get("birim","Dakika"),
            "miktar": int(item["miktar"]),
            "kaynak": item.get("kaynak",""),
            "durum": False
        })
    return rows
