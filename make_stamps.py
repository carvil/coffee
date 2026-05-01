"""Generate stamp design templates for hand-carving as linocut blocks.

Each design is a high-contrast black-and-white silhouette in a 100x100
coordinate space, exported as both SVG (vector, scales to any print size)
and PNG (preview at 200 dpi).

Carving workflow:
  1. Print the SVG at the size you want your block (e.g. 10x10cm)
  2. Place ink-side-down on a lino block, rub the back firmly to transfer
  3. Carve away the WHITE areas; the BLACK parts will print
  4. Ink the raised surface with a brayer, press onto paper

Outputs to output/stamps/ — one SVG + PNG per design plus a contact sheet.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output" / "stamps"
OUTPUT.mkdir(parents=True, exist_ok=True)


# ---- Helper: build a quadratic-Bezier path ----
def qbez_path(*points, closed=False):
    """Build a path from MOVETO + alternating CURVE3 control/end pairs."""
    verts = list(points)
    codes = [MplPath.MOVETO]
    i = 1
    while i < len(verts):
        codes.append(MplPath.CURVE3)
        codes.append(MplPath.CURVE3)
        i += 2
    if closed:
        verts.append(verts[0])
        codes.append(MplPath.CLOSEPOLY)
    return MplPath(verts, codes)


# ============================================================
# STAMP DESIGNS (each draws into a 100x100, y-up coordinate space)
# ============================================================

def stamp_hourglass(ax):
    """Senzu-style hourglass — two triangles meeting at a point."""
    # Top triangle (points down)
    ax.add_patch(mp.Polygon([(20, 85), (80, 85), (50, 50)], color="black"))
    # Bottom triangle (points up)
    ax.add_patch(mp.Polygon([(20, 15), (80, 15), (50, 50)], color="black"))


def stamp_bean(ax):
    """Coffee bean — oval with a single curved center crease."""
    # Bean outline
    ax.add_patch(mp.Ellipse((50, 50), 72, 52, angle=8, color="black"))
    # Crease — sigmoid curve through the middle (white)
    crease = MplPath(
        [(20, 53), (38, 38), (62, 62), (80, 47)],
        [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4],
    )
    ax.add_patch(mp.PathPatch(crease, color="white", linewidth=3.5, fill=False))


def stamp_cherry(ax):
    """Coffee cherry pair on a Y-stem with a small leaf."""
    # Stem (vertical + Y branches)
    stem = MplPath(
        [(50, 95), (50, 70), (50, 70), (32, 55),  # left branch
         (50, 70), (50, 70), (68, 55)],           # right branch
        [MplPath.MOVETO, MplPath.LINETO, MplPath.MOVETO, MplPath.LINETO,
         MplPath.MOVETO, MplPath.MOVETO, MplPath.LINETO],
    )
    ax.add_patch(mp.PathPatch(stem, color="black", linewidth=3.2, fill=False,
                              capstyle="round", joinstyle="round"))
    # Small leaf on the upper stem
    leaf = qbez_path((50, 86), (62, 92), (66, 84),
                     (62, 80), (50, 84), closed=True)
    ax.add_patch(mp.PathPatch(leaf, color="black"))
    # Two cherries
    ax.add_patch(mp.Circle((30, 38), 22, color="black"))
    ax.add_patch(mp.Circle((70, 38), 22, color="black"))
    # Highlights (small white circles to suggest sheen)
    ax.add_patch(mp.Circle((22, 46), 3.2, color="white"))
    ax.add_patch(mp.Circle((62, 46), 3.2, color="white"))


def stamp_v60(ax):
    """V60 dripper — wide rim, conical body, drip tip."""
    # Rim (top lip)
    ax.add_patch(mp.FancyBboxPatch(
        (14, 71), 72, 8, boxstyle="round,pad=0,rounding_size=2",
        color="black",
    ))
    # Cone (trapezoid pointing down)
    ax.add_patch(mp.Polygon(
        [(20, 71), (80, 71), (60, 18), (40, 18)],
        color="black",
    ))
    # Drip tip
    ax.add_patch(mp.FancyBboxPatch(
        (46, 8), 8, 10, boxstyle="round,pad=0,rounding_size=3",
        color="black",
    ))


def stamp_bloom(ax):
    """Coffea arabica blossom — 5 white petals around a stamen."""
    # 5 petals as ellipses, rotated around (50, 50)
    for angle in (0, 72, 144, 216, 288):
        e = mp.Ellipse((50, 72), 14, 36, color="black")
        e.set_transform(Affine2D().rotate_deg_around(50, 50, angle) + ax.transData)
        ax.add_patch(e)
    # Center stamen — black disk with white core
    ax.add_patch(mp.Circle((50, 50), 7, color="black"))
    ax.add_patch(mp.Circle((50, 50), 3, color="white"))


def stamp_leaf(ax):
    """Coffee leaf — pointed almond shape with center + side veins."""
    # Leaf outline (cubic Bezier)
    leaf_path = MplPath(
        [(50, 96),  # top tip
         (78, 78), (78, 50),  # right side curving down
         (50, 4),   # bottom tip
         (22, 50), (22, 78),  # left side curving up
         (50, 96)],  # close
        [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
         MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4],
    )
    ax.add_patch(mp.PathPatch(leaf_path, color="black"))
    # Center vein
    ax.add_patch(mp.PathPatch(
        MplPath([(50, 92), (50, 8)], [MplPath.MOVETO, MplPath.LINETO]),
        color="white", linewidth=2.2, fill=False,
    ))
    # Side veins — three pairs branching off the center
    for cy, dx in [(70, 14), (50, 18), (30, 14)]:
        for sign in (-1, 1):
            v = MplPath(
                [(50, cy), (50 + sign * dx * 0.5, cy - 4),
                 (50 + sign * dx, cy - 8)],
                [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3],
            )
            ax.add_patch(mp.PathPatch(v, color="white", linewidth=1.4, fill=False))


def stamp_espresso(ax):
    """Espresso cup with saucer, handle, and rising steam wisps."""
    # Cup body — slightly tapered trapezoid
    ax.add_patch(mp.Polygon(
        [(30, 68), (70, 68), (66, 32), (34, 32)],
        color="black",
    ))
    # Handle — filled annulus on the right (ring)
    ax.add_patch(mp.Wedge((76, 50), 11, -100, 100, width=5.5, color="black"))
    # Saucer — flat band beneath the cup
    ax.add_patch(mp.FancyBboxPatch(
        (16, 22), 68, 7, boxstyle="round,pad=0,rounding_size=3",
        color="black",
    ))
    # Three steam wisps rising from the cup mouth
    for x_base, phase_offset in [(40, 0), (50, 1), (60, 2)]:
        wisp = MplPath(
            [(x_base, 76), (x_base - 4 + phase_offset, 84),
             (x_base + 4 - phase_offset, 88), (x_base, 95)],
            [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4],
        )
        ax.add_patch(mp.PathPatch(wisp, color="black", linewidth=2.4,
                                  fill=False, capstyle="round"))


def stamp_kettle(ax):
    """Pour-over gooseneck kettle — body, gooseneck spout, handle, lid."""
    # Body — rounded rectangle
    ax.add_patch(mp.FancyBboxPatch(
        (28, 18), 42, 50, boxstyle="round,pad=0,rounding_size=4",
        color="black",
    ))
    # Bottom band slightly wider — like a base
    ax.add_patch(mp.FancyBboxPatch(
        (24, 14), 50, 7, boxstyle="round,pad=0,rounding_size=2",
        color="black",
    ))
    # Lid (rounded rectangle on top of body)
    ax.add_patch(mp.FancyBboxPatch(
        (36, 68), 26, 6, boxstyle="round,pad=0,rounding_size=2",
        color="black",
    ))
    # Lid knob
    ax.add_patch(mp.Circle((49, 76), 3, color="black"))
    # Gooseneck spout — curved tube on the upper-left
    spout = MplPath(
        [(28, 60),                     # attach to body
         (10, 60), (8, 78),             # curve up
         (12, 88),                      # tip area
         (12, 88), (16, 88)],           # tip end
        [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
         MplPath.MOVETO, MplPath.LINETO],
    )
    ax.add_patch(mp.PathPatch(spout, color="black", linewidth=6.5,
                              fill=False, capstyle="round", joinstyle="round"))
    # Handle on the right — D-shaped loop
    ax.add_patch(mp.Wedge((78, 45), 13, -85, 85, width=5, color="black"))


# ---- Stamp registry ----
STAMPS = [
    ("01_hourglass",  "Senzu hourglass",    "★",      stamp_hourglass),
    ("02_bean",       "Coffee bean",         "★",      stamp_bean),
    ("03_cherry",     "Coffee cherry pair",  "★",      stamp_cherry),
    ("04_v60",        "V60 dripper",         "★★",     stamp_v60),
    ("05_bloom",      "Coffea arabica bloom","★★",     stamp_bloom),
    ("06_leaf",       "Coffee leaf",         "★★",     stamp_leaf),
    ("07_espresso",   "Espresso cup",        "★★★",   stamp_espresso),
    ("08_kettle",     "Pour-over kettle",    "★★★",   stamp_kettle),
]


# ---- Renderers ----

def render_one(name, draw_fn, size_cm=10):
    fig, ax = plt.subplots(figsize=(size_cm / 2.54, size_cm / 2.54), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    draw_fn(ax)
    fig.savefig(OUTPUT / f"{name}.svg", format="svg",
                bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUTPUT / f"{name}.png", format="png",
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def render_contact_sheet():
    """A4 landscape sheet, 4×2 grid showing all stamps with labels."""
    fig, axes = plt.subplots(2, 4, figsize=(11.7, 8.3), dpi=200,
                             facecolor="#FAFAF7")
    fig.suptitle("SENZU COFFEE STAMP LIBRARY",
                 fontsize=16, fontweight="bold", y=0.97, color="#1a1a1a")
    fig.text(0.5, 0.92, "8 designs · print at 100% for 10cm blocks · 50% for 5cm",
             ha="center", fontsize=8, color="#555", style="italic")

    for ax, (name, label, difficulty, fn) in zip(axes.flat, STAMPS):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#ddd")
            spine.set_linewidth(0.6)
        fn(ax)
        ax.set_title(f"{label}  {difficulty}",
                     fontsize=9, color="#1a1a1a", pad=6)
        ax.text(0.5, -0.09, name, ha="center", va="top",
                transform=ax.transAxes, fontsize=6, color="#888",
                family="monospace")

    fig.tight_layout(rect=[0.02, 0.04, 0.98, 0.90])
    fig.savefig(OUTPUT / "contact_sheet.svg", format="svg",
                facecolor="#FAFAF7")
    fig.savefig(OUTPUT / "contact_sheet.png", format="png",
                facecolor="#FAFAF7")
    plt.close(fig)


def write_materials_md():
    body = """# Stamp library — materials & technique

Eight stamp designs for hand-carving as linocut blocks. Each `.svg` is
vector and scales to any print size — print at 100% for a 10×10cm block,
or at 50% for a 5×5cm block.

## Materials (around €40 total)

| Item | Purpose | Approx. cost |
|---|---|---|
| Lino blocks (5×5cm or 10×10cm, qty 8–10) | one per design | €10–15 |
| Lino cutters set with V and U gouges | carving | €10–15 |
| Black water-based block printing ink | inking | €5–8 |
| Brayer (small rubber roller) | even ink application | €5–8 |
| Glass or acrylic slab (A4 size) | for rolling out ink | €5 |
| Heavyweight matte paper (220 gsm+) | final prints | scrap or A3 pack ~€8 |
| Tracing paper or cheap printer paper | transferring designs | from your printer |
| Pencil (HB or B) | rubbing transfer | already have |

Recommended European suppliers: **Cowling & Wilcox** (UK, ships EU),
**Boesner** (DE/PT/FR), **Manufactum** (DE), or any well-stocked art shop
in Porto (e.g. **Firmo**).

## Carving order — easiest to hardest

| # | Design | Difficulty |
|---|---|---|
| 1 | Senzu hourglass | ★ |
| 2 | Coffee bean | ★ |
| 3 | Coffee cherry pair | ★ |
| 4 | V60 dripper | ★★ |
| 5 | Coffea arabica bloom | ★★ |
| 6 | Coffee leaf | ★★ |
| 7 | Espresso cup | ★★★ |
| 8 | Pour-over kettle | ★★★ |

The first three are great practice — mostly straight lines and circles.
The last two have curved details (handle, gooseneck) where slips will show.

## Technique

**Transfer the design to lino:**
1. Print the SVG at the target physical size (10×10cm or 5×5cm).
2. Scribble heavily over the back of the print with a pencil (graphite layer).
3. Place print **face-up** on the lino block, lined up with the edges.
4. Trace over every line with the pencil firmly. The pressure transfers the
   graphite onto the lino as a mirror image.
5. Lift the paper — you should see a faint copy on the lino. Re-draw it with
   a fine pen to make it visible.

**Carve:**
1. Carve away **everything that should print white** — the inverse of what
   you see in the design files. The black areas stay raised.
2. Start with a fine V-tool to outline the shapes, then a wider U-gouge to
   clear the larger background areas.
3. Always cut **away from your fingers**. Lino dust is harmless but messy.

**Print:**
1. Squeeze ink onto the glass slab and roll it out with the brayer until
   thin and even (you'll hear a tacky "shhh" sound).
2. Roll ink onto the carved block — multiple light passes, not one heavy one.
3. Lay paper on top of the inked block (or stamp the block onto paper —
   either works).
4. Rub the back of the paper firmly with the back of a spoon, your hand, or
   a baren. Pressure must be even across the whole image.
5. Lift the paper carefully. Re-ink for the next print.

## Composing a poster

Once you have the stamps, compose them on a single sheet:

- **Grid layout** — 4×2 or 5×3, all stamps in rows. Reads as a "type
  specimen" or specimen sheet.
- **Specimen plate** — one stamp big in the center, smaller variants around it.
- **Periodic table** — each stamp in a labelled cell with origin annotations
  (e.g. "the V60 stamp is used for these 12 coffees").
- **Repeat patterns** — same stamp printed in a tessellation, like wallpaper.
  The bean and cherry stamps work especially well repeated.

A rough first poster: pick 4–6 stamps you like, lay out a 3×2 grid on A3
paper, and print each one onto the paper using a kitchen-spoon press.
Mistakes and double-prints are part of the charm — don't try to make it
perfect.
"""
    (OUTPUT / "MATERIALS.md").write_text(body)


def main() -> int:
    print(f"Rendering {len(STAMPS)} stamps to {OUTPUT}/")
    for name, label, difficulty, fn in STAMPS:
        render_one(name, fn)
        print(f"  → {name}.svg  +  .png   ({label}  {difficulty})")
    print("Rendering contact sheet...")
    render_contact_sheet()
    print(f"  → contact_sheet.svg  +  .png")
    write_materials_md()
    print(f"  → MATERIALS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
