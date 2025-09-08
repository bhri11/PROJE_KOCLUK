# core/channel_features.py
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CSV = DATA / "channel_features.csv"

_COLS = [
    "channel_id",   # opsiyonel, artan id
    "name",         # kanal adı
    "subject",      # Türkçe / Paragraf / Dil Bilgisi / (ileride Matematik ...)
    "difficulty",   # Başlangıç / Orta / İleri
    "tags",         # ; ile ayrılmış (örn: "kamp; konu anlatımı; soru çözümü")
    "avg_duration", # ortalama süre (dakika, tamsayı)
    "video_count",  # yaklaşık video sayısı (tamsayı)
    "playlists",    # kısa liste/seri adları (; ile ayrılmış)
    "notes"         # serbest metin
]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLS)

def load_channels() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    if not CSV.exists() or CSV.stat().st_size == 0:
        _empty_df().to_csv(CSV, index=False, encoding="utf-8")
        return _empty_df()
    try:
        df = pd.read_csv(CSV, encoding="utf-8")
    except pd.errors.EmptyDataError:
        df = _empty_df()
    for c in _COLS:
        if c not in df.columns:
            df[c] = ""
    for c in ["channel_id","avg_duration","video_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df[_COLS]

def list_by_subject(subject: str) -> pd.DataFrame:
    df = load_channels()
    sub = df[df["subject"].str.strip().str.lower() == subject.strip().lower()].copy()
    # basit sıralama: seviye + ad
    level_order = {"Başlangıç":0,"Orta":1,"İleri":2}
    sub["__ord"] = sub["difficulty"].map(level_order).fillna(9).astype(int)
    return sub.sort_values(["__ord","name"]).drop(columns="__ord").reset_index(drop=True)

def get_channel(name: str, subject: str | None = None) -> pd.Series | None:
    df = load_channels()
    m = df["name"].str.strip().str.lower() == name.strip().lower()
    if subject:
        m &= df["subject"].str.strip().str.lower() == subject.strip().lower()
    sub = df[m]
    return None if sub.empty else sub.iloc[0]

def _chip(text: str) -> str:
    return f"<span style='display:inline-block;padding:.18rem .5rem;border:1px solid #2a2f3a;border-radius:.6rem;margin:.12rem .2rem 0 0;background:#111827'>{text}</span>"

def render_channel_card(row: pd.Series) -> str:
    name = row.get("name","")
    subject = row.get("subject","")
    diff = row.get("difficulty","")
    tags = [t.strip() for t in str(row.get("tags","")).split(";") if t.strip()]
    playlists = [p.strip() for p in str(row.get("playlists","")).split(";") if p.strip()]
    notes = row.get("notes","")
    avg = int(row.get("avg_duration",0))
    vcount = int(row.get("video_count",0))

    chips = "".join(_chip(x) for x in ([subject, diff] + tags if any([subject,diff]) else tags))
    pl_html = ""
    if playlists:
        items = "".join(f"<li>{p}</li>" for p in playlists)
        pl_html = f"<ul style='margin:.2rem 0 .2rem .9rem;'>{items}</ul>"

    meta = []
    if avg: meta.append(f"Ortalama süre: {avg} dk")
    if vcount: meta.append(f"Video adedi: ~{vcount}")
    meta_html = f"<div style='opacity:.85;margin:.15rem 0'>{' • '.join(meta)}</div>" if meta else ""

    return f"""
<div style="border:1px solid #2a2f3a;border-radius:12px;padding:12px 16px;margin:8px 0;">
  <div style="font-weight:700;font-size:1.05rem;margin-bottom:.25rem">{name}</div>
  <div style="margin-bottom:.5rem">{chips}</div>
  {meta_html}
  {pl_html}
  <div style="opacity:.9">{notes}</div>
</div>
"""
