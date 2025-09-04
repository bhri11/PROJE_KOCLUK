from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = DATA / "resources.csv"

_COLUMNS = ["resource_id","name","type","subject","total_items","notes"]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLUMNS)

def _ensure_res_initialized():
    DATA.mkdir(parents=True, exist_ok=True)
    if not RES.exists() or RES.stat().st_size == 0:
        _empty_df().to_csv(RES, index=False, encoding="utf-8")
        return
    try:
        pd.read_csv(RES, nrows=0, encoding="utf-8")
    except Exception:
        _empty_df().to_csv(RES, index=False, encoding="utf-8")

def load_resources() -> pd.DataFrame:
    _ensure_res_initialized()
    try:
        df = pd.read_csv(RES, encoding="utf-8")
    except pd.errors.EmptyDataError:
        _empty_df().to_csv(RES, index=False, encoding="utf-8")
        df = _empty_df()
    if "resource_id" in df.columns:
        df["resource_id"] = pd.to_numeric(df["resource_id"], errors="coerce").fillna(0).astype(int)
    if "total_items" in df.columns:
        df["total_items"] = pd.to_numeric(df["total_items"], errors="coerce").fillna(0).astype(int)
    for c in _COLUMNS:
        if c not in df.columns:
            df[c] = [] if c in ("name","type","subject","notes") else 0
    return df[_COLUMNS]

def save_resources(df: pd.DataFrame):
    df[_COLUMNS].to_csv(RES, index=False, encoding="utf-8")

def get_resources(subject: str | None = None, type_: str | None = None) -> pd.DataFrame:
    df = load_resources()
    if subject: df = df[df["subject"] == subject]
    if type_: df = df[df["type"] == type_]
    return df.sort_values(["subject","type","name"]).reset_index(drop=True)

def add_resource(name: str, type_: str, subject: str, total_items: int = 0, notes: str = "") -> int:
    df = load_resources()
    new_id = (df["resource_id"].max() + 1) if not df.empty else 1
    row = {"resource_id": int(new_id), "name": name.strip(), "type": type_.strip(),
           "subject": subject.strip(), "total_items": int(total_items), "notes": notes.strip()}
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_resources(df2)
    return int(new_id)

def update_resource(resource_id: int, **kwargs):
    df = load_resources()
    mask = df["resource_id"] == int(resource_id)
    if not mask.any(): raise ValueError("Kaynak bulunamadı.")
    for k, v in kwargs.items():
        if k in _COLUMNS and k != "resource_id" and v is not None:
            df.loc[mask, k] = v
    save_resources(df)

def delete_resource(resource_id: int):
    df = load_resources()
    df2 = df[df["resource_id"] != int(resource_id)]
    save_resources(df2)
