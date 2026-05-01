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

# ---- Page setup ----
# A2 portrait, in mm. We render at MM_PER_PX so the final raster is print-grade.
PAGE_W_MM, PAGE_H_MM = 420, 594  # A2 portrait
DPI = 220
MM_PER_INCH = 25.4
PX = lambda mm: int(round(mm / MM_PER_INCH * DPI))
PAGE_W_PX, PAGE_H_PX = PX(PAGE_W_MM), PX(PAGE_H_MM)

# Margins for title + footer (where no text fill happens)
MARGIN_TOP_MM = 40
MARGIN_BOTTOM_MM = 30
MARGIN_SIDE_MM = 35

# Body text
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"
FONT_SIZE_PT = 7.0
LINE_HEIGHT_FACTOR = 1.05  # tight — we want the lines to read as a solid block

# Title typography
TITLE_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
TITLE_TEXT = "37 COFFEES"
SUBTITLE_TEXT = "SENZU COFFEE ROASTERS · ROASTED IN PORTO"

# Colors
PAPER = (250, 248, 243)        # warm off-white
INK = (24, 12, 8)              # very dark warm-brown
SILHOUETTE_TINT = (235, 228, 215)  # very faint warm tint behind the text
CONTEXT_LINE = (200, 195, 185)


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
    """Return an L-mode mask where 255 = where text goes, 0 = empty paper.

    Layered composition (top to bottom):
        1. V60 rim (handle/lip)
        2. V60 cone (filter holder, tapers down)
        3. small gap with a drip
        4. Carafe mouth (narrower than body)
        5. Carafe body (cylinder with rounded bottom)
        6. Pour spout (triangular beak, right side)
        7. Saucer
    """
    mask = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(mask)

    cx = width // 2
    top_y = PX(MARGIN_TOP_MM + 60)

    # Sizes in mm
    rim_w_mm, rim_h_mm = 230, 12
    cone_top_w_mm, cone_bot_w_mm, cone_h_mm = 215, 38, 125
    drip_gap_mm = 18                   # air between cone tip and carafe
    carafe_mouth_w_mm, carafe_mouth_h_mm = 175, 26
    carafe_body_w_mm, carafe_body_h_mm = 230, 240
    spout_w_mm, spout_h_mm = 32, 36
    saucer_w_mm, saucer_h_mm = 290, 10
    body_radius_mm = 28
    mouth_radius_mm = 6

    # Y coordinates
    rim_y0 = top_y
    rim_y1 = rim_y0 + PX(rim_h_mm)
    cone_y0 = rim_y1
    cone_y1 = cone_y0 + PX(cone_h_mm)
    drip_y0 = cone_y1
    drip_y1 = drip_y0 + PX(drip_gap_mm)
    mouth_y0 = drip_y1
    mouth_y1 = mouth_y0 + PX(carafe_mouth_h_mm)
    body_y0 = mouth_y1 - PX(6)         # body slightly overlaps mouth bottom
    body_y1 = body_y0 + PX(carafe_body_h_mm)
    saucer_y0 = body_y1
    saucer_y1 = saucer_y0 + PX(saucer_h_mm)

    # ---- V60 rim ----
    d.rounded_rectangle(
        [cx - PX(rim_w_mm) // 2, rim_y0, cx + PX(rim_w_mm) // 2, rim_y1],
        radius=PX(4), fill=255,
    )

    # ---- V60 cone ----
    d.polygon([
        (cx - PX(cone_top_w_mm) // 2, cone_y0),
        (cx + PX(cone_top_w_mm) // 2, cone_y0),
        (cx + PX(cone_bot_w_mm) // 2, cone_y1),
        (cx - PX(cone_bot_w_mm) // 2, cone_y1),
    ], fill=255)

    # ---- Drip in the air-gap ----
    drip_w = PX(8)
    drip_h = PX(drip_gap_mm - 4)
    drip_x0 = cx - drip_w // 2
    drip_y_mid = (drip_y0 + drip_y1) // 2
    d.ellipse(
        [drip_x0, drip_y_mid - drip_h // 2,
         drip_x0 + drip_w, drip_y_mid + drip_h // 2],
        fill=255,
    )

    # ---- Carafe body ----
    body_x0 = cx - PX(carafe_body_w_mm) // 2
    body_x1 = cx + PX(carafe_body_w_mm) // 2
    d.rounded_rectangle(
        [body_x0, body_y0, body_x1, body_y1],
        radius=PX(body_radius_mm), fill=255,
    )

    # ---- Carafe mouth (narrower lip on top of body) ----
    mouth_x0 = cx - PX(carafe_mouth_w_mm) // 2
    mouth_x1 = cx + PX(carafe_mouth_w_mm) // 2
    d.rounded_rectangle(
        [mouth_x0, mouth_y0, mouth_x1, mouth_y1],
        radius=PX(mouth_radius_mm), fill=255,
    )

    # ---- Pour spout — clear forward-pointing beak from upper-right ----
    # Anchored on the body's right edge near the top, extending right.
    sx_anchor = body_x1
    sy_top = body_y0 + PX(8)
    sy_bot = sy_top + PX(spout_h_mm)
    d.polygon([
        (sx_anchor - PX(8), sy_top),
        (sx_anchor + PX(spout_w_mm), sy_top + PX(spout_h_mm * 0.55)),
        (sx_anchor - PX(8), sy_bot),
    ], fill=255)

    # ---- Saucer ----
    d.rounded_rectangle(
        [cx - PX(saucer_w_mm) // 2, saucer_y0,
         cx + PX(saucer_w_mm) // 2, saucer_y1],
        radius=PX(2), fill=255,
    )

    return mask


# ---- Typesetter ----

def typeset(mask: Image.Image, corpus: str, font: ImageFont.FreeTypeFont,
            line_height: int) -> Image.Image:
    """Walk the mask row-by-row at line_height intervals; for each row find
    the contiguous dark horizontal segments; fill each with characters from
    the corpus. Returns a final RGB image rendered on PAPER.
    """
    width, height = mask.size
    out = Image.new("RGB", (width, height), PAPER)
    # Paint a very faint tint inside the silhouette so the shape reads as a
    # block from afar even where text is sparse (e.g. line gaps, narrow rows).
    tint = Image.new("RGB", (width, height), SILHOUETTE_TINT)
    out.paste(tint, mask=mask)
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
            # Draw text inside segment
            draw.text((x0, y + text_baseline_offset), text,
                      font=font, fill=INK)

        y += line_height

    return out


def draw_overlays(img: Image.Image) -> Image.Image:
    """Draw title above and footer below the silhouette."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(34))
    sub_font = ImageFont.truetype(TITLE_FONT_PATH, pt_to_px(11))

    # Title near the top
    title_y = PX(MARGIN_TOP_MM)
    tw = draw.textlength(TITLE_TEXT, font=title_font)
    draw.text(((width - tw) / 2, title_y), TITLE_TEXT, fill=INK, font=title_font)

    # Subtitle below title
    sub_y = title_y + pt_to_px(38)
    sw = draw.textlength(SUBTITLE_TEXT, font=sub_font)
    draw.text(((width - sw) / 2, sub_y), SUBTITLE_TEXT,
              fill=CONTEXT_LINE, font=sub_font)

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
    print(f"  print size: {PAGE_W_MM}×{PAGE_H_MM} mm (A2 portrait)")

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
