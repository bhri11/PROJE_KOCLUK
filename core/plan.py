from datetime import date, timedelta
import pandas as pd

def compute_status(topics: pd.DataFrame, progress: pd.DataFrame, student_id: int = 1):
    dfp = progress[progress["student_id"] == student_id].copy()
    done = dfp.groupby("topic", as_index=False)["minutes"].sum().rename(columns={"minutes":"done_min"})
    merged = topics.merge(done, on="topic", how="left")
    merged["done_min"] = merged["done_min"].fillna(0).astype(int)
    merged["remaining_min"] = (merged["target_min"] - merged["done_min"]).clip(lower=0)
    overall_done = int(merged["done_min"].sum())
    overall_target = int(merged["target_min"].sum())
    overall_pct = 0 if overall_target == 0 else round(100 * overall_done / overall_target, 1)
    return merged, overall_done, overall_target, overall_pct

def next_study_day(start_date: date, study_weekdays: list[int], base: date | None = None) -> date:
    d = base or start_date
    while d.weekday() not in study_weekdays:
        d += timedelta(days=1)
    return d

def get_study_dates(start_from: date, study_weekdays: list[int], days: int = 7):
    d = start_from
    out = []
    while len(out) < days:
        if d.weekday() in study_weekdays:
            out.append(d)
        d += timedelta(days=1)
    return out

def build_daily_plan(topics_status: pd.DataFrame, daily_minutes: int):
    left = daily_minutes
    plan_rows = []
    for _, row in topics_status.sort_values(["subject","order"]).iterrows():
        if left <= 0:
            break
        rem = int(row["remaining_min"])
        if rem <= 0:
            continue
        take = min(rem, left)
        plan_rows.append((row["topic"], int(take)))
        left -= take
    return plan_rows

def build_sequential_plan(topics_status: pd.DataFrame, daily_minutes: int, dates: list[date]) -> pd.DataFrame:
    ts = topics_status.copy()
    remaining = ts[["subject","order","topic","remaining_min"]].copy()
    remaining["remaining_min"] = remaining["remaining_min"].astype(int)

    rows = []
    for d in dates:
        left = daily_minutes
        for idx, row in remaining.sort_values(["subject","order"]).iterrows():
            if left <= 0:
                break
            rem = int(row["remaining_min"])
            if rem <= 0:
                continue
            take = min(rem, left)
            rows.append({"date": d, "topic": row["topic"], "minutes": int(take)})
            remaining.at[idx, "remaining_min"] = rem - take
            left -= take
    return pd.DataFrame(rows)
