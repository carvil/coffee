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

# Two-tone "pulling a shot" palette: dark espresso body + golden crema.
# Both colors live in the warm Senzu palette (terracotta/coffee family).
PAPER = (250, 248, 243)
ESPRESSO = (38, 22, 18)          # #261612 deep coffee — almost black with warm undertone
CREMA = (194, 136, 64)           # #C28840 warm golden tan — the foam on top of espresso
INK_ON_DARK = (250, 245, 230)    # cream text on espresso
INK_ON_CREMA = (38, 22, 18)      # dark text on crema/pour
INK_OUTSIDE = (38, 22, 18)       # title/footer on paper


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

def build_silhouette(width: int, height: int) -> dict:
    """Pulling-a-shot composition: a stream of espresso pours from above
    into a small white cup; crema (golden foam) sits on the surface; the
    rest of the cup body is dark espresso with a handle on the right.

    Returns a dict of disjoint region masks. Each is L-mode where 255 means
    'this pixel belongs to the region'. Regions get different fill+text
    colors in the typesetter.

    Regions, top to bottom:
        pour      — thin vertical stream descending from top of page
        crema     — golden foam, top portion of cup interior
        cup_body  — dark espresso, lower portion of cup + handle
    """
    from PIL import ImageChops

    cx = width // 2

    # Sizes (mm) — cup bigger and more central; pour shorter and thicker
    cup_top_w = 200
    cup_bot_w = 150
    cup_h = 155
    cup_wall_mm = 6
    crema_h = 30
    pour_w = 17
    pour_h = 140
    handle_outer_d = 68
    handle_inner_d = 38
    rim_lip_h = 7

    # Vertical layout: title (top), some breathing room, pour, cup, footer
    top_y = PX(MARGIN_TOP_MM + 38)
    pour_y0 = top_y
    pour_y1 = pour_y0 + PX(pour_h)
    cup_y0 = pour_y1
    cup_y1 = cup_y0 + PX(cup_h)

    crema_y0 = cup_y0 + PX(rim_lip_h)
    crema_y1 = crema_y0 + PX(crema_h)

    # Horizontal cup edges at any y (for taper interpolation)
    def cup_edge_x(y_px: int, side: int) -> int:
        """side: -1 left, +1 right. Linear interpolation top→bottom."""
        t = (y_px - cup_y0) / max(1, (cup_y1 - cup_y0))
        w = PX(cup_top_w) + (PX(cup_bot_w) - PX(cup_top_w)) * t
        return int(cx + side * w / 2)

    # Inner edges (after cup wall)
    def cup_inner_x(y_px: int, side: int) -> int:
        return cup_edge_x(y_px, side) - side * PX(cup_wall_mm)

    # ---- POUR mask — thin vertical column above cup ----
    pour_mask = Image.new("L", (width, height), 0)
    pd = ImageDraw.Draw(pour_mask)
    pd.rounded_rectangle(
        [cx - PX(pour_w) // 2, pour_y0,
         cx + PX(pour_w) // 2, pour_y1],
        radius=PX(pour_w // 2), fill=255,
    )

    # ---- CUP outer silhouette — for ceramic shape (used to subtract regions) ----
    cup_outer = Image.new("L", (width, height), 0)
    co = ImageDraw.Draw(cup_outer)
    # Rim lip extends slightly wider than cup top
    co.rounded_rectangle([
        cx - PX(cup_top_w + 6) // 2, cup_y0 - PX(rim_lip_h) // 2,
        cx + PX(cup_top_w + 6) // 2, cup_y0 + PX(rim_lip_h) // 2,
    ], radius=PX(3), fill=255)
    # Trapezoid body
    co.polygon([
        (cup_edge_x(cup_y0, -1), cup_y0),
        (cup_edge_x(cup_y0, +1), cup_y0),
        (cup_edge_x(cup_y1, +1), cup_y1),
        (cup_edge_x(cup_y1, -1), cup_y1),
    ], fill=255)
    # Slight rounding on the bottom corners — overlay an ellipse near the base
    base_w = PX(cup_bot_w + 6)
    base_h = PX(20)
    co.ellipse([
        cx - base_w // 2, cup_y1 - base_h // 2,
        cx + base_w // 2, cup_y1 + base_h // 2,
    ], fill=255)

    # ---- CUP interior — what's INSIDE the ceramic (no wall) ----
    cup_interior = Image.new("L", (width, height), 0)
    ci = ImageDraw.Draw(cup_interior)
    ci.polygon([
        (cup_inner_x(crema_y0, -1), crema_y0),
        (cup_inner_x(crema_y0, +1), crema_y0),
        (cup_inner_x(cup_y1 - PX(8), +1), cup_y1 - PX(8)),
        (cup_inner_x(cup_y1 - PX(8), -1), cup_y1 - PX(8)),
    ], fill=255)

    # ---- CREMA region: top band of cup interior ----
    crema_mask = Image.new("L", (width, height), 0)
    cm = ImageDraw.Draw(crema_mask)
    cm.polygon([
        (cup_inner_x(crema_y0, -1), crema_y0),
        (cup_inner_x(crema_y0, +1), crema_y0),
        (cup_inner_x(crema_y1, +1), crema_y1),
        (cup_inner_x(crema_y1, -1), crema_y1),
    ], fill=255)

    # ---- ESPRESSO body region: rest of cup interior + handle ring ----
    espresso_interior = ImageChops.subtract(cup_interior, crema_mask)

    # Handle: filled annulus on right side
    handle_mask = Image.new("L", (width, height), 0)
    hm = ImageDraw.Draw(handle_mask)
    handle_cx = cup_edge_x(cup_y0 + PX(cup_h * 0.45), +1) + PX(handle_outer_d) // 2 - PX(8)
    handle_cy = cup_y0 + PX(cup_h * 0.55)
    hm.ellipse([
        handle_cx - PX(handle_outer_d) // 2, handle_cy - PX(handle_outer_d) // 2,
        handle_cx + PX(handle_outer_d) // 2, handle_cy + PX(handle_outer_d) // 2,
    ], fill=255)
    hm.ellipse([
        handle_cx - PX(handle_inner_d) // 2, handle_cy - PX(handle_inner_d) // 2,
        handle_cx + PX(handle_inner_d) // 2, handle_cy + PX(handle_inner_d) // 2,
    ], fill=0)
    # Subtract any portion of the handle that overlaps the cup outer (the
    # cup's body should hide the handle there)
    handle_visible = ImageChops.subtract(handle_mask, cup_outer)

    # Espresso region = interior body + visible handle
    espresso_body = ImageChops.add(espresso_interior, handle_visible)

    return {
        "pour": pour_mask,
        "crema": crema_mask,
        "cup_body": espresso_body,
        "cup_outer": cup_outer,  # used for outline only — no fill, no text
    }


# ---- Typesetter ----

def typeset(regions: dict, corpus: str, font: ImageFont.FreeTypeFont,
            line_height: int) -> Image.Image:
    """Multi-region typesetter. Each region in REGION_STYLES gets its own
    fill color and text color, with text flowing from a shared corpus cursor
    so the narrative reads top-to-bottom across regions.
    """
    width, height = regions["cup_body"].size
    out = Image.new("RGB", (width, height), PAPER)

    # Fill each region with its background color
    for name, fill in [
        ("cup_body", ESPRESSO),
        ("crema", CREMA),
        ("pour", ESPRESSO),       # the pour stream is the dark coffee itself
    ]:
        layer = Image.new("RGB", (width, height), fill)
        out.paste(layer, mask=regions[name])

    # Cup outer rim/wall — we let the paper show through for the white ceramic.
    # But we still want a thin dark stroke around the cup so it reads as a
    # discrete object on cream paper. Skip if we want a fully invisible cup.

    draw = ImageDraw.Draw(out)
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]
    text_baseline_offset = int(line_height * 0.08)

    cursor = 0

    def fill_region(mask_img, text_color):
        nonlocal cursor
        mask_px = mask_img.load()
        y = 0
        while y + line_height <= height:
            sample_y = y + line_height // 2
            in_seg = False
            segments = []
            seg_start = 0
            for x in range(width):
                on = mask_px[x, sample_y] > 127
                if on and not in_seg:
                    seg_start = x
                    in_seg = True
                elif not on and in_seg:
                    segments.append((seg_start, x))
                    in_seg = False
            if in_seg:
                segments.append((seg_start, width))

            for x0, x1 in segments:
                seg_w = x1 - x0
                n_chars = max(1, seg_w // char_w)
                # Fetch n_chars from corpus, wrapping if we run out
                pieces = []
                remaining = n_chars
                while remaining > 0:
                    avail = len(corpus) - cursor
                    take = min(avail, remaining)
                    pieces.append(corpus[cursor:cursor + take])
                    cursor = (cursor + take) % len(corpus)
                    remaining -= take
                text = "".join(pieces)
                draw.text((x0, y + text_baseline_offset), text,
                          font=font, fill=text_color)
            y += line_height

    # Order: pour (top) → crema → cup_body. Reads top-to-bottom.
    fill_region(regions["pour"], INK_ON_DARK)
    fill_region(regions["crema"], INK_ON_CREMA)
    fill_region(regions["cup_body"], INK_ON_DARK)

    return out


def draw_overlays(img: Image.Image) -> Image.Image:
    """Title at top, footer at bottom on cream paper."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(28))
    sub_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(9))

    title_y = PX(MARGIN_TOP_MM // 2)
    tw = draw.textlength(TITLE_TEXT, font=title_font)
    draw.text(((width - tw) / 2, title_y), TITLE_TEXT,
              fill=ESPRESSO, font=title_font)

    sub_y = title_y + pt_to_px(32)
    sw = draw.textlength(SUBTITLE_TEXT, font=sub_font)
    draw.text(((width - sw) / 2, sub_y), SUBTITLE_TEXT,
              fill=INK_OUTSIDE, font=sub_font)

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

    regions = build_silhouette(PAGE_W_PX, PAGE_H_PX)

    font = ImageFont.truetype(FONT_PATH, pt_to_px(FONT_SIZE_PT))
    line_height = int(pt_to_px(FONT_SIZE_PT) * LINE_HEIGHT_FACTOR)

    typeset_img = typeset(regions, corpus, font, line_height)
    final = draw_overlays(typeset_img)

    out_png = OUTPUT / "micrography_v1.png"
    final.save(out_png, dpi=(DPI, DPI))
    print(f"  → {out_png}  ({final.size[0]}×{final.size[1]} px @ {DPI} dpi)")
    print(f"  print size: {PAGE_W_MM}×{PAGE_H_MM} mm (A3 portrait)")

    # Composite of all regions for inspection
    inspection = Image.new("RGB", regions["cup_body"].size, PAPER)
    for name, fill in [("cup_body", ESPRESSO), ("crema", CREMA),
                       ("pour", ESPRESSO)]:
        layer = Image.new("RGB", regions["cup_body"].size, fill)
        inspection.paste(layer, mask=regions[name])
    inspection.thumbnail((1200, 1700), Image.Resampling.LANCZOS)
    inspection.save(OUTPUT / "micrography_v1_silhouette.png")
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
