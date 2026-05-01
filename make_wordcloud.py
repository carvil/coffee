"""Generate a word cloud poster: every tasting note from your 37 coffees,
sized by frequency, packed into a coffee-bean silhouette.

A3 portrait. From across the room: the bean shape. Up close: every flavor
you've ever picked out, scaled by how often it appeared.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from wordcloud import WordCloud

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

# Page setup
PAGE_W_MM, PAGE_H_MM = 297, 420
DPI = 220
MM_PER_INCH = 25.4
PX = lambda mm: int(round(mm / MM_PER_INCH * DPI))
PAGE_W_PX, PAGE_H_PX = PX(PAGE_W_MM), PX(PAGE_H_MM)

MARGIN_TOP_MM = 32
MARGIN_BOTTOM_MM = 30
MARGIN_SIDE_MM = 26

PAPER = (250, 248, 243)
INK_DARK = (40, 22, 18)

# Senzu palette tiered by frequency — high-contrast: black → wine → terracotta
COLOR_HOT  = "#000000"   # pure black — words appearing 5+ times
COLOR_MID  = "#5A1A28"   # deep wine — 2-4 times
COLOR_COOL = "#9C5A3A"   # darker terracotta — once (more contrast on cream paper)

TITLE_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
BODY_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"


# Synonym merges — clean up near-duplicates that come from inconsistent
# tasting-language across cards. Meaningful distinctions (Milk vs Dark
# Chocolate, Plum vs Red Plum, Caramel variants) are preserved.
MERGE_TO = {
    "Raisins": "Raisin",
    "Wine": "Winey",
    "Winey Acidity": "Winey",
    "Cacao": "Cocoa",
    "Cream Milky Chocolate": "Milk Chocolate",
    "Creamy Dark Chocolate": "Dark Chocolate",
}


def build_corpus() -> Counter:
    coffees = json.loads((DATA / "coffees.json").read_text())
    counter: Counter = Counter()
    for coffee in coffees:
        for note in coffee.get("tasting_notes", []):
            normalized = " ".join(w.capitalize() for w in note.strip().split())
            normalized = MERGE_TO.get(normalized, normalized)
            counter[normalized] += 1
    return counter


def bean_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    """Return (cx, bean_cy, bean_w, bean_h) for the vertical coffee-bean."""
    avail_top = PX(MARGIN_TOP_MM + 38)
    avail_bot = height - PX(MARGIN_BOTTOM_MM + 22)
    avail_h = avail_bot - avail_top
    avail_w = width - 2 * PX(MARGIN_SIDE_MM)
    target_ratio = 1.5
    if avail_h / avail_w > target_ratio:
        bean_w, bean_h = avail_w, int(avail_w * target_ratio)
    else:
        bean_h, bean_w = avail_h, int(avail_h / target_ratio)
    return width // 2, (avail_top + avail_bot) // 2, bean_w, bean_h


def build_mask(width: int, height: int) -> np.ndarray:
    """Coffee-bean silhouette mask, drawn parametrically.

    The shape is a tapered oval (pinched slightly at the tips like a real
    bean), with subtle low-frequency perturbations so the outline reads as
    organic rather than a perfect ellipse. A thin S-curve channel runs down
    the middle of the mask — words pack into the two lobes, and the empty
    space between them IS the seam (no drawn line on top).

    wordcloud convention: 255 (white) = no words; 0 (black) = words go here.
    """
    import math
    mask = Image.new("L", (width, height), 255)
    d = ImageDraw.Draw(mask)
    cx, bean_cy, bean_w, bean_h = bean_geometry(width, height)

    # Parametric bean outline: ellipse with tapered tips + gentle organic wave
    a = bean_w / 2
    b = bean_h / 2
    n_outline = 360
    outline = []
    for i in range(n_outline):
        t = i / n_outline * 2 * math.pi   # ccw around perimeter
        cos_t = math.cos(t)
        sin_t = math.sin(t)
        # Taper at top/bottom (where |cos_t| → 1)
        taper = 1 - 0.20 * abs(cos_t) ** 3.5
        # Subtle low-frequency perturbation — gives an organic edge
        wave = 0.022 * math.sin(t * 3 + 0.7) + 0.014 * math.sin(t * 5 - 0.3)
        # Slight asymmetry: left lobe a touch fuller than right
        asymm = 1.04 if sin_t < 0 else 0.97
        x = a * sin_t * taper * asymm * (1 + wave)
        y = b * cos_t * (1 + wave * 0.4)
        outline.append((cx + x, bean_cy + y))
    d.polygon(outline, fill=0)

    # Carve a thin S-curve channel down the middle (the seam, as empty space).
    bean_top = bean_cy - int(b)
    bean_bot = bean_cy + int(b)
    n_pts = 220
    sway = bean_w * 0.045
    channel_thickness = max(3, int(bean_w * 0.018))   # thin
    channel_pts = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        eased = math.sin(t * math.pi)                  # 0 at tips, 1 at middle
        x_offset = int(math.sin(t * math.pi * 1.1) * sway * eased)
        y = bean_top + int(t * (bean_bot - bean_top))
        channel_pts.append((cx + x_offset, y))
    d.line(channel_pts, fill=255, width=channel_thickness)

    return np.array(mask)


SEAM_COLOR = (90, 56, 44)         # warm muted brown — softer than pure black
OUTLINE_COLOR = (90, 56, 44)


def draw_bean_crease(img: Image.Image) -> Image.Image:
    """Overlay a subtle curved seam down the bean's middle — drawn ON TOP of
    the rendered cloud so it reads as the bean's natural fold.
    """
    import math
    width, height = img.size
    cx, bean_cy, bean_w, bean_h = bean_geometry(width, height)
    bean_top = bean_cy - bean_h // 2
    bean_bot = bean_cy + bean_h // 2

    draw = ImageDraw.Draw(img)
    n_pts = 240
    sway = bean_w * 0.05
    thickness = max(2, int(bean_w * 0.006))   # was 0.020 — much thinner
    pts = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        eased = math.sin(t * math.pi)
        x_offset = int(math.sin(t * math.pi * 1.1) * sway * eased)
        y = bean_top + int(t * bean_h)
        pts.append((cx + x_offset, y))
    draw.line(pts, fill=SEAM_COLOR, width=thickness, joint="curve")
    return img


def draw_bean_outline(img: Image.Image) -> Image.Image:
    """Trace a thin border around the bean to define the silhouette edge."""
    width, height = img.size
    cx, bean_cy, bean_w, bean_h = bean_geometry(width, height)
    draw = ImageDraw.Draw(img)
    thickness = max(2, int(bean_w * 0.008))
    draw.ellipse(
        [cx - bean_w // 2, bean_cy - bean_h // 2,
         cx + bean_w // 2, bean_cy + bean_h // 2],
        outline=OUTLINE_COLOR,
        width=thickness,
    )
    return img


def make_color_func(counter: Counter):
    """Pick a Senzu color based on the word's frequency tier."""
    def color_func(word, font_size, position, orientation, random_state, **kwargs):
        freq = counter.get(word, 1)
        if freq >= 5:
            return COLOR_HOT
        elif freq >= 2:
            return COLOR_MID
        else:
            return COLOR_COOL
    return color_func


def render_overlays(img: Image.Image, counter: Counter) -> Image.Image:
    """Add title and footer to the rendered word cloud image."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, int(28 / 72 * DPI))
    sub_font = ImageFont.truetype(TITLE_FONT_PATH, int(10 / 72 * DPI))
    foot_font = ImageFont.truetype(TITLE_FONT_PATH, int(8 / 72 * DPI))

    title = "TASTING NOTES"
    n_unique = len(counter)
    n_total = sum(counter.values())
    subtitle = f"37 COFFEES · {n_unique} DISTINCT FLAVOURS · {n_total} TOTAL"

    title_y = PX(MARGIN_TOP_MM // 2)
    tw = draw.textlength(title, font=title_font)
    draw.text(((width - tw) / 2, title_y), title, fill=COLOR_HOT, font=title_font)

    sub_y = title_y + int(36 / 72 * DPI)
    sw = draw.textlength(subtitle, font=sub_font)
    draw.text(((width - sw) / 2, sub_y), subtitle, fill=INK_DARK, font=sub_font)

    footer = "SENZU COFFEE ROASTERS   ·   ROASTED IN PORTO"
    fw = draw.textlength(footer, font=foot_font)
    foot_y = height - PX(MARGIN_BOTTOM_MM // 2) - int(10 / 72 * DPI)
    draw.text(((width - fw) / 2, foot_y), footer, fill=INK_DARK, font=foot_font)

    return img


def main() -> int:
    counter = build_corpus()
    print(f"{len(counter)} unique notes, {sum(counter.values())} occurrences "
          f"from {len(json.loads((DATA / 'coffees.json').read_text()))} coffees.")
    print("\nTop 10:")
    for note, n in counter.most_common(10):
        print(f"  {n:>2}  {note}")

    mask = build_mask(PAGE_W_PX, PAGE_H_PX)

    wc = WordCloud(
        width=PAGE_W_PX,
        height=PAGE_H_PX,
        mask=mask,
        background_color="rgb(250,248,243)",
        color_func=make_color_func(counter),
        font_path=BODY_FONT_PATH,
        prefer_horizontal=0.80,        # mostly horizontal — only a few vertical accents
        max_words=200,
        relative_scaling=0.55,         # scale by frequency
        min_font_size=10,
        max_font_size=int(220 / 72 * DPI),  # ~220pt for the largest
        random_state=42,
        margin=4,                      # gap between words
        collocations=False,            # don't merge multi-word phrases
    )
    wc.generate_from_frequencies(counter)

    img = wc.to_image()
    img = render_overlays(img, counter)

    out = OUTPUT / "wordcloud_v1.png"
    img.save(out, dpi=(DPI, DPI))
    print(f"\n→ {out}  ({img.size[0]}×{img.size[1]} px @ {DPI} dpi)")
    print(f"  print size: {PAGE_W_MM}×{PAGE_H_MM} mm (A3 portrait)")

    # Smaller scaled preview for quick inspection
    preview = img.copy()
    preview.thumbnail((1400, 2000), Image.Resampling.LANCZOS)
    preview.save(OUTPUT / "wordcloud_v1_preview.png")
    print(f"→ output/wordcloud_v1_preview.png  (scaled preview)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
