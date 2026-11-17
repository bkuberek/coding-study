"""Render tools/brand/readme-header.html to docs/images/readme-header.png.

Run from the repository root:

    uv run --group browser python tools/brand/render_readme_header.py

The card is 1200x300 pixels with transparent rounded corners.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "tools" / "brand" / "readme-header.html"
OUTPUT = ROOT / "docs" / "images" / "readme-header.png"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 300}, device_scale_factor=1)
        page.goto(TEMPLATE.as_uri())
        page.locator(".card").screenshot(path=str(OUTPUT), omit_background=True)
        browser.close()


if __name__ == "__main__":
    main()
