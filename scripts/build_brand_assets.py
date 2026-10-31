"""Render the approved DXt geometry into theme logos and Windows icon formats.

Optional asset authoring dependencies: cairosvg and Pillow. Not needed at runtime
or for the Windows package build; generated assets are committed.
"""
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets/brand"


def main():
    source = (BRAND / "dxt.svg").read_text(encoding="utf-8")
    for theme, ink in (("light", "#111b28"), ("dark", "#f4f7fb")):
        svg = source.replace("#111b28", ink)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(BRAND / f"logo-{theme}.png"),
                        output_width=472, output_height=176)
    # A stable dark tile keeps the shell icon visible on either Windows theme.
    inner = source.split('<g fill=', 1)[1].split('</svg>', 1)[0]
    inner = '<g fill=' + inner.replace("#111b28", "#f4f7fb")
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
            '<rect x="4" y="4" width="248" height="248" rx="48" fill="#111b28"/>'
            '<g transform="translate(18 87) scale(.186)">' + inner + '</g></svg>')
    png = cairosvg.svg2png(bytestring=icon.encode(), output_width=256, output_height=256)
    (BRAND / "icon.png").write_bytes(png)
    with Image.open(BytesIO(png)) as image:
        image.save(BRAND / "dxt.ico", sizes=[(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)])


if __name__ == "__main__":
    main()
