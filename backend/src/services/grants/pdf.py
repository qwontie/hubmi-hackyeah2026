from functools import cache
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .notify import local
from .schemas import ApplicationOut

FONTS = Path(__file__).parent / "fonts"
INK = HexColor("#1b1b35")
MUTED = HexColor("#4a4a68")
ACCENT = HexColor("#4137a6")
STATUS_NAMES = {
    "draft": "Wersja robocza",
    "submitted": "Złożony",
    "in_review": "W ocenie",
    "accepted": "Przyjęty",
    "rejected": "Odrzucony",
}
FORM_NOTE = (
    "Dane wnioskodawcy i oświadczenia uzupełnia się w formularzu ROPS. Treść "
    "sekcji przygotowano w HubMi na podstawie pomysłu autora; fragmenty oznaczone "
    "jako do uzupełnienia wymagają informacji, których w pomyśle jeszcze nie ma."
)


@cache
def styles() -> dict[str, ParagraphStyle]:
    pdfmetrics.registerFont(TTFont("Geist", str(FONTS / "Geist-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Geist-SemiBold", str(FONTS / "Geist-SemiBold.ttf")))
    base = ParagraphStyle(
        "base", fontName="Geist", fontSize=10.5, leading=15, textColor=INK
    )
    return {
        "base": base,
        "badge": ParagraphStyle(
            "badge",
            parent=base,
            fontName="Geist-SemiBold",
            fontSize=9,
            textColor=ACCENT,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base,
            fontName="Geist-SemiBold",
            fontSize=18,
            leading=23,
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "meta", parent=base, fontSize=9.5, leading=13.5, textColor=MUTED
        ),
        "label": ParagraphStyle(
            "label",
            parent=base,
            fontName="Geist-SemiBold",
            fontSize=12.5,
            leading=17,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "hint": ParagraphStyle(
            "hint", parent=base, fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=4
        ),
        "missing": ParagraphStyle(
            "missing", parent=base, fontSize=9.5, leading=13.5, textColor=ACCENT
        ),
    }


def paragraphs(text: str, style: ParagraphStyle) -> list[Any]:
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return [Paragraph(escape(b).replace("\n", "<br/>"), style) for b in blocks]


def footer(canvas: Any, document: Any) -> None:  # noqa: ANN401
    canvas.saveState()
    canvas.setFont("Geist", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        20 * mm, 12 * mm, "HubMi, Małopolski Hub Innowacji Społecznych, ROPS w Krakowie"
    )
    canvas.drawRightString(190 * mm, 12 * mm, f"Strona {document.page}")
    canvas.restoreState()


def render(application: ApplicationOut) -> bytes:
    s = styles()
    story: list[Any] = []
    if application.call.demo:
        story.append(Paragraph("NABÓR POKAZOWY, NIE PRAWDZIWY NABÓR ROPS", s["badge"]))
    story.append(Paragraph(f"Wniosek nr {application.number}", s["badge"]))
    story.append(Paragraph(escape(application.call.title), s["title"]))
    call = application.call
    meta = [
        f"Nabór: od {local(call.opens_at)} do {local(call.closes_at)}",
        f"Pomysł nr {application.idea.number}: {application.idea.title}"
        if application.idea
        else "Wniosek bez pomysłu w HubMi",
        f"Stan: {STATUS_NAMES.get(application.status, application.status)}",
    ]
    if application.submitted_at:
        meta.append(f"Złożono: {local(application.submitted_at)}")
    story.extend(Paragraph(escape(line), s["meta"]) for line in meta)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(escape(FORM_NOTE), s["hint"]))
    for section in application.sections:
        block: list[Any] = [Paragraph(escape(section.label), s["label"])]
        if section.text.strip():
            block.extend(paragraphs(section.text, s["base"]))
        else:
            block.append(Paragraph("Sekcja nie jest jeszcze wypełniona.", s["missing"]))
        if section.missing:
            block.append(Paragraph("Do uzupełnienia:", s["missing"]))
            block.append(
                ListFlowable(
                    [
                        ListItem(Paragraph(escape(item), s["missing"]))
                        for item in section.missing
                    ],
                    bulletType="bullet",
                    leftIndent=12,
                    bulletColor=ACCENT,
                )
            )
        story.append(KeepTogether(block[:2]))
        story.extend(block[2:])
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Wniosek nr {application.number}: {application.call.title}",
        author="HubMi",
        lang="pl-PL",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
