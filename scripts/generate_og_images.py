"""
Generate OG (Open Graph) social share images for Pollination Africa Summit 2026.
Produces 1200x630px PNG files using html2image (headless Chrome).

Output: app/static/images/og/{default,speakers,register}.png

Usage:
    python scripts/generate_og_images.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "app" / "static" / "images" / "logo_circle.png"
OUTPUT = ROOT / "app" / "static" / "images" / "og"

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1200px;
    height: 630px;
    background-color: #142601;
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .main {{
    flex: 1;
    display: flex;
    flex-direction: row;
    align-items: center;
    padding: 55px 80px;
    gap: 55px;
  }}
  .logo {{
    width: 168px;
    height: 168px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    border: 5px solid #f2c12e;
  }}
  .text-block {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .event-name {{
    font-size: 54px;
    font-weight: 800;
    line-height: 1.1;
    color: #ffffff;
    letter-spacing: -1px;
  }}
  .event-name span {{
    color: #f2c12e;
  }}
  .tagline {{
    font-size: 21px;
    font-weight: 400;
    color: #a5d6a7;
    line-height: 1.4;
    max-width: 700px;
  }}
  .meta-row {{
    display: flex;
    gap: 24px;
    align-items: center;
    font-size: 19px;
    color: #c8e6c9;
    font-weight: 500;
  }}
  .meta-row .sep {{ color: #f2c12e; }}
  .page-label {{
    display: inline-block;
    background: #f2c12e;
    color: #142601;
    font-size: 16px;
    font-weight: 800;
    padding: 8px 24px;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 4px;
  }}
  .bottom-strip {{
    height: 18px;
    background: #f2c12e;
    width: 100%;
    flex-shrink: 0;
  }}
</style>
</head>
<body>
  <div class="main">
    <img class="logo" src="{logo_url}" alt="Pollination Africa Summit Logo">
    <div class="text-block">
      <div class="event-name">Pollination <span>Africa</span> Summit 2026</div>
      <div class="tagline">Harnessing Pollination for Food Security,<br>Biodiversity &amp; Livelihoods</div>
      <div class="meta-row">
        <span>3&ndash;5 June 2026</span>
        <span class="sep">&middot;</span>
        <span>Arusha, Tanzania</span>
      </div>
      {page_label}
    </div>
  </div>
  <div class="bottom-strip"></div>
</body>
</html>"""

VARIANTS = {
    "default.png": "",
    "speakers.png": '<div class="page-label">Speakers</div>',
    "register.png": '<div class="page-label">Register Now</div>',
}


def main():
    if not LOGO.exists():
        print(f"ERROR: Logo not found at {LOGO}", file=sys.stderr)
        sys.exit(1)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    logo_url = LOGO.as_uri()  # file:///...

    try:
        from html2image import Html2Image
    except ImportError:
        print("ERROR: html2image not installed. Run: pip install html2image", file=sys.stderr)
        sys.exit(1)

    hti = Html2Image(output_path=str(OUTPUT), size=(1200, 630))

    for filename, page_label in VARIANTS.items():
        html = TEMPLATE.format(logo_url=logo_url, page_label=page_label)
        hti.screenshot(html_str=html, save_as=filename)
        print(f"  Generated: app/static/images/og/{filename}")

    print("\nDone. OG images saved to app/static/images/og/")


if __name__ == "__main__":
    main()
