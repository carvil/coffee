"""Generate a micrography poster: a coffee silhouette filled with text from
the coffee dataset.

From across the room: a strong silhouette. Up close: every line is your
coffee history — countries, farms, tasting notes, blurbs.

Outputs:
  output/micrography_v1.png   (preview at chosen DPI)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

# ---- Page setup: A3 portrait ----
PAGE_W_MM, PAGE_H_MM = 297, 420
DPI = 260
MM_PER_INCH = 25.4
PX = lambda mm: int(round(mm / MM_PER_INCH * DPI))
PAGE_W_PX, PAGE_H_PX = PX(PAGE_W_MM), PX(PAGE_H_MM)

MARGIN_TOP_MM = 32
MARGIN_BOTTOM_MM = 26
MARGIN_SIDE_MM = 28

# Body text
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"
FONT_SIZE_PT = 6.4
LINE_HEIGHT_FACTOR = 1.04

# Title typography
TITLE_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
TITLE_TEXT = "37 COFFEES"
SUBTITLE_TEXT = "SENZU COFFEE ROASTERS · ROASTED IN PORTO"

# Colors — inverted from v1: deep Senzu burgundy silhouette, cream text inside.
# The deep wine echoes the Palermo / El Panal cards, darkened for espresso vibe.
PAPER = (250, 248, 243)
SILHOUETTE_FILL = (90, 26, 40)   # #5A1A28 deep wine — the saturated block
INK_INSIDE = (250, 248, 243)     # cream/paper text inside the silhouette
INK_OUTSIDE = (40, 22, 18)       # near-black for title/footer outside


def pt_to_px(pt: float) -> int:
    return int(round(pt / 72 * DPI))


def build_corpus(coffees: list[dict]) -> str:
    """Concatenate each coffee into a block of text. Order: country, farm,
    tasting notes, then the blurb. Coffees are sorted by country then farm.
    """
    rows = sorted(coffees, key=lambda c: (c["country"], c.get("farm") or ""))
    blocks = []
    for c in rows:
        country = c["country"].upper()
        farm = (c.get("farm") or "").upper()
        region = (c.get("region") or "")
        notes = " · ".join(c.get("tasting_notes") or [])
        blurb = (c.get("blurb") or "").strip()
        head = f"{country} — {farm}"
        if region:
            head += f", {region}"
        block = f"{head}.  Notes: {notes}.  {blurb}  "
        # Clean any double spaces/newlines
        block = " ".join(block.split())
        blocks.append(block)
    # Join blocks with a section separator that reads up close
    return "   ◆   ".join(blocks)


# ---- Silhouette: V60 dripper + carafe ----

def build_silhouette(width: int, height: int) -> Image.Image:
    """Espresso cup, side view, with saucer, handle, and steam wisps.

    255 = silhouette (gets filled in the saturated color), 0 = paper.
    """
    import math
    mask = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(mask)
    cx = width // 2

    # Layout
    top_y = PX(MARGIN_TOP_MM + 18)
    bottom_y = height - PX(MARGIN_BOTTOM_MM + 14)

    # Sizes (mm)
    cup_top_w = 130
    cup_bot_w = 95
    cup_h = 130
    saucer_w = 215
    saucer_h = 18
    handle_outer_d = 64
    handle_inner_d = 36
    handle_offset_mm = 8           # how far handle center sits past cup edge

    steam_count = 3
    steam_amplitude_mm = 12
    steam_height_mm = 110
    steam_thickness_mm = 12
    steam_top_gap_mm = 30          # gap between cup rim and start of steam

    # Position cup+saucer centered vertically, leaving room above for steam
    composition_h = PX(steam_height_mm + steam_top_gap_mm + cup_h + saucer_h)
    available_h = bottom_y - top_y
    block_top = top_y + (available_h - composition_h) // 2

    steam_y0 = block_top
    steam_y1 = steam_y0 + PX(steam_height_mm)
    cup_y0 = steam_y1 + PX(steam_top_gap_mm)
    cup_y1 = cup_y0 + PX(cup_h)
    saucer_y0 = cup_y1
    saucer_y1 = saucer_y0 + PX(saucer_h)

    # ---- Steam wisps (drawn first; cup overlaps the bottom) ----
    # 3 wavy plumes that sway side-to-side, getting thinner and sparser at top
    for i in range(steam_count):
        # Each wisp slightly different x, phase, height
        x_offset = (i - (steam_count - 1) / 2) * PX(22)
        phase = i * 1.7
        # Build polygon of wisp by following sinusoidal centerline
        n_pts = 80
        pts_left = []
        pts_right = []
        for j in range(n_pts):
            t = j / (n_pts - 1)
            y = steam_y1 - t * PX(steam_height_mm)
            # Amplitude grows toward top (more dramatic at the tip)
            amp = PX(steam_amplitude_mm) * (0.4 + 0.9 * t)
            sway = amp * math.sin(t * math.pi * 1.6 + phase)
            # Thickness tapers toward top (thinner higher up)
            thickness = PX(steam_thickness_mm) * (1.0 - 0.85 * t)
            cx_w = cx + x_offset + sway
            pts_left.append((cx_w - thickness / 2, y))
            pts_right.append((cx_w + thickness / 2, y))
        wisp = pts_left + list(reversed(pts_right))
        d.polygon(wisp, fill=255)

    # ---- Cup body ----
    # Trapezoid (slightly wider at top), with a small rounded bottom.
    cup_pts = [
        (cx - PX(cup_top_w) // 2, cup_y0),
        (cx + PX(cup_top_w) // 2, cup_y0),
        (cx + PX(cup_bot_w) // 2, cup_y1),
        (cx - PX(cup_bot_w) // 2, cup_y1),
    ]

    # ---- Handle on right side (drawn before cup so cup hides the inner edge) ----
    handle_cx = cx + PX(cup_top_w) // 2 + PX(handle_offset_mm) - PX(2)
    handle_cy = cup_y0 + PX(cup_h * 0.55)
    d.ellipse([
        handle_cx - PX(handle_outer_d) // 2, handle_cy - PX(handle_outer_d) // 2,
        handle_cx + PX(handle_outer_d) // 2, handle_cy + PX(handle_outer_d) // 2,
    ], fill=255)
    d.ellipse([
        handle_cx - PX(handle_inner_d) // 2, handle_cy - PX(handle_inner_d) // 2,
        handle_cx + PX(handle_inner_d) // 2, handle_cy + PX(handle_inner_d) // 2,
    ], fill=0)

    # Cup on top covers the left portion of the handle's inner cutout
    d.polygon(cup_pts, fill=255)

    # Small cap at the very top of the cup (rim line) — adds an espresso-cup "lip"
    rim_h = PX(7)
    d.rounded_rectangle([
        cx - PX(cup_top_w + 8) // 2, cup_y0 - rim_h // 2,
        cx + PX(cup_top_w + 8) // 2, cup_y0 + rim_h // 2,
    ], radius=PX(3), fill=255)

    # ---- Saucer — wide ellipse-like band ----
    d.rounded_rectangle([
        cx - PX(saucer_w) // 2, saucer_y0,
        cx + PX(saucer_w) // 2, saucer_y1,
    ], radius=PX(saucer_h // 2), fill=255)

    return mask


# ---- Typesetter ----

def typeset(mask: Image.Image, corpus: str, font: ImageFont.FreeTypeFont,
            line_height: int) -> Image.Image:
    """Walk the mask row-by-row at line_height intervals; for each row find
    the contiguous dark horizontal segments; fill each with characters from
    the corpus. Returns a final RGB image rendered on PAPER.

    Inverted color scheme: silhouette is filled with SILHOUETTE_FILL, text
    inside is rendered in INK_INSIDE (cream) for a card-like high-contrast look.
    """
    width, height = mask.size
    out = Image.new("RGB", (width, height), PAPER)
    # Solid fill of the silhouette with the saturated color
    fill_layer = Image.new("RGB", (width, height), SILHOUETTE_FILL)
    out.paste(fill_layer, mask=mask)
    draw = ImageDraw.Draw(out)

    mask_px = mask.load()

    # Approximate glyph width for SF Mono at this size
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]  # width of one mono char
    # Vertical position of text baseline within a line cell
    # Pillow draws text from top-left; estimate baseline at roughly 0.8 * line height
    text_baseline_offset = int(line_height * 0.08)

    corpus_pos = 0
    corpus_len = len(corpus)

    # Center-of-line y coordinates we'll sample for "is this row inside the shape"
    y = 0
    while y + line_height <= height:
        # Sample at the visual middle of the line
        sample_y = y + line_height // 2

        # Find dark segments along this row
        in_segment = False
        segments = []
        seg_start = 0
        for x in range(width):
            on = mask_px[x, sample_y] > 127
            if on and not in_segment:
                seg_start = x
                in_segment = True
            elif not on and in_segment:
                segments.append((seg_start, x))
                in_segment = False
        if in_segment:
            segments.append((seg_start, width))

        # Fill each segment with characters
        for x0, x1 in segments:
            seg_w = x1 - x0
            n_chars = max(1, seg_w // char_w)
            text = corpus[corpus_pos: corpus_pos + n_chars]
            # If we run out of corpus, wrap around (rare for now)
            if len(text) < n_chars:
                wrap = corpus[: n_chars - len(text)]
                text += wrap
                corpus_pos = len(wrap)
            else:
                corpus_pos = (corpus_pos + n_chars) % corpus_len
            # Draw text inside segment in cream — reads as engraved/embossed
            draw.text((x0, y + text_baseline_offset), text,
                      font=font, fill=INK_INSIDE)

        y += line_height

    return out


def draw_overlays(img: Image.Image) -> Image.Image:
    """Draw title above and footer below the silhouette."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(28))
    sub_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(9))

    # Title in the deep silhouette color, near the top
    title_y = PX(MARGIN_TOP_MM // 2)
    tw = draw.textlength(TITLE_TEXT, font=title_font)
    draw.text(((width - tw) / 2, title_y), TITLE_TEXT,
              fill=SILHOUETTE_FILL, font=title_font)

    sub_y = title_y + pt_to_px(32)
    sw = draw.textlength(SUBTITLE_TEXT, font=sub_font)
    draw.text(((width - sw) / 2, sub_y), SUBTITLE_TEXT,
              fill=INK_OUTSIDE, font=sub_font)

    # Footer
    footer_text = "37 SINGLE-ORIGIN COFFEES   ·   ROASTED IN PORTO"
    foot_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(8))
    fw = draw.textlength(footer_text, font=foot_font)
    foot_y = height - PX(MARGIN_BOTTOM_MM // 2) - pt_to_px(10)
    draw.text(((width - fw) / 2, foot_y), footer_text,
              fill=INK_OUTSIDE, font=foot_font)

    return img


def main() -> int:
    coffees = json.loads((DATA / "coffees.json").read_text())
    corpus = build_corpus(coffees)
    print(f"Corpus: {len(corpus):,} characters from {len(coffees)} coffees.")

    mask = build_silhouette(PAGE_W_PX, PAGE_H_PX)

    font = ImageFont.truetype(FONT_PATH, pt_to_px(FONT_SIZE_PT))
    line_height = int(pt_to_px(FONT_SIZE_PT) * LINE_HEIGHT_FACTOR)

    typeset_img = typeset(mask, corpus, font, line_height)
    final = draw_overlays(typeset_img)

    out_png = OUTPUT / "micrography_v1.png"
    final.save(out_png, dpi=(DPI, DPI))
    print(f"  → {out_png}  ({final.size[0]}×{final.size[1]} px @ {DPI} dpi)")
    print(f"  print size: {PAGE_W_MM}×{PAGE_H_MM} mm (A3 portrait)")

    # Inspection helpers
    silhouette_preview = mask.convert("RGB")
    silhouette_preview.thumbnail((1200, 1700), Image.Resampling.LANCZOS)
    silhouette_preview.save(OUTPUT / "micrography_v1_silhouette.png")
    print(f"  → output/micrography_v1_silhouette.png  (silhouette only)")

    small = final.copy()
    small.thumbnail((1400, 2000), Image.Resampling.LANCZOS)
    small.save(OUTPUT / "micrography_v1_preview.png")
    print(f"  → output/micrography_v1_preview.png  (scaled preview)")

    # Detail crop — middle 1/3 of the carafe at full resolution, to show
    # what the text actually looks like up close.
    cw, ch = final.size
    cx, cy = cw // 2, int(ch * 0.62)
    crop_w, crop_h = cw // 2, ch // 5
    detail = final.crop((cx - crop_w // 2, cy - crop_h // 2,
                         cx + crop_w // 2, cy + crop_h // 2))
    detail.save(OUTPUT / "micrography_v1_detail.png")
    print(f"  → output/micrography_v1_detail.png  (detail crop, carafe middle)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
