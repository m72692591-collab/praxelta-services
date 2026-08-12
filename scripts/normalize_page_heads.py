"""Add required static security and canonical tags to root HTML pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://m72692591-collab.github.io/praxelta-services/"
CSP = (
    "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; "
    "style-src 'self'; img-src 'self' data:; font-src 'self'; script-src 'none'; "
    "connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'none'; "
    "upgrade-insecure-requests; block-all-mixed-content\">"
)


def main() -> None:
    changed = 0
    for path in ROOT.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        original = text
        if "Content-Security-Policy" not in text:
            text = text.replace(
                '<meta name="viewport" content="width=device-width,initial-scale=1">',
                '<meta name="viewport" content="width=device-width,initial-scale=1">' + CSP,
                1,
            )
        if 'rel="canonical"' not in text:
            route = "" if path.name == "index.html" else path.name
            text = text.replace(
                '<link rel="stylesheet" href="styles.css">',
                f'<link rel="canonical" href="{BASE}{route}"><link rel="stylesheet" href="styles.css">',
                1,
            )
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    print(f"Normalized {changed} HTML heads")


if __name__ == "__main__":
    main()
