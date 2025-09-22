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


# --- ASSIGNMENTS → PDF -------------------------------------------------------
def assignments_to_pdf(assign_df: pd.DataFrame, student_name: str, week_start, week_end) -> bytes:
    """
    Ödevleri A4 dikey, hizaları sabit bir tablo düzeninde PDF'e çevirir.
    Sütunlar: [ ] | Konu | Hedef | Kaynak
    """
    import io, textwrap
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.patches as patches

    # ---------- Yardımcılar ----------
    def _fmt_minutes(m: int) -> str:
        m = int(m); h, r = divmod(m, 60)
        return f"{h}s {r}dk" if h else f"{r}dk"

    def _fmt_amount(birim: str, miktar) -> str:
        try: miktar = int(miktar)
        except Exception: pass
        if birim == "Dakika": return _fmt_minutes(miktar)
        if birim == "Soru":   return f"{miktar} Soru"
        if birim == "Video":  return f"{miktar} Video"
        return f"{miktar} {birim}" if birim else str(miktar)

    def _wrap(s: str, max_chars: int) -> list[str]:
        s = str(s or "").strip()
        if not s: return [""]
        return textwrap.wrap(s, width=max_chars, break_long_words=False, break_on_hyphens=True)

    buf = io.BytesIO()

    # ---------- Boş liste ise tek sayfa ----------
    if assign_df is None or assign_df.empty:
        with PdfPages(buf) as pdf:
            fig = plt.figure(figsize=(8.27, 11.69), dpi=150)  # A4
            plt.axis("off")
            fig.text(0.5, 0.94, f"Ödev Listesi — {student_name}", ha="center", va="top",
                     fontsize=16, fontweight="bold")
            fig.text(0.5, 0.90, f"Hafta: {week_start} — {week_end}", ha="center", va="top", fontsize=12)
            fig.text(0.5, 0.50, "Bu hafta için ödev bulunmuyor.", ha="center", va="center", fontsize=12)
            pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
        return buf.getvalue()

    # ---------- Stil / Yerleşim ----------
    LEFT, RIGHT, TOP, BOTTOM = 0.07, 0.07, 0.07, 0.08
    HEADER_H = 0.030
    LINE_H   = 0.020
    PAD_T    = 0.006   # satır içi üst boşluk
    PAD_B    = 0.004   # satır içi alt boşluk
    GAP      = 0.004   # satırlar arası boşluk
    MIN_Y    = 0.05

    COLS = {"check": 0.04, "konu": 0.55, "hedef": 0.14, "kaynak": 0.27}
    X_CHECK  = 0
    X_KONU   = X_CHECK + COLS["check"]
    X_HEDEF  = X_KONU  + COLS["konu"]
    X_KAYNAK = X_HEDEF + COLS["hedef"]

    CHAR_LIMIT = {"konu": 70, "hedef": 18, "kaynak": 36}

    GREY_BG   = (246/255, 248/255, 251/255)
    HEADER_BG = (232/255, 236/255, 242/255)
    BORDER    = (205/255, 210/255, 218/255)
    PALETTE   = [
        (64/255, 120/255, 242/255),
        (0/255, 170/255, 136/255),
        (240/255, 98/255, 94/255),
        (246/255, 178/255, 51/255),
        (156/255, 105/255, 226/255),
        (61/255, 213/255, 152/255),
    ]
    subj_color = {}

    # ---------- Sayfa kurucu ----------
    def new_page(page_no: int):
        page_no += 1
        fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
        ax = fig.add_axes([LEFT, BOTTOM, 1-LEFT-RIGHT, 1-TOP-BOTTOM])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

        fig.text(0.5, 1-TOP+0.01, f"Ödev Listesi — {student_name}", ha="center", va="top",
                 fontsize=16, fontweight="bold")
        fig.text(0.5, 1-TOP-0.02, f"Hafta: {week_start} — {week_end}",
                 ha="center", va="top", fontsize=12)
        fig.text(0.5, BOTTOM-0.03, f"Sayfa {page_no}", ha="center", va="bottom",
                 fontsize=9, color=(0.3, 0.3, 0.3))

        # tablo başlığı
        ax.add_patch(patches.Rectangle((0, 1-0.10), 1, HEADER_H, facecolor=HEADER_BG, edgecolor=BORDER, linewidth=0.8))
        ax.text(X_KONU + COLS["konu"]/2,   1-0.10 + HEADER_H/2, "Konu",   ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(X_HEDEF + COLS["hedef"]/2, 1-0.10 + HEADER_H/2, "Hedef",  ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(X_KAYNAK + COLS["kaynak"]/2,1-0.10 + HEADER_H/2, "Kaynak", ha="center", va="center", fontsize=11, fontweight="bold")

        # dikey kolon çizgileri
        ax.plot([X_KONU, X_KONU],     [0, 1], color=BORDER, linewidth=0.6)
        ax.plot([X_HEDEF, X_HEDEF],   [0, 1], color=BORDER, linewidth=0.6)
        ax.plot([X_KAYNAK, X_KAYNAK], [0, 1], color=BORDER, linewidth=0.6)

        y_start = 1-0.10-HEADER_H - GAP
        return fig, ax, page_no, y_start

    # ---------- Çiziciler ----------
    def draw_subject(ax, subject: str, y: float) -> float:
        bar_h = LINE_H * 1.2
        if subject not in subj_color:
            subj_color[subject] = PALETTE[len(subj_color) % len(PALETTE)]
        color = subj_color[subject]
        ax.add_patch(patches.Rectangle((0, y - bar_h), 1, bar_h, facecolor=color, edgecolor=color))
        ax.text(0.006, y - bar_h/2, f"[{subject}]", ha="left", va="center", fontsize=11,
                color="white", fontweight="bold")
        return y - (bar_h + GAP)

    def row_height(konu_wrapped, hedef_wrapped, kaynak_wrapped) -> float:
        max_lines = max(len(konu_wrapped), len(hedef_wrapped), len(kaynak_wrapped))
        return PAD_T + max_lines*LINE_H + PAD_B

    def draw_row(ax, konu_wrapped, hedef_wrapped, kaynak_wrapped, y: float) -> float:
        h = row_height(konu_wrapped, hedef_wrapped, kaynak_wrapped)

        # arka plan
        ax.add_patch(patches.Rectangle((0, y-h), 1, h, facecolor=GREY_BG, edgecolor=BORDER, linewidth=0.5))
        # checkbox
        ax.add_patch(patches.Rectangle((0.006, y - PAD_T - 0.014), 0.018, 0.018,
                                       facecolor="white", edgecolor=BORDER, linewidth=0.8))

        # metinler (tepeye hizalı)
        # Konu
        yy = y - PAD_T
        for s in konu_wrapped:
            ax.text(X_KONU + 0.006, yy, s, ha="left", va="top", fontsize=10)
            yy -= LINE_H

        # Hedef
        yy = y - PAD_T
        for s in hedef_wrapped:
            ax.text(X_HEDEF + COLS["hedef"]/2, yy, s, ha="center", va="top", fontsize=10)
            yy -= LINE_H

        # Kaynak
        yy = y - PAD_T
        for s in kaynak_wrapped:
            ax.text(X_KAYNAK + 0.006, yy, s, ha="left", va="top", fontsize=10)
            yy -= LINE_H

        # satır alt çizgisi
        ax.plot([0, 1], [y-h, y-h], color=BORDER, linewidth=0.6)

        return y - h - GAP

    # ---------- Veri ----------
    df = assign_df.copy()
    for col in ["ders", "konu", "birim", "miktar"]:
        if col not in df.columns: df[col] = ""
    df["hedef_txt"] = df.apply(lambda r: _fmt_amount(str(r["birim"]), r["miktar"]), axis=1)
    df = df.sort_values(["ders", "konu", "kaynak"]).reset_index(drop=True)

    # ---------- PDF ----------
    with PdfPages(buf) as pdf:
        fig, ax, page_no, y = new_page(0)
        current_subject = None

        for ders, sub in df.groupby("ders", sort=False):
            # yer yoksa sayfa ata
            need = LINE_H * 1.2 + GAP
            if y - need < MIN_Y:
                pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
                fig, ax, page_no, y = new_page(page_no)

            y = draw_subject(ax, ders, y)
            current_subject = ders

            for _, r in sub.iterrows():
                konu_w   = _wrap(str(r["konu"]),      CHAR_LIMIT["konu"])
                hedef_w  = _wrap(str(r["hedef_txt"]), CHAR_LIMIT["hedef"])
                kaynak_w = _wrap(str(r.get("kaynak") or ""), CHAR_LIMIT["kaynak"])

                h_need = row_height(konu_w, hedef_w, kaynak_w) + GAP
                if y - h_need < MIN_Y:
                    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)
                    fig, ax, page_no, y = new_page(page_no)
                    # yeni sayfada aynı ders başlığını tekrar bas
                    y = draw_subject(ax, current_subject, y)

                y = draw_row(ax, konu_w, hedef_w, kaynak_w, y)

        pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)

    return buf.getvalue()
