from pathlib import Path
from datetime import datetime
import pandas as pd
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

# ---------- Settings ----------
def load_settings() -> dict:
    p = DATA / "settings.json"
    with p.open("r", encoding="utf-8-sig") as f:
        raw = f.read().strip()
        if not raw:
            raise ValueError("settings.json boş.")
        s = json.loads(raw)
    s.setdefault("level", "beginner")
    s.setdefault("daily_minutes", 90)
    s.setdefault("study_days", ["Mon","Wed","Fri","Sun"])
    s.setdefault("start_date", datetime.now().date().isoformat())
    s.setdefault("locale", "tr-TR")
    return s

def save_settings(settings: dict) -> None:
    p = DATA / "settings.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def level_to_col(level: str) -> str:
    m = {"beginner": "beginner_min", "intermediate": "intermediate_min", "advanced": "advanced_min"}
    return m.get(level, "beginner_min")

# ---------- Topics ----------
def load_topics(level_col: str) -> pd.DataFrame:
    """topics.csv'yi ; veya , ayraçla güvenli şekilde okur."""
    p = DATA / "topics.csv"
    # Önce ; ile dene (önerilen format)
    try:
        df = pd.read_csv(p, sep=";", encoding="utf-8")
        if df.shape[1] < 3:
            raise ValueError("Sep=';' ile sütun sayısı anormal.")
    except Exception:
        # Geriye dönük: , + düzgün tırnaklı CSV
        df = pd.read_csv(p, encoding="utf-8")
    df = df.sort_values(["subject", "order"]).reset_index(drop=True)
    df["topic"] = df["topic"].astype(str).str.strip()
    df = df[df["topic"] != ""].copy()
    df = df[~df["topic"].isin(["-", "—", "–", "_"])].copy()

    df["target_min"] = df[level_col].astype(int)
    return df

# ---------- Students ----------
_STUDENTS_PATH = DATA / "students.csv"

def _ensure_students_file():
    if not _STUDENTS_PATH.exists():
        df = pd.DataFrame([{
            "student_id": 1,
            "student_name": "Öğrenci A",
            "active": True,
            "created_at": datetime.now().isoformat(timespec="seconds")
        }])
        df.to_csv(_STUDENTS_PATH, index=False, encoding="utf-8")

def load_students() -> pd.DataFrame:
    _ensure_students_file()
    df = pd.read_csv(_STUDENTS_PATH, encoding="utf-8")
    if "active" not in df.columns: df["active"] = True
    if "created_at" not in df.columns: df["created_at"] = datetime.now().isoformat(timespec="seconds")
    return df

def save_students(df: pd.DataFrame):
    df.to_csv(_STUDENTS_PATH, index=False, encoding="utf-8")

def _next_student_id(df: pd.DataFrame) -> int:
    if df.empty: return 1
    return int(df["student_id"].max()) + 1

def student_exists(name: str) -> bool:
    df = load_students()
    name_cf = (name or "").strip().casefold()
    return any(str(x).strip().casefold() == name_cf for x in df["student_name"].tolist())

def add_student(name: str) -> int:
    if not name or not name.strip():
        raise ValueError("Öğrenci adı boş olamaz.")
    if student_exists(name):
        raise ValueError("Bu isimde bir öğrenci zaten var.")
    df = load_students()
    new_id = _next_student_id(df)
    row = {"student_id": new_id, "student_name": name.strip(), "active": True,
           "created_at": datetime.now().isoformat(timespec="seconds")}
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_students(df2)
    return new_id

def rename_student(student_id: int, new_name: str):
    if not new_name or not new_name.strip():
        raise ValueError("Yeni ad boş olamaz.")
    df = load_students()
    if student_exists(new_name):
        raise ValueError("Bu isimde bir öğrenci zaten var.")
    mask = df["student_id"] == int(student_id)
    if not mask.any(): raise ValueError("Öğrenci bulunamadı.")
    df.loc[mask, "student_name"] = new_name.strip()
    save_students(df)

def deactivate_student(student_id: int):
    df = load_students()
    mask = df["student_id"] == int(student_id)
    if not mask.any(): raise ValueError("Öğrenci bulunamadı.")
    df.loc[mask, "active"] = False
    save_students(df)

def reactivate_student(student_id: int):
    df = load_students()
    mask = df["student_id"] == int(student_id)
    if not mask.any(): raise ValueError("Öğrenci bulunamadı.")
    df.loc[mask, "active"] = True
    save_students(df)

# ---------- Progress ----------
def load_progress() -> pd.DataFrame:
    p = DATA / "progress.csv"
    try:
        df = pd.read_csv(p, encoding="utf-8", parse_dates=["date"])
    except Exception:
        df = pd.DataFrame(columns=["date","topic","minutes","student_id"])
    if "student_id" not in df.columns:
        df["student_id"] = 1
    return df

def save_progress(df: pd.DataFrame):
    df.to_csv(DATA / "progress.csv", index=False, encoding="utf-8")

def append_progress(date_str: str, topic: str, minutes: int, student_id: int = 1):
    df = load_progress()
    new_row = {"date": date_str, "topic": topic, "minutes": int(minutes), "student_id": int(student_id)}
    df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_progress(df2)
