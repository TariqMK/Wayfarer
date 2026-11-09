"""Builds every Wayfarer brand image from the icon masters in assets/icon/.

Writes:
  assets/icon/wayfarer.png    1024 x 1024 px
  assets/icon/wayfarer.ico    16 to 256 px, PNG-encoded (Windows exe and window)
  assets/icon/wayfarer.icns   16 to 1024 px, including @2x sizes (macOS app)
  wayfarer/ui/icon.ico        copy for the app window on Windows
  wayfarer/ui/icon.png        256 px copy for the app window on Linux
  assets/banner.png           README banner, 1280 x 320 px at 2x
  assets/social-card.png      GitHub social preview, 1280 x 640 px
  docs/ copies                the site's icon, touch icon and social card, plus docs/app/: the app's poster code,
                              its colour and poster CSS, its fonts, and the sample trip with its text export

Sizes of 32 px and smaller use wayfarer-small.svg. Everything else uses wayfarer.svg.

Run from the project root (needs PySide6 and Pillow, which the app itself does not use):
  pip install PySide6 Pillow fonttools brotli
  python assets/make_assets.py
"""

import argparse
import io
import json
import shutil
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtSvg import QSvgRenderer

# ---- Values to change by hand -------------------------------------------------------------------
NAME = "Wayfarer"
TAGLINE = "Plan the trip. Print the route."
SUBLINE = "Windows · macOS · Linux"
# --------------------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "assets" / "icon"
MASTER = ICON_DIR / "wayfarer.svg"
SMALL = ICON_DIR / "wayfarer-small.svg"
FONTS = ROOT / "wayfarer" / "ui" / "vendor" / "fonts"

# Colours from the app's dark theme (wayfarer/ui/app.css).
DEEP = "#0f0f10"  # --deep
BORDER = "#232324"  # --line over --deep
T1 = "#ededed"  # --t1
T2 = "#a8a8ad"  # --t2
T3 = "#8c8c92"  # --t3

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]  # 32, 64, 256, 512 and 1024 also serve as @2x.


def render_svg(size: int) -> QImage:
    source = SMALL if size <= 32 else MASTER
    renderer = QSvgRenderer(QByteArray(source.read_bytes()))
    if not renderer.isValid():
        sys.exit(f"Cannot read {source}")
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def to_pil(image: QImage) -> Image.Image:
    buffer = QByteArray()
    device = QBuffer(buffer)
    device.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(device, "PNG")
    device.close()
    return Image.open(io.BytesIO(bytes(buffer))).convert("RGBA")


def make_icons() -> None:
    big = to_pil(render_svg(1024))
    big.save(ICON_DIR / "wayfarer.png")
    ico = [to_pil(render_svg(s)) for s in ICO_SIZES]
    ico[-1].save(ICON_DIR / "wayfarer.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=ico[:-1])
    icns = [to_pil(render_svg(s)) for s in ICNS_SIZES]
    icns[-1].save(ICON_DIR / "wayfarer.icns", format="ICNS", append_images=icns[:-1])
    ui = ROOT / "wayfarer" / "ui"
    shutil.copyfile(ICON_DIR / "wayfarer.ico", ui / "icon.ico")
    ico[-1].save(ui / "icon.png")


def load_font(file: str, fallback: list[str], px: float, weight: QFont.Weight) -> QFont:
    """Loads one of the app's bundled fonts. Qt can't read WOFF2, so fontTools unpacks it in memory first."""
    family = None
    font = TTFont(FONTS / file)
    font.flavor = None
    data = io.BytesIO()
    font.save(data)
    font_id = QFontDatabase.addApplicationFontFromData(QByteArray(data.getvalue()))
    if font_id >= 0:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
    else:
        print(f"Warning: could not load {file}. Using a system font.")
    result = QFont()
    result.setFamilies([family] if family else fallback)
    result.setPixelSize(round(px))
    result.setWeight(weight)
    return result


def sans(px: float) -> QFont:
    return load_font("ibm-plex-sans-latin-600-normal.woff2", ["Segoe UI", "Helvetica Neue"], px, QFont.Weight.DemiBold)


def mono(px: float) -> QFont:
    return load_font("ibm-plex-mono-latin-400-normal.woff2", ["Consolas", "Menlo"], px, QFont.Weight.Normal)


def draw_icon(painter: QPainter, rect: QRectF) -> None:
    QSvgRenderer(QByteArray(MASTER.read_bytes())).render(painter, rect)


def make_banner(scale: int = 2) -> None:
    """1280 x 320 rounded panel: icon left, name and tagline right, centred as one group."""
    w, h = 1280 * scale, 320 * scale
    image = QImage(w, h, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    panel = QPainterPath()
    half = scale / 2
    panel.addRoundedRect(QRectF(half, half, w - scale, h - scale), 24 * scale, 24 * scale)
    p.fillPath(panel, QColor(DEEP))
    p.setPen(QPen(QColor(BORDER), scale))
    p.drawPath(panel)

    icon, gap = 176 * scale, 48 * scale
    name_font, tag_font = sans(96 * scale), mono(24 * scale)
    name_m, tag_m = QFontMetrics(name_font), QFontMetrics(tag_font)
    text_w = max(name_m.horizontalAdvance(NAME), tag_m.horizontalAdvance(TAGLINE))
    left = (w - (icon + gap + text_w)) / 2
    draw_icon(p, QRectF(left, (h - icon) / 2, icon, icon))
    # Text block: name cap height, a gap, then the tagline, centred on the icon.
    line_gap = 28 * scale
    block = name_m.capHeight() + line_gap + tag_m.ascent()
    top = (h - block) / 2
    x = left + icon + gap
    p.setFont(name_font)
    p.setPen(QColor(T1))
    p.drawText(QPointF(x - name_font.pixelSize() * 0.04, top + name_m.capHeight()), NAME)
    p.setFont(tag_font)
    p.setPen(QColor(T2))
    p.drawText(QPointF(x, top + block), TAGLINE)
    p.end()
    image.save(str(ROOT / "assets" / "banner.png"))


# Social card: the fixed repo-card layout (GitHub's template). Keep these values in step with every project.
CARD_W, CARD_H, SAFE = 1280, 640, 80
CARD_ICON, CARD_ICON_TOP, CARD_ICON_GAP = 168, 150, 40
CARD_NAME_PX, CARD_TAGLINE_PX, CARD_TAGLINE_Y, CARD_SUB_PX, CARD_SUB_Y = 112, 34, 420, 24, 476


def make_social_card(guides: Path | None = None) -> bool:
    image = QImage(CARD_W, CARD_H, QImage.Format.Format_ARGB32)
    image.fill(QColor(DEEP))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    name_font = sans(CARD_NAME_PX)
    name_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
    name_w = QFontMetrics(name_font).horizontalAdvance(NAME)
    left = (CARD_W - (CARD_ICON + CARD_ICON_GAP + name_w)) / 2
    draw_icon(p, QRectF(left, CARD_ICON_TOP, CARD_ICON, CARD_ICON))
    cap = QFontMetrics(name_font).capHeight()
    p.setFont(name_font)
    p.setPen(QColor(T1))
    p.drawText(QPointF(left + CARD_ICON + CARD_ICON_GAP - CARD_NAME_PX * 0.035, CARD_ICON_TOP + CARD_ICON / 2 + cap / 2), NAME)
    for text, font, color, y in ((TAGLINE, mono(CARD_TAGLINE_PX), T2, CARD_TAGLINE_Y), (SUBLINE, mono(CARD_SUB_PX), T3, CARD_SUB_Y)):
        if text:
            p.setFont(font)
            p.setPen(QColor(color))
            p.drawText(QPointF((CARD_W - QFontMetrics(font).horizontalAdvance(text)) / 2, y), text)
    p.end()
    image.save(str(ROOT / "assets" / "social-card.png"))

    bg = QColor(DEEP)
    xs, ys = [], []
    for y in range(CARD_H):
        for x in range(CARD_W):
            if image.pixelColor(x, y) != bg:
                xs.append(x)
                ys.append(y)
    inside = min(xs) >= SAFE and min(ys) >= SAFE and max(xs) <= CARD_W - SAFE and max(ys) <= CARD_H - SAFE
    print(f"Social card content: x {min(xs)}-{max(xs)}, y {min(ys)}-{max(ys)}. Safe area check {'passed' if inside else 'FAILED'}.")
    if guides:
        p = QPainter(image)
        p.setPen(QPen(QColor("#d1242f"), 2))
        p.drawRect(SAFE, SAFE, CARD_W - 2 * SAFE, CARD_H - 2 * SAFE)
        p.end()
        image.save(str(guides))
    return inside


def css_section(css: str, start: str, end: str) -> str:
    """Return app.css from the comment `/* start */` up to the comment `/* end */`."""
    a, b = css.index(f"/* {start} */"), css.index(f"/* {end} */")
    return css[a:b]


def make_site_copies() -> None:
    """Copy what the GitHub Pages site needs into docs/, so the site draws posters with the app's own code."""
    docs, ui = ROOT / "docs", ROOT / "wayfarer" / "ui"
    app_dir = docs / "app"
    (app_dir / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MASTER, docs / "icon.svg")
    shutil.copyfile(ROOT / "assets" / "social-card.png", docs / "social-card.png")
    to_pil(render_svg(180)).save(docs / "apple-touch-icon.png")
    (docs / ".nojekyll").touch()
    for name in ("routes.js", "posters.js"):
        shutil.copyfile(ui / name, app_dir / name)

    # The app's colour tokens, header controls, editor and posters. The site scopes them with data-theme.
    css = (ui / "app.css").read_text(encoding="utf-8")
    tokens = "".join(line + "\n" for line in css.splitlines() if line.startswith(("[data-theme=", "  --")))
    root = css.splitlines()[2] + "\n"  # :root{--ease;--mono;--sans;--display}
    parts = [css_section(css, "Header", "Trips (home)"), css_section(css, "Editor", "Dialogs")]
    (app_dir / "app.css").write_text(
        "/* Copied from wayfarer/ui/app.css by assets/make_assets.py. Do not edit here. */\n" + root + tokens + "".join(parts),
        encoding="utf-8",
    )

    # Latin subsets only: the site shows English sample text.
    fonts_css = (ui / "vendor" / "fonts.css").read_text(encoding="utf-8").splitlines()
    keep = [line for line in fonts_css if line.startswith("@font-face") and "-latin-ext-" not in line]
    for line in keep:
        name = line.split("url(fonts/")[1].split(")")[0]
        shutil.copyfile(ui / "vendor" / "fonts" / name, app_dir / "fonts" / name)
    (app_dir / "fonts.css").write_text(
        "/* Fonts copied from the app (Fontsource, SIL Open Font License). Written by assets/make_assets.py. */\n"
        + "\n".join(keep)
        + "\n",
        encoding="utf-8",
    )

    # The sample trip from the screenshot script, and its text export from the app's own exporter.
    sys.path[:0] = [str(ROOT), str(ROOT / "assets")]
    from make_screenshots import MAIN_TRIP

    from wayfarer.export import build_text

    (app_dir / "sample.js").write_text(
        "// The made-up sample trip from assets/make_screenshots.py, and its text export. Written by assets/make_assets.py.\n"
        f"const SAMPLE_TRIP = {json.dumps(MAIN_TRIP, ensure_ascii=False)};\n"
        f"const SAMPLE_TEXT = {json.dumps(build_text(MAIN_TRIP), ensure_ascii=False)};\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Wayfarer brand images. With no parts, builds all.")
    parser.add_argument("parts", nargs="*", choices=["icon", "banner", "card", "site"], help="Build only these parts.")
    parser.add_argument("--guides", type=Path, help="Also write a social card copy with the safe area drawn on.")
    args = parser.parse_args()
    only, guides = set(args.parts), args.guides
    app = QGuiApplication(sys.argv[:1])  # noqa: F841 - Qt needs an application object for fonts.
    if not only or "icon" in only:
        make_icons()
        print("Wrote icons")
    if not only or "banner" in only:
        make_banner()
        print("Wrote assets/banner.png")
    if not only or "card" in only:
        if not make_social_card(guides):
            return 1
        print("Wrote assets/social-card.png")
    if not only or "site" in only:
        make_site_copies()
        print("Wrote copies in docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
