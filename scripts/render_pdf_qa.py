"""Render generated PDFs to PNG for visual QA when Poppler is unavailable."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output" / "pdf"
TARGET = ROOT / "tmp" / "pdfs"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for pdf_path in sorted(SOURCE.glob("*.pdf")):
        document = pdfium.PdfDocument(pdf_path)
        for index, page in enumerate(document):
            bitmap = page.render(scale=1.8)
            target = TARGET / f"{pdf_path.stem}-{index + 1}.png"
            bitmap.to_pil().save(target)
            print(f"Rendered {target.name}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
