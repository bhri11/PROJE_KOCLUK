from pathlib import Path
import pandas as pd
import html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RF = DATA / "resource_features.csv"

_COLUMNS = [
    "resource_id", "name", "subject", "type", "difficulty",
    "tags", "bullets", "notes"
]

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLUMNS)

def _ensure_initialized():
    DATA.mkdir(parents=True, exist_ok=True)
    if not RF.exists() or RF.stat().st_size == 0:
        _empty_df().to_csv(RF, index=False, encoding="utf-8")
        return
    try:
        pd.read_csv(RF, nrows=1, encoding="utf-8")
    except Exception:
        _empty_df().to_csv(RF, index=False, encoding="utf-8")

def load_resource_features() -> pd.DataFrame:
    _ensure_initialized()
    try:
        df = pd.read_csv(RF, encoding="utf-8")
    except pd.errors.EmptyDataError:
        df = _empty_df()
        df.to_csv(RF, index=False, encoding="utf-8")
    # eksik kolonları tamamla
    for c in _columns_needed():
        if c not in df.columns:
            df[c] = "" if c not in ("resource_id",) else 0
    df["resource_id"] = pd.to_numeric(df["resource_id"], errors="coerce").fillna(0).astype(int)
    return df[_COLUMNS]

def _columns_needed():
    return _COLUMNS

def save_resource_features(df: pd.DataFrame):
    df[_COLUMNS].to_csv(RF, index=False, encoding="utf-8")

def upsert_resource_feature(
    resource_id: int,
    name: str,
    subject: str,
    type_: str,
    difficulty: str,
    tags: str | list[str] = "",
    bullets: str | list[str] = "",
    notes: str = ""
):
    df = load_resource_features()
    # normalize
    if isinstance(tags, list):    tags = "; ".join([t.strip() for t in tags if t.strip()])
    if isinstance(bullets, list): bullets = "|".join([b.strip() for b in bullets if b.strip()])

    mask = (df["resource_id"] == int(resource_id)) | ((df["name"] == name) & (df["subject"] == subject))
    row = {
        "resource_id": int(resource_id),
        "name": name.strip(),
        "subject": subject.strip(),
        "type": type_.strip(),
        "difficulty": difficulty.strip(),
        "tags": (tags or "").strip(),
        "bullets": (bullets or "").strip(),
        "notes": (notes or "").strip(),
    }
    if mask.any():
        for k, v in row.items():
            if k != "resource_id":
                df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    save_resource_features(df)

def list_by_subject(subject: str) -> pd.DataFrame:
    df = load_resource_features()
    if subject:
        df = df[df["subject"] == subject]
    return df.sort_values(["subject", "difficulty", "name"]).reset_index(drop=True)

def get_feature(subject: str, name: str) -> dict | None:
    df = load_resource_features()
    hit = df[(df["subject"] == subject) & (df["name"] == name)]
    if hit.empty:
        return None
    return hit.iloc[0].to_dict()

def render_feature_card(row_like: dict | pd.Series) -> str:
    """Kaynak özellik kartını HTML döndürür (Streamlit markdown ile render edilir)."""
    import html
    r = row_like if isinstance(row_like, dict) else row_like.to_dict()
    esc = html.escape

    base_chips = [
        f"<span class='goal-chip'>{esc(str(r.get('subject','')))}</span>",
        f"<span class='goal-chip'>{esc(str(r.get('type','')))}</span>",
        f"<span class='goal-chip'>{esc(str(r.get('difficulty','')))}</span>",
    ]

    extra_tags = []
    for t in str(r.get("tags","")).split(";"):
        t = t.strip()
        if t:
            extra_tags.append(f"<span class='goal-chip'>{esc(t)}</span>")

    bullets_html = ""
    bullets = [b.strip() for b in str(r.get("bullets","")).split("|") if b.strip()]
    if bullets:
        li = "".join(f"<li>{esc(b)}</li>" for b in bullets)
        bullets_html = f"<ul>{li}</ul>"

    # ÖNEMLİ: chip'leri boşlukla birleştir
    chips_html = " ".join(base_chips + extra_tags)

    notes_html = esc(str(r.get("notes","")))

    return (
        "<div class='card'>"
        f"<div class='title'>{esc(str(r.get('name','')))}</div>"
        f"<div class='chips'>{chips_html}</div>"
        f"{bullets_html}"
        f"<div class='help-meta'>{notes_html}</div>"
        "</div>"
    )
