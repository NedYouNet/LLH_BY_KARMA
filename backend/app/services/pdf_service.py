"""
Автогенерация стандартизированного PDF-профиля кандидата (требование ТЗ).

Используем reportlab. Для кириллицы нужен шрифт с русскими буквами — DejaVu.
В Docker-образе он ставится пакетом fonts-dejavu-core; локально ищем в системе.
"""
import io
import os
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import CandidateProfile
from app.reference import GRADE_NAME, SPEC_NAME, WORK_FORMATS, category_label

WORK_FORMAT_NAME = {w["code"]: w["name"] for w in WORK_FORMATS}

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
_FONT = "Helvetica"
for path in _FONT_CANDIDATES:
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont("Main", path))
        bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
        pdfmetrics.registerFont(TTFont("Main-Bold", bold_path if os.path.exists(bold_path) else path))
        pdfmetrics.registerFontFamily("Main", normal="Main", bold="Main-Bold", italic="Main", boldItalic="Main-Bold")
        _FONT = "Main"
        break

FSP_BLUE = colors.HexColor("#1F4E9E")


def build_profile_pdf(c: CandidateProfile, email: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"Профиль {c.full_name}")
    h1 = ParagraphStyle("h1", fontName=_FONT, fontSize=18, leading=22, textColor=FSP_BLUE)
    h2 = ParagraphStyle("h2", fontName=_FONT, fontSize=12, leading=16, textColor=FSP_BLUE, spaceBefore=8)
    body = ParagraphStyle("b", fontName=_FONT, fontSize=10, leading=14)

    def row(k, v):
        return [Paragraph(k, body), Paragraph(str(v) if v not in (None, "", []) else "—", body)]

    story = [Paragraph(c.full_name or "Кандидат", h1),
             Paragraph(category_label(c.specialization, c.grade) if c.grade_verified else
                       (f"{category_label(c.effective_specialization, c.effective_grade)} — заявлено, тест не пройден"
                        if c.effective_grade and c.effective_specialization else "Категория ещё не присвоена"), body),
             Spacer(1, 6)]
    info = Table([
        row("Специализация", SPEC_NAME.get(c.effective_specialization or "", "—")),
        row("Грейд", f"{GRADE_NAME.get(c.grade, c.grade)} (подтверждён тестом)" if c.grade_verified else
            (f"{GRADE_NAME.get(c.declared_grade, c.declared_grade)} (заявлен, не подтверждён)"
             if c.declared_grade else None)),
        row("Балл теста", f"{c.test_score:.0f}/100" if c.test_score is not None else None),
        row("Опыт", f"{c.experience_years:g} лет"),
        row("Город", c.city), row("Формат работы", WORK_FORMAT_NAME.get(c.work_format or "", c.work_format)),
        row("Email", c.contact_email or email), row("Телефон", c.phone), row("Telegram", c.telegram),
    ], colWidths=[55 * mm, 115 * mm])
    info.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                              ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [info, Paragraph("Навыки", h2), Paragraph(", ".join(c.skills or []) or "—", body)]
    if c.soft_skills:
        story += [Paragraph("Soft skills", h2), Paragraph(", ".join(c.soft_skills), body)]
    if c.about:
        story += [Paragraph("О себе", h2), Paragraph(c.about.replace("\n", "<br/>"), body)]
    story.append(Paragraph("Достижения ФСП", h2))
    if c.fsp_achievements:
        for a in c.fsp_achievements:
            story.append(Paragraph(f"• {a.get('year', '')} — {a.get('event')} ({a.get('level_name', '')}), "
                                   f"{a.get('discipline', '')}: <b>{a.get('result', '')}</b>", body))
    else:
        story.append(Paragraph("Нет подтверждённых достижений ФСП", body))
    story += [Spacer(1, 12), Paragraph(
        f"Сформировано платформой FSP Talent {datetime.now(timezone.utc):%d.%m.%Y}. "
        "Категория и грейд присвоены по результатам тестирования, достижения подтверждены реестром ФСП.",
        ParagraphStyle("f", fontName=_FONT, fontSize=8, textColor=colors.grey))]
    doc.build(story)
    return buf.getvalue()
