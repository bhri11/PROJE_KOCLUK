# core/resource_features.py
from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import pandas as pd
import html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FEATURES = DATA / "resource_features.csv"

# Beklenen kolonlar
REQ_COLS = [
    "resource_id", "name", "subject", "type",
    "difficulty", "tags", "bullets", "notes"
]

def _init_csv_if_needed() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if not FEATURES.exists() or FEATURES.stat().st_size == 0:
        pd.DataFrame(columns=REQ_COLS).to_csv(FEATURES, index=False, encoding="utf-8")

def _split_multi(s: str) -> List[str]:
    """; | , ayraçlarını destekleyerek parçala."""
    if not isinstance(s, str):
        return []
    parts: List[str] = []
    for chunk in s.replace("|", ";").replace(",", ";").split(";"):
        t = chunk.strip()
        if t:
            parts.append(t)
    return parts

def load_features() -> pd.DataFrame:
    """resource_features.csv dosyasını güvenli şekilde yükle."""
    _init_csv_if_needed()
    try:
        df = pd.read_csv(FEATURES, encoding="utf-8")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=REQ_COLS)

    # Eksik kolonları tamamla
    for c in REQ_COLS:
        if c not in df.columns:
            df[c] = ""

    # Tip/boşluk düzeltme
    df["resource_id"] = pd.to_numeric(df["resource_id"], errors="coerce").fillna(0).astype(int)
    for c in ["name","subject","type","difficulty","tags","bullets","notes"]:
        df[c] = df[c].astype(str).fillna("").str.strip()

    return df[REQ_COLS]

def get_feature(subject: str, name: str) -> Optional[pd.Series]:
    """
    Önce subject+name ile tam eşleşme; yoksa sadece name ile fallback.
    Kart bulunamazsa None döner.
    """
    df = load_features()
    # Tam eşleşme (case/boşluk esnek)
    mask_full = (
        (df["name"].str.lower() == name.strip().lower()) &
        (df["subject"].str.lower() == subject.strip().lower())
    )
    if mask_full.any():
        return df.loc[mask_full].iloc[0]

    # Fallback: sadece ada göre
    mask_name = (df["name"].str.lower() == name.strip().lower())
    if mask_name.any():
        return df.loc[mask_name].iloc[0]

    return None

def render_feature_card(row: pd.Series) -> str:
    """
    Özellik satırını HTML kartı olarak döndürür.
    (Streamlit içinde st.markdown(..., unsafe_allow_html=True) ile basılır.)
    """
    title = html.escape(str(row.get("name", "")))
    subject = html.escape(str(row.get("subject", "")))
    rtype = html.escape(str(row.get("type", "")))
    level = html.escape(str(row.get("difficulty", "")))

    tags = _split_multi(row.get("tags", ""))
    bullets = _split_multi(row.get("bullets", ""))
    notes = html.escape(str(row.get("notes", "")))

    # Chipler
    chips = []
    if subject: chips.append(f"<span class='goal-chip'>{subject}</span>")
    if rtype:   chips.append(f"<span class='goal-chip'>{rtype}</span>")
    if level:   chips.append(f"<span class='goal-chip'>{level}</span>")
    for t in tags:
        chips.append(f"<span class='goal-chip'>{html.escape(t)}</span>")
    chips_html = " ".join(chips)

    # Bullet list
    bullets_html = ""
    if bullets:
        items = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
        bullets_html = f"<ul>{items}</ul>"

    card_html = f"""
    <div class="card">
      <div class="title">{title}</div>
      <div class="meta">{chips_html}</div>
      {bullets_html}
      <div class="help-meta">{notes}</div>
    </div>
    """
    return card_html
