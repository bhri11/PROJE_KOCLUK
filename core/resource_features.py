# core/resource_features.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FEATS = DATA / "resource_features.csv"

_COLS = [
    "resource_id",   # resources.csv ile bağlamak için (opsiyonel ama önerilir)
    "name",          # kaynak adı (eşlemede kullanılır)
    "subject",       # Türkçe / Paragraf / Dil Bilgisi / Matematik ... (genişleyebilir)
    "type",          # Soru / Video
    "difficulty",    # Başlangıç / Orta / İleri
    "tags",          # ; ile ayrılmış kısa etiketler (örn: "video çözümlü; ÖSYM yakın")
    "bullets",       # | ile ayrılmış kısa maddeler (kartta noktalı liste olur)
    "notes"          # serbest metin (alt açıklama)
]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLS)

def load_resource_features() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    if not FEATS.exists() or FEATS.stat().st_size == 0:
        _empty_df().to_csv(FEATS, index=False, encoding="utf-8")
        return _empty_df()
    try:
        df = pd.read_csv(FEATS, encoding="utf-8")
    except pd.errors.EmptyDataError:
        df = _empty_df()
    # tip düzeltmeleri
    if "resource_id" in df.columns:
        df["resource_id"] = pd.to_numeric(df["resource_id"], errors="coerce").fillna(0).astype(int)
    for c in _COLS:
        if c not in df.columns:
            df[c] = ""
    return df[_COLS]

def get_feature(subject: str | None = None, name: str | None = None, resource_id: int | None = None) -> pd.Series | None:
    """Önce id ile, sonra (subject+name) ile eşleştirir."""
    df = load_resource_features()
    sub = df
    if resource_id:
        sub = sub[sub["resource_id"] == int(resource_id)]
    if name:
        sub = sub[sub["name"].str.strip().str.lower() == str(name).strip().lower()]
    if subject:
        sub = sub[sub["subject"].str.strip().str.lower() == subject.strip().lower()]
    if sub.empty:
        return None
    return sub.iloc[0]

def list_by_subject(subject: str) -> pd.DataFrame:
    df = load_resource_features()
    return df[df["subject"].str.strip().str.lower() == subject.strip().lower()]\
             .sort_values(["difficulty","name"]).reset_index(drop=True)

def _chip(text: str) -> str:
    return f"<span style='display:inline-block;padding:.18rem .5rem;border:1px solid #2a2f3a;border-radius:.6rem;margin:.12rem .2rem 0 0;background:#111827'>{text}</span>"

def render_feature_card(row: pd.Series) -> str:
    """Streamlit st.markdown(..., unsafe_allow_html=True) içinde kullan."""
    name = row.get("name","")
    subject = row.get("subject","")
    typ = row.get("type","")
    diff = row.get("difficulty","")
    tags = [t.strip() for t in str(row.get("tags","")).split(";") if t.strip()]
    bullets = [b.strip() for b in str(row.get("bullets","")).split("|") if b.strip()]
    notes = row.get("notes","")

    chips = "".join(_chip(x) for x in ([subject, typ, diff] + tags if any([subject,typ,diff]) else tags))
    bullet_html = "".join(f"<li>{b}</li>" for b in bullets)

    return f"""
<div style="border:1px solid #2a2f3a;border-radius:12px;padding:12px 16px;margin:8px 0;">
  <div style="font-weight:700;font-size:1.05rem;margin-bottom:.25rem">{name}</div>
  <div style="margin-bottom:.5rem">{chips}</div>
  {'<ul style="margin:.3rem 0 .2rem .9rem;">'+bullet_html+'</ul>' if bullet_html else ''}
  <div style="opacity:.9">{notes}</div>
</div>
"""
