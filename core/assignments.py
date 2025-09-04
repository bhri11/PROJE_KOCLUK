# core/assignments.py
from pathlib import Path
from datetime import date, timedelta
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSIGN_PATH = DATA / "assignments.csv"

def week_start_of(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Pazartesi

def _empty_df() -> pd.DataFrame:
    cols = ["week_start","student_id","ders","konu","birim","miktar","kaynak","durum"]
    return pd.DataFrame(columns=cols)

def _legacy_upgrade(df: pd.DataFrame) -> pd.DataFrame:
    if "birim" not in df.columns and "hedef_tur" in df.columns:
        df["birim"] = df["hedef_tur"]
    if "miktar" not in df.columns and "hedef_deger" in df.columns:
        df["miktar"] = df["hedef_deger"]
    if "kaynak" not in df.columns:
        df["kaynak"] = ""
    drop_cols = [c for c in ["hedef_tur","hedef_deger"] if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")
    return df

def load_assignments() -> pd.DataFrame:
    if not ASSIGN_PATH.exists():
        return _empty_df()
    df = pd.read_csv(ASSIGN_PATH, encoding="utf-8")
    if "week_start" in df.columns:
        df["week_start"] = pd.to_datetime(df["week_start"]).dt.date
    if "student_id" not in df.columns:
        df["student_id"] = 1
    df = _legacy_upgrade(df)
    if "miktar" in df.columns:
        df["miktar"] = pd.to_numeric(df["miktar"], errors="coerce").fillna(0).astype(int)
    if "durum" in df.columns:
        df["durum"] = df["durum"].astype(bool)
    if "kaynak" in df.columns:
        df["kaynak"] = df["kaynak"].fillna("").astype(str)
    return df[["week_start","student_id","ders","konu","birim","miktar","kaynak","durum"]]

def save_assignments(df: pd.DataFrame):
    out = df.copy()
    out.to_csv(ASSIGN_PATH, index=False, encoding="utf-8")

def get_assignments(student_id: int, week_start: date) -> pd.DataFrame:
    df = load_assignments()
    return df[(df["student_id"] == student_id) & (df["week_start"] == week_start)].copy()

def add_assignments(student_id: int, week_start: date, ders: str, konular: list[str],
                    birim: str, miktar: int, kaynak: str = ""):
    df = load_assignments()
    rows = []
    for konu in konular:
        rows.append({
            "week_start": week_start,
            "student_id": int(student_id),
            "ders": ders,
            "konu": konu,
            "birim": birim,
            "miktar": int(miktar),
            "kaynak": (kaynak or "").strip(),
            "durum": False
        })
    df_new = pd.concat([df, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
        subset=["week_start","student_id","ders","konu","birim","kaynak"], keep="last"
    )
    save_assignments(df_new)

def add_bulk(rows: list[dict]):
    """rows: week_start, student_id, ders, konu, birim, miktar, kaynak, durum"""
    if not rows:
        return
    df = load_assignments()
    df_new = pd.concat([df, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
        subset=["week_start","student_id","ders","konu","birim","kaynak"], keep="last"
    )
    save_assignments(df_new)

def update_status(student_id: int, week_start: date, ders: str, konu: str, done: bool,
                  birim: str | None = None, kaynak: str | None = None):
    df = load_assignments()
    mask = (
        (df["student_id"] == int(student_id)) &
        (df["week_start"] == week_start) &
        (df["ders"] == ders) &
        (df["konu"] == konu)
    )
    if birim is not None:
        mask = mask & (df["birim"] == birim)
    if kaynak is not None:
        k = (kaynak or "").strip()
        mask = mask & (df["kaynak"].fillna("") == k)
    if mask.any():
        df.loc[mask, "durum"] = bool(done)
        save_assignments(df)
