"""Export chat conversations to PDF (server-side, no heavy frontend libs)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from io import BytesIO

from fpdf import FPDF


def _safe_text(text: str) -> str:
    """Keep PDF core fonts happy; strip unsupported chars."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\n\t\x20-\x7e\u00a0-\u00ff]", "?", text)
    return text


def build_chat_pdf(
    messages: list[dict],
    *,
    mode: str = "both",
    session_id: str | None = None,
) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Header band
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(0, 0, 210, 32, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(14, 10)
    pdf.cell(0, 8, "LifeChanger - Impact Guide", ln=True)
    pdf.set_font("Helvetica", "", 9)
    exported = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_xy(14, 18)
    pdf.cell(90, 6, "Conversation export")
    pdf.set_xy(110, 18)
    pdf.cell(86, 6, exported, align="R")

    pdf.set_text_color(60, 60, 60)
    pdf.set_xy(14, 38)
    pdf.set_font("Helvetica", "", 9)
    meta = f"Mode: {mode}"
    if session_id:
        meta += f"  |  Session: {session_id[:24]}"
    pdf.multi_cell(182, 5, _safe_text(meta))
    pdf.ln(4)

    for msg in messages:
        role = msg.get("role", "assistant")
        if role not in ("user", "assistant"):
            continue

        is_user = role == "user"
        label = "You" if is_user else "Impact Guide"
        pdf.set_font("Helvetica", "B", 11)
        if is_user:
            pdf.set_text_color(37, 99, 235)
        else:
            pdf.set_text_color(5, 80, 60)
        pdf.multi_cell(182, 6, label)
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        body = _safe_text(msg.get("content") or "")
        pdf.multi_cell(182, 5, body)
        pdf.ln(2)

        charts = msg.get("charts") or []
        if charts:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(182, 5, "Charts:")
            pdf.set_font("Helvetica", "", 9)
            for chart in charts[:6]:
                title = _safe_text(chart.get("title") or "Chart")
                ctype = chart.get("type") or ""
                pdf.multi_cell(182, 5, f"  - {title} ({ctype})")
                for row in (chart.get("data") or [])[:10]:
                    label_r = _safe_text(str(row.get("label", "")))
                    val = row.get("value", "")
                    pdf.multi_cell(182, 4, f"      {label_r}: {val}")
            pdf.ln(2)

        pdf.set_draw_color(220, 220, 220)
        y = pdf.get_y()
        pdf.line(14, y, 196, y)
        pdf.ln(5)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
