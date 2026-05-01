"""Generate a micrography poster: a coffee silhouette filled with text from
the coffee dataset.

From across the room: a strong silhouette. Up close: every line is your
coffee history — countries, farms, tasting notes, blurbs.

Outputs:
  output/micrography/micrography_v1.png   (preview at chosen DPI)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output" / "micrography"
OUTPUT.mkdir(parents=True, exist_ok=True)

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

# Top-down composition palette: dark shadow + white saucer + dark espresso
# inside the cup, with a golden crema disc and a silver spoon.
PAPER = (250, 248, 243)
ESPRESSO = (38, 22, 18)          # #261612 deep coffee — used for shadow + cup interior
CREMA = (194, 136, 64)           # #C28840 warm gold
SAUCER_FILL = (245, 240, 230)    # slightly cooler than paper so the white ceramic reads
SPOON_FILL = (90, 78, 70)        # silvery brown — silver in shadow
OUTLINE = (38, 22, 18)           # near-black for thin edges
INK_ON_DARK = (250, 245, 230)    # cream text inside espresso/shadow
INK_ON_CREMA = (38, 22, 18)      # dark text inside crema
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
    """Top-down view of an espresso cup on a saucer with an offset shadow
    behind for depth. A spoon rests on the saucer at an angle.

    Concentric ellipses + offset shadow gives strong 3D feel even though
    everything is rendered as flat fills. Inspired by Image 1 reference.

    Regions returned (each L-mode, 255 = this region):
        shadow      — crescent of shadow visible past the saucer
        saucer      — white-ceramic ring between saucer edge and cup edge
        cup_rim     — narrow ring of cup wall (white ceramic)
        cup_interior— dark espresso visible inside the cup, minus crema
        crema       — golden disc on the espresso surface, slightly off-center
        spoon       — small angled shape on the saucer
    Plus outlines for thin dark strokes.
    """
    from PIL import ImageChops
    import math

    # Sizes (mm)
    saucer_r = 108
    cup_outer_r = 64
    cup_inner_r = 56
    crema_r_x = 48
    crema_r_y = 44
    crema_off_x = -3
    crema_off_y = -6

    shadow_off_x = 22
    shadow_off_y = 22
    shadow_r_x = 108
    shadow_r_y = 100

    # Layout — center the composition vertically in available area
    avail_top_mm = MARGIN_TOP_MM + 38
    avail_bot_mm = PAGE_H_MM - MARGIN_BOTTOM_MM - 22
    composition_top_mm = avail_top_mm + 8
    saucer_cy_mm = composition_top_mm + saucer_r
    saucer_cx_mm = PAGE_W_MM // 2 - 6   # nudge slightly left so shadow has room

    sx = PX(saucer_cx_mm)
    sy = PX(saucer_cy_mm)

    # ---- Shadow ellipse ----
    shadow_full = Image.new("L", (width, height), 0)
    ImageDraw.Draw(shadow_full).ellipse([
        sx + PX(shadow_off_x) - PX(shadow_r_x),
        sy + PX(shadow_off_y) - PX(shadow_r_y),
        sx + PX(shadow_off_x) + PX(shadow_r_x),
        sy + PX(shadow_off_y) + PX(shadow_r_y),
    ], fill=255)

    # ---- Saucer (full disc) ----
    saucer_full = Image.new("L", (width, height), 0)
    ImageDraw.Draw(saucer_full).ellipse([
        sx - PX(saucer_r), sy - PX(saucer_r),
        sx + PX(saucer_r), sy + PX(saucer_r),
    ], fill=255)

    # ---- Cup outer ----
    cup_outer = Image.new("L", (width, height), 0)
    ImageDraw.Draw(cup_outer).ellipse([
        sx - PX(cup_outer_r), sy - PX(cup_outer_r),
        sx + PX(cup_outer_r), sy + PX(cup_outer_r),
    ], fill=255)

    # ---- Cup inner (interior of cup) ----
    cup_inner = Image.new("L", (width, height), 0)
    ImageDraw.Draw(cup_inner).ellipse([
        sx - PX(cup_inner_r), sy - PX(cup_inner_r),
        sx + PX(cup_inner_r), sy + PX(cup_inner_r),
    ], fill=255)

    # ---- Crema disc, slightly off-center ----
    crema_mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(crema_mask).ellipse([
        sx + PX(crema_off_x) - PX(crema_r_x),
        sy + PX(crema_off_y) - PX(crema_r_y),
        sx + PX(crema_off_x) + PX(crema_r_x),
        sy + PX(crema_off_y) + PX(crema_r_y),
    ], fill=255)

    # ---- Spoon: oval bowl + tapered handle, like a real teaspoon ----
    # Bowl rests near the cup edge; handle extends out across the saucer
    # toward the upper-left.
    spoon_mask = Image.new("L", (width, height), 0)
    sd = ImageDraw.Draw(spoon_mask)

    # Geometry (mm)
    bowl_length_mm = 18
    bowl_width_mm = 12
    handle_length_mm = 56
    handle_w_bowl_mm = 5.5    # at the bowl junction
    handle_w_tip_mm = 3.0     # at the far tip
    handle_inset_mm = 2.0     # handle starts slightly inside the bowl edge

    # Bowl center placement — just inside the cup, biased toward upper-left
    bowl_cx_mm = saucer_cx_mm - 14
    bowl_cy_mm = saucer_cy_mm - 18
    bowl_cx_px = PX(bowl_cx_mm)
    bowl_cy_px = PX(bowl_cy_mm)

    # Spoon's long axis direction (handle goes upper-left from bowl)
    # 210° in math = pointing upper-left in PIL screen coords (y-flipped)
    spoon_angle = math.radians(210)
    cos_a, sin_a = math.cos(spoon_angle), math.sin(spoon_angle)

    def to_world(lx, ly):
        return (bowl_cx_px + lx * cos_a - ly * sin_a,
                bowl_cy_px + lx * sin_a + ly * cos_a)

    # Bowl as an oval, approximated by 36 points
    a = PX(bowl_length_mm) / 2     # semi-major (along spoon axis)
    b = PX(bowl_width_mm) / 2      # semi-minor (perpendicular)
    bowl_pts = []
    n = 36
    for i in range(n):
        t = 2 * math.pi * i / n
        bowl_pts.append(to_world(a * math.cos(t), b * math.sin(t)))
    sd.polygon(bowl_pts, fill=255)

    # Handle: tapered trapezoid extending from bowl back edge toward tip
    handle_x_start = a - PX(handle_inset_mm)
    handle_x_end = handle_x_start + PX(handle_length_mm)
    half_w_bowl = PX(handle_w_bowl_mm) / 2
    half_w_tip = PX(handle_w_tip_mm) / 2
    handle_pts = [
        to_world(handle_x_start, -half_w_bowl),
        to_world(handle_x_end, -half_w_tip),
        to_world(handle_x_end, half_w_tip),
        to_world(handle_x_start, half_w_bowl),
    ]
    sd.polygon(handle_pts, fill=255)

    # ---- Compose disjoint regions ----
    # Shadow visible only outside saucer
    shadow_visible = ImageChops.subtract(shadow_full, saucer_full)
    # Saucer visible only outside cup
    saucer_visible = ImageChops.subtract(saucer_full, cup_outer)
    # Cup rim ring
    cup_rim = ImageChops.subtract(cup_outer, cup_inner)
    # Cup interior minus crema
    cup_interior_dark = ImageChops.subtract(cup_inner, crema_mask)
    # Spoon clipped to saucer area (so it doesn't float on background or shadow)
    spoon_visible = ImageChops.multiply(spoon_mask, saucer_full)

    return {
        "shadow": shadow_visible,
        "saucer": saucer_visible,
        "cup_rim": cup_rim,
        "cup_interior": cup_interior_dark,
        "crema": crema_mask,
        "spoon": spoon_visible,
        # Useful for outlines:
        "_saucer_full": saucer_full,
        "_cup_outer": cup_outer,
        "_cup_inner": cup_inner,
    }


# ---- Typesetter ----

def typeset(regions: dict, corpus: str, font: ImageFont.FreeTypeFont,
            line_height: int) -> Image.Image:
    """Multi-region typesetter. Each region in REGION_STYLES gets its own
    fill color and text color, with text flowing from a shared corpus cursor
    so the narrative reads top-to-bottom across regions.
    """
    width, height = regions["shadow"].size
    out = Image.new("RGB", (width, height), PAPER)

    # Order matters: shadow first (deepest layer), then saucer on top, then
    # cup, crema, spoon. Each gets its background fill, then its text.
    layers = [
        ("shadow",       ESPRESSO,       INK_ON_DARK),
        ("saucer",       SAUCER_FILL,    None),         # no text — clean ceramic
        ("cup_rim",      SAUCER_FILL,    None),
        ("cup_interior", ESPRESSO,       INK_ON_DARK),
        ("crema",        CREMA,          INK_ON_CREMA),
        ("spoon",        SPOON_FILL,     None),
    ]
    for name, fill, _ in layers:
        layer = Image.new("RGB", (width, height), fill)
        out.paste(layer, mask=regions[name])

    # Thin dark outlines on the saucer rim, cup rim, and crema edge — these
    # give the composition crisp graphic edges from afar (a la the painted
    # references).
    outline_draw = ImageDraw.Draw(out)
    for ring_name, lw in [("_saucer_full", 3), ("_cup_outer", 2),
                          ("_cup_inner", 1)]:
        # Stroke = subtract eroded mask from mask, then paint OUTLINE color
        ring = regions[ring_name]
        eroded = ring.filter(__import__("PIL.ImageFilter", fromlist=["MinFilter"]).MinFilter(2 * lw + 1))
        from PIL import ImageChops
        edge = ImageChops.subtract(ring, eroded)
        outline_layer = Image.new("RGB", (width, height), OUTLINE)
        out.paste(outline_layer, mask=edge)

    draw = ImageDraw.Draw(out)
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]
    text_baseline_offset = int(line_height * 0.08)

    cursor = 0

    def fill_region(mask_img, text_color):
        nonlocal cursor
        mask_px = mask_img.load()
        y = 0
        # Sample top, middle, bottom of each text row — text only renders
        # where the mask is "on" across the entire vertical span of the line.
        # This avoids text bleeding past curved boundaries (crema disc, saucer rim).
        while y + line_height <= height:
            sample_ys = (
                y + text_baseline_offset + 2,
                y + line_height // 2,
                y + line_height - 3,
            )
            in_seg = False
            segments = []
            seg_start = 0
            for x in range(width):
                all_on = (mask_px[x, sample_ys[0]] > 127
                          and mask_px[x, sample_ys[1]] > 127
                          and mask_px[x, sample_ys[2]] > 127)
                if all_on and not in_seg:
                    seg_start = x
                    in_seg = True
                elif not all_on and in_seg:
                    segments.append((seg_start, x))
                    in_seg = False
            if in_seg:
                segments.append((seg_start, width))

            for x0, x1 in segments:
                seg_w = x1 - x0
                n_chars = max(1, seg_w // char_w)
                pieces = []
                remaining = n_chars
                while remaining > 0:
                    avail = len(corpus) - cursor
                    take = min(avail, remaining)
                    pieces.append(corpus[cursor:cursor + take])
                    cursor = (cursor + take) % len(corpus)
                    remaining -= take
                draw.text((x0, y + text_baseline_offset), "".join(pieces),
                          font=font, fill=text_color)
            y += line_height

    # Render text into the regions that take it (shadow first — biggest mass)
    for name, _, text_color in layers:
        if text_color is not None:
            fill_region(regions[name], text_color)

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
    inspection_size = regions["shadow"].size
    inspection = Image.new("RGB", inspection_size, PAPER)
    for name, fill in [("shadow", ESPRESSO), ("saucer", SAUCER_FILL),
                       ("cup_rim", SAUCER_FILL),
                       ("cup_interior", ESPRESSO), ("crema", CREMA),
                       ("spoon", SPOON_FILL)]:
        layer = Image.new("RGB", inspection_size, fill)
        inspection.paste(layer, mask=regions[name])
    inspection.thumbnail((1200, 1700), Image.Resampling.LANCZOS)
    inspection.save(OUTPUT / "micrography_v1_silhouette.png")
    print(f"  → output/micrography/micrography_v1_silhouette.png  (silhouette only)")

    small = final.copy()
    small.thumbnail((1400, 2000), Image.Resampling.LANCZOS)
    small.save(OUTPUT / "micrography_v1_preview.png")
    print(f"  → output/micrography/micrography_v1_preview.png  (scaled preview)")

    # Detail crop — middle 1/3 of the carafe at full resolution, to show
    # what the text actually looks like up close.
    cw, ch = final.size
    cx, cy = cw // 2, int(ch * 0.62)
    crop_w, crop_h = cw // 2, ch // 5
    detail = final.crop((cx - crop_w // 2, cy - crop_h // 2,
                         cx + crop_w // 2, cy + crop_h // 2))
    detail.save(OUTPUT / "micrography_v1_detail.png")
    print(f"  → output/micrography/micrography_v1_detail.png  (detail crop, carafe middle)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
