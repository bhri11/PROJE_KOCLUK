# core/exam_reviews.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CSV = DATA / "exam_reviews.csv"

_COLS = [
    "exam_id",       # artan id
    "name",          # deneme adı / yayın
    "subject",       # örn: "Türkçe Genel" (ileride: Matematik Genel vs.)
    "exam_count",    # deneme sayısı
    "difficulty",    # 1-10
    "osym_fit",      # 1-10
    "solution_clarity", # 1-10 (video çözüm açıklığı)
    "layout",        # 1-10 (mizanpaj)
    "notes"          # opsiyonel açıklama
]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLS)

def load_exam_reviews() -> pd.DataFrame:
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
    # sayısal alanlar
    for c in ["exam_id","exam_count","difficulty","osym_fit","solution_clarity","layout"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df[_COLS]

Level = Literal["Başlangıç","Orta","İleri"]

def _center_score(x: float, target: float) -> float:
    """x (0-10) hedef 'target'a ne kadar yakın? 0-1 arası skor."""
    return max(0.0, 1.0 - abs(x - target) / 10.0)

def compute_match(row: pd.Series, level: Level = "Orta") -> float:
    """0-100 arası öneri skoru. Seviyeye göre ağırlıklar değişir."""
    diff = float(row["difficulty"])
    fit  = float(row["osym_fit"]) / 10.0
    sol  = float(row["solution_clarity"]) / 10.0
    lay  = float(row["layout"]) / 10.0

    if level == "Başlangıç":
        s_diff = _center_score(diff, 6.0)     # çok zor olmasın
        w = dict(diff=0.35, fit=0.25, sol=0.25, lay=0.15)
    elif level == "İleri":
        s_diff = _center_score(diff, 9.0)     # zorluk arıyoruz
        w = dict(diff=0.40, fit=0.30, sol=0.20, lay=0.10)
    else:  # Orta
        s_diff = _center_score(diff, 7.5)
        w = dict(diff=0.35, fit=0.25, sol=0.25, lay=0.15)

    score = 100.0 * (w["diff"]*s_diff + w["fit"]*fit + w["sol"]*sol + w["lay"]*lay)
    return round(score, 1)

def recommend_exams(subject: str, level: Level = "Orta", min_exams: int = 0) -> pd.DataFrame:
    df = load_exam_reviews()
    df = df[df["subject"].str.strip().str.lower() == subject.strip().lower()].copy()
    if min_exams:
        df = df[df["exam_count"] >= int(min_exams)]
    if df.empty:
        return df
    df["match"] = df.apply(lambda r: compute_match(r, level), axis=1)
    return df.sort_values(["match","exam_count"], ascending=[False, False]).reset_index(drop=True)

def render_exam_card(row: pd.Series) -> str:
    """Streamlit kartı (HTML)."""
    name = row.get("name","")
    subj = row.get("subject","")
    count = int(row.get("exam_count",0))
    diff = int(row.get("difficulty",0))
    fit  = int(row.get("osym_fit",0))
    sol  = int(row.get("solution_clarity",0))
    lay  = int(row.get("layout",0))
    notes = str(row.get("notes","")).strip()
    meta = f"🧪 {count} deneme • Zorluk {diff}/10 • ÖSYM Yakınlık {fit}/10 • Çözüm {sol}/10 • Mizanpaj {lay}/10"
    body = f"<div style='opacity:.9'>{notes}</div>" if notes else ""
    return f"""
<div style="border:1px solid #2a2f3a;border-radius:12px;padding:12px 16px;margin:8px 0;">
  <div style="font-weight:700;font-size:1.05rem;margin-bottom:.25rem">{name}</div>
  <div style="opacity:.85;margin-bottom:.35rem'>{subj}</div>
  <div style="margin-bottom:.35rem">{meta}</div>
  {body}
</div>
"""
