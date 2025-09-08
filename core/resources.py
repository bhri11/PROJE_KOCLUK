# core/resources.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES  = DATA / "resources.csv"

REQUIRED_COLS = [
    "resource_id", "name", "type", "subject",
    "area", "difficulty", "total_items", "notes"
]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=REQUIRED_COLS)

def _init_csv_if_needed() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if not RES.exists() or RES.stat().st_size == 0:
        _empty_df().to_csv(RES, index=False, encoding="utf-8")

def load_resources() -> pd.DataFrame:
    _init_csv_if_needed()
    try:
        df = pd.read_csv(RES, encoding="utf-8")
    except pd.errors.EmptyDataError:
        df = _empty_df()

    # Eksik kolonları ekle
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = 0 if c in ("resource_id", "total_items") else ""

    # Tip ve boşluk düzeltmeleri
    df["resource_id"] = pd.to_numeric(df["resource_id"], errors="coerce").fillna(0).astype(int)
    df["total_items"]  = pd.to_numeric(df["total_items"],  errors="coerce").fillna(0).astype(int)
    for c in ["name","type","subject","area","difficulty","notes"]:
        df[c] = df[c].astype(str).fillna("").str.strip()

    return df[REQUIRED_COLS]

def save_resources(df: pd.DataFrame) -> None:
    df[REQUIRED_COLS].to_csv(RES, index=False, encoding="utf-8")

def get_resources(subject: Optional[str]=None,
                  type_: Optional[str]=None,
                  area: Optional[str]=None,
                  difficulty: Optional[str]=None) -> pd.DataFrame:
    """CSV’den toleranslı (case/boşluk duyarsız) filtreleme."""
    df = load_resources()
    if subject:
        df = df[df["subject"].str.lower() == subject.strip().lower()]
    if type_:
        df = df[df["type"].str.lower() == type_.strip().lower()]
    if area:
        df = df[df["area"].str.lower() == area.strip().lower()]
    if difficulty:
        df = df[df["difficulty"].str.lower() == difficulty.strip().lower()]
    return df.sort_values(["subject","area","difficulty","name"]).reset_index(drop=True)

def add_resource(name: str, type_: str, subject: str,
                 total_items: int = 0, notes: str = "",
                 area: str = "", difficulty: str = "") -> int:
    df = load_resources()
    new_id = (df["resource_id"].max() + 1) if not df.empty else 1
    row = {
        "resource_id": int(new_id),
        "name": name.strip(),
        "type": type_.strip(),
        "subject": subject.strip(),
        "area": area.strip(),
        "difficulty": difficulty.strip(),
        "total_items": int(total_items),
        "notes": notes.strip()
    }
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_resources(df2)
    return int(new_id)

def update_resource(resource_id: int, **kwargs) -> None:
    df = load_resources()
    mask = df["resource_id"] == int(resource_id)
    if not mask.any():
        raise ValueError("Kaynak bulunamadı.")
    for k, v in kwargs.items():
        if k in REQUIRED_COLS and k != "resource_id" and v is not None:
            df.loc[mask, k] = v
    save_resources(df)

def delete_resource(resource_id: int) -> None:
    df = load_resources()
    save_resources(df[df["resource_id"] != int(resource_id)])
