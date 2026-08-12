"""Generate and structurally verify PDFs from public HTML source pages."""

from __future__ import annotations

from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup, Tag
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
SOURCES = {
    "local-growth-commercial.html": "praxelta-local-growth-commercial.pdf",
    "local-growth-teaser.html": "praxelta-local-growth-teaser.pdf",
    "local-growth-checklist.html": "praxelta-7-points-checklist.pdf",
}


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (
            Path("C:/Windows/Fonts/calibri.ttf"),
            Path("C:/Windows/Fonts/calibrib.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("PraxeltaRegular", regular))
            pdfmetrics.registerFont(TTFont("PraxeltaBold", bold))
            return "PraxeltaRegular", "PraxeltaBold"
    raise RuntimeError("Cyrillic TrueType fonts were not found")


def page_footer(canvas: object, document: object) -> None:
    canvas.saveState()  # type: ignore[attr-defined]
    canvas.setFont("PraxeltaRegular", 8)  # type: ignore[attr-defined]
    canvas.setFillColor(colors.HexColor("#64707A"))  # type: ignore[attr-defined]
    canvas.drawString(18 * mm, 11 * mm, "ПРАКСЕЛЬТА · 2026")  # type: ignore[attr-defined]
    canvas.drawRightString(192 * mm, 11 * mm, f"{document.page}")  # type: ignore[attr-defined]
    canvas.restoreState()  # type: ignore[attr-defined]


def build_pdf(source: Path, target: Path) -> None:
    regular, bold = register_fonts()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=regular,
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#28333D"),
        spaceAfter=7,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=body,
        fontName=bold,
        fontSize=29,
        leading=31,
        textColor=colors.HexColor("#18212A"),
        spaceAfter=15,
        keepWithNext=True,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=body,
        fontName=bold,
        fontSize=18,
        leading=21,
        textColor=colors.HexColor("#18212A"),
        spaceBefore=12,
        spaceAfter=9,
        keepWithNext=True,
    )
    h3 = ParagraphStyle(
        "H3",
        parent=body,
        fontName=bold,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#A87524"),
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
    eyebrow = ParagraphStyle(
        "Eyebrow",
        parent=body,
        fontName=bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#A87524"),
        spaceAfter=7,
    )
    price = ParagraphStyle(
        "Price",
        parent=body,
        fontName=bold,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#F25322"),
        spaceAfter=8,
    )
    lead = ParagraphStyle(
        "Lead",
        parent=body,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#405064"),
        spaceAfter=12,
    )
    title = ParagraphStyle(
        "Brand",
        parent=body,
        fontName=bold,
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#A87524"),
        spaceAfter=14,
    )

    soup = BeautifulSoup(source.read_text(encoding="utf-8"), "html.parser")
    main = soup.find("main")
    if main is None:
        raise RuntimeError(f"{source.name}: main not found")
    story: list[object] = [Paragraph("ПРАКСЕЛЬТА", title)]
    for element in main.find_all(["h1", "h2", "h3", "p", "ul", "ol"], recursive=True):
        if not isinstance(element, Tag):
            continue
        if element.name in {"p", "ul", "ol"} and element.find_parent(["ul", "ol"]):
            continue
        text = " ".join(element.get_text(" ", strip=True).split())
        if not text:
            continue
        if element.name == "h1":
            story.extend([Paragraph(escape(text), h1), Spacer(1, 4 * mm)])
        elif element.name == "h2":
            story.append(Paragraph(escape(text), h2))
        elif element.name == "h3":
            story.append(Paragraph(escape(text), h3))
        elif element.name in {"ul", "ol"}:
            items = [
                ListItem(Paragraph(escape(" ".join(li.get_text(" ", strip=True).split())), body))
                for li in element.find_all("li", recursive=False)
            ]
            list_options = {
                "bulletType": "1" if element.name == "ol" else "bullet",
                "leftIndent": 18,
                "bulletFontName": regular,
                "bulletFontSize": 9,
                "spaceAfter": 7,
            }
            if element.name == "ol":
                list_options["start"] = "1"
            story.append(ListFlowable(items, **list_options))
        else:
            classes = set(element.get("class", []))
            style = eyebrow if "eyebrow" in classes else price if classes & {"price", "price-line"} else lead if "lead" in classes else body
            story.append(Paragraph(escape(text), style))

    document = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=soup.title.get_text(strip=True) if soup.title else source.stem,
        author="ПРАКСЕЛЬТА",
    )
    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for source_name, output_name in SOURCES.items():
        source = ROOT / source_name
        target = OUTPUT / output_name
        build_pdf(source, target)
        reader = PdfReader(target)
        if not reader.pages:
            raise RuntimeError(f"{target.name}: PDF has no pages")
        with pdfplumber.open(target) as document:
            text = "\n".join(page.extract_text() or "" for page in document.pages)
        required = ["ПРАКСЕЛЬТА", "7 900 ₽"]
        if output_name == "praxelta-local-growth-commercial.pdf":
            required.extend(["Авито", "Тарифы после разбора"])
        for value in required:
            if value not in text:
                raise RuntimeError(f"{target.name}: required text missing: {value}")
        print(f"PDF {target.name}: {len(reader.pages)} pages, {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
