from datetime import datetime, timedelta
import hashlib
import pandas as pd

def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")

def plan_to_ics(dated_plan: pd.DataFrame, start_time="19:00"):
    """
    dated_plan: columns -> date (date/datetime), topic (str), minutes (int)
    Bir gün için birden çok satır varsa ardışık bloklar halinde arka arkaya konur.
    """
    # Gün bazında grupla
    out = []
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TYT-Kocluk//Planner v0.1//TR",
    ]
    out.extend(header)

    for day, block in dated_plan.groupby("date"):
        h, m = map(int, start_time.split(":"))
        start_dt = datetime(day.year, day.month, day.day, h, m, 0)

        for _, row in block.iterrows():
            dur = int(row["minutes"])
            end_dt = start_dt + timedelta(minutes=dur)
            uid_src = f"{day.isoformat()}_{row['topic']}_{dur}".encode("utf-8")
            uid = hashlib.sha1(uid_src).hexdigest()[:12] + "@tyt-kocluk"
            lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART:{_fmt_dt(start_dt)}",
                f"DTEND:{_fmt_dt(end_dt)}",
                f"SUMMARY:Çalışma - {row['topic']}",
                "END:VEVENT",
            ]
            out.extend(lines)
            start_dt = end_dt  # bir sonraki blok, bir öncekinin bitişinden başlar

    out.append("END:VCALENDAR")
    return "\r\n".join(out).encode("utf-8")
