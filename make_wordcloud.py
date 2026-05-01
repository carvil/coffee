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

# Senzu palette tiered by frequency
COLOR_HOT  = "#5A1A28"   # deep wine — words appearing 5+ times
COLOR_MID  = "#3A1F18"   # espresso brown — 2-4 times
COLOR_COOL = "#B5734F"   # terracotta — once

TITLE_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
BODY_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"


def build_corpus() -> Counter:
    coffees = json.loads((DATA / "coffees.json").read_text())
    counter: Counter = Counter()
    for coffee in coffees:
        for note in coffee.get("tasting_notes", []):
            normalized = " ".join(w.capitalize() for w in note.strip().split())
            counter[normalized] += 1
    return counter


def build_mask(width: int, height: int) -> np.ndarray:
    """Vertical coffee-bean silhouette mask.

    wordcloud convention: 255 (white) = no words; <255 (black) = words go here.
    """
    mask = Image.new("L", (width, height), 255)
    d = ImageDraw.Draw(mask)
    cx, cy = width // 2, height // 2

    # Reserve space for title (top) and footer (bottom)
    avail_top = PX(MARGIN_TOP_MM + 38)
    avail_bot = height - PX(MARGIN_BOTTOM_MM + 22)
    avail_h = avail_bot - avail_top
    avail_w = width - 2 * PX(MARGIN_SIDE_MM)

    # Bean: vertical ellipse — taller than wide for portrait fill
    bean_w = int(avail_w * 0.96)
    bean_h = int(avail_h * 0.96)
    bean_cy = (avail_top + avail_bot) // 2

    d.ellipse(
        [cx - bean_w // 2, bean_cy - bean_h // 2,
         cx + bean_w // 2, bean_cy + bean_h // 2],
        fill=0,
    )
    return np.array(mask)


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


def render_overlays(img: Image.Image) -> Image.Image:
    """Add title and footer to the rendered word cloud image."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, int(28 / 72 * DPI))
    sub_font = ImageFont.truetype(TITLE_FONT_PATH, int(10 / 72 * DPI))
    foot_font = ImageFont.truetype(TITLE_FONT_PATH, int(8 / 72 * DPI))

    title = "TASTING NOTES"
    subtitle = "37 COFFEES · 94 DISTINCT FLAVOURS · 173 TOTAL"

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
        prefer_horizontal=0.85,        # most words horizontal
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
    img = render_overlays(img)

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
