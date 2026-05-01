"""Render zoomed regional A3 maps with finca callouts.

For each region, produces:
  - output/map_<region>.pdf   (print-ready, vector)
  - output/map_<region>.png   (preview at 300 dpi)

Style: Senzu-inspired — saturated single color per sheet, white paper, hairline
country outlines, finca callouts in fine print readable up close.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

NE_PATH = DATA / "ne_50m_admin_0_countries.geojson"

# A3 landscape in inches
A3_W, A3_H = 16.54, 11.69
DPI = 200  # for preview PNG; PDF is vector

PAPER = "#FAFAF7"
TEXT_DARK = "#1A1A1A"
TEXT_MID = "#666666"
CONTEXT_OUTLINE = "#D8D5CC"

REGIONS = {
    "east_africa": {
        "title": "EAST AFRICAN HIGHLANDS",
        "subtitle": "ETIÓPIA · QUÉNIA · UGANDA · RUANDA",
        "highlight": ["Ethiopia", "Kenya", "Uganda", "Rwanda"],
        "context": ["United Republic of Tanzania", "South Sudan", "Burundi",
                    "Somalia", "Somaliland", "Eritrea", "Djibouti",
                    "Democratic Republic of the Congo"],
        "extent": ((27.5, 43), (-3, 15.5)),
        "color": "#82213A",
        "min_step_lat": 0.85,
        "force_side": "left",  # Ethiopia dominates the right; push all labels left
    },
    "central_america": {
        "title": "CENTRAL AMERICAN PACIFIC",
        "subtitle": "GUATEMALA · EL SALVADOR · HONDURAS · COSTA RICA · PANAMÁ",
        "highlight": ["Guatemala", "El Salvador", "Honduras", "Costa Rica", "Panama"],
        "context": ["Mexico", "Belize", "Nicaragua", "Colombia", "Cuba"],
        "extent": ((-93, -77), (6.5, 17.5)),
        "color": "#B5734F",
        "min_step_lat": 0.80,
    },
    "south_america": {
        "title": "SOUTH AMERICA",
        "subtitle": "COLÔMBIA · BRASIL",
        "highlight": ["Colombia", "Brazil"],
        "context": ["Venezuela", "Ecuador", "Peru", "Bolivia", "Paraguay",
                    "Argentina", "Panama", "Guyana", "Suriname", "French Guiana"],
        "extent": ((-79, -38), (-22, 12)),
        "color": "#4F7A2C",
        "min_step_lat": 1.6,
    },
}

# Two visual presets — soft (low contrast, lots of paper showing) and bold
# (Senzu-card style, solid color blocks). Both render so you can compare.
STYLES = {
    "soft": {
        "fill_alpha": 0.18,
        "country_outline_lw": 0.7,
        "country_outline_color": None,  # use saturated color (handled in render)
        "context_outline": "#D8D5CC",
        "context_outline_lw": 0.4,
        "pin_size": 5.0,
        "pin_face": "color",
        "pin_edge": "white",
        "pin_edge_lw": 0.8,
        "leader_color": TEXT_MID,
        "leader_alpha": 0.7,
        "leader_lw": 0.32,
        "title_weight": "bold",
        "label_dark": TEXT_DARK,
        "label_mid": TEXT_MID,
    },
    "bold": {
        "fill_alpha": 1.0,           # solid color block — Senzu-card style
        "country_outline_lw": 1.4,   # white border separates touching highlight countries
        "country_outline_color": PAPER,
        "context_outline": "#A8A39A",  # darker, more visible from afar
        "context_outline_lw": 0.9,
        "pin_size": 7.5,
        "pin_face": "white",
        "pin_edge": "color",
        "pin_edge_lw": 1.0,
        "leader_color": "#2A2A2A",
        "leader_alpha": 0.85,
        "leader_lw": 0.45,
        "title_weight": "black",
        "label_dark": "#0A0A0A",
        "label_mid": "#444444",
    },
}


def load_countries() -> dict[str, dict]:
    with NE_PATH.open() as f:
        data = json.load(f)
    return {f["properties"]["NAME"]: f["geometry"] for f in data["features"]}


def geom_to_polys(geom: dict) -> list[list]:
    """Return a flat list of outer rings (ignoring holes for simplicity)."""
    if geom is None:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def draw_country(ax, geom, fill=None, edge=None, linewidth=0.4, zorder=1, alpha=1.0):
    rings = geom_to_polys(geom)
    for ring in rings:
        xs, ys = zip(*ring)
        if fill is not None:
            ax.fill(xs, ys, color=fill, alpha=alpha, zorder=zorder, edgecolor="none")
        if edge is not None:
            ax.plot(xs, ys, color=edge, linewidth=linewidth, zorder=zorder + 0.5,
                    solid_capstyle="round", solid_joinstyle="round")


def place_labels(ax, pins, color, extent, style, min_step_lat=1.0, force_side=None):
    """Two label columns just outside the highlight extent. Country fill in
    the margin is masked by render_region, so labels sit on white space.

    force_side='left' or 'right' overrides the longitude-based split and sends
    every pin to that single column. Useful when the country geometry is
    asymmetric (e.g. Ethiopia dominating the right side of East Africa).
    """
    (lon_min, lon_max), (lat_min, lat_max) = extent
    mid_lon = (lon_min + lon_max) / 2

    if force_side == "left":
        left, right = sorted(pins, key=lambda p: -p["lat"]), []
    elif force_side == "right":
        left, right = [], sorted(pins, key=lambda p: -p["lat"])
    else:
        left = sorted([p for p in pins if p["lon"] < mid_lon], key=lambda p: -p["lat"])
        right = sorted([p for p in pins if p["lon"] >= mid_lon], key=lambda p: -p["lat"])

    span = lon_max - lon_min
    pad = span * 0.02
    left_col_x = lon_min - pad      # just outside the country area on left
    right_col_x = lon_max + pad     # just outside on right

    def stack(group, col_x, anchor):
        if not group:
            return
        n = len(group)
        avg_lat = sum(p["lat"] for p in group) / n
        total_h = (n - 1) * min_step_lat
        top = avg_lat + total_h / 2
        slack = (lat_max - lat_min) * 0.04
        if top > lat_max + slack:
            top = lat_max + slack
        if top - total_h < lat_min - slack:
            top = lat_min - slack + total_h

        ys = [top - i * min_step_lat for i in range(n)]
        for pin, ly in zip(group, ys):
            farm = pin.get("farm") or pin.get("region") or pin["country"]
            region = pin.get("region") or ""
            country = pin["country"]
            label_sub = f"{region}, {country}" if region else country
            variety = pin.get("variety", "")

            kink_x = col_x + (-pad * 0.5 if anchor == "left" else pad * 0.5)
            ax.plot([pin["lon"], kink_x, col_x],
                    [pin["lat"], ly, ly],
                    color=style["leader_color"],
                    linewidth=style.get("leader_lw", 0.32),
                    zorder=7,
                    solid_capstyle="round", solid_joinstyle="round",
                    alpha=style["leader_alpha"])

            # Text extends OUTWARD into the margin (away from country):
            # left column → ha="right" (text extends LEFT from col_x)
            # right column → ha="left"  (text extends RIGHT from col_x)
            ha = "right" if anchor == "left" else "left"
            ax.text(col_x, ly + 0.1, farm, fontsize=7.1, ha=ha, va="bottom",
                    color=style["label_dark"], fontfamily="sans-serif",
                    fontweight="medium", zorder=8)
            ax.text(col_x, ly - 0.05, label_sub, fontsize=5.5, ha=ha, va="top",
                    color=style["label_mid"], fontfamily="sans-serif", zorder=8)
            if variety:
                tracked = " ".join(variety.upper())
                ax.text(col_x, ly - 0.42, tracked, fontsize=4.25, ha=ha, va="top",
                        color=color, fontfamily="sans-serif", zorder=8)

    stack(left, left_col_x, "left")
    stack(right, right_col_x, "right")


# (inset rendering removed for now — Asia is dropped until critical mass)


def render_region(region_key, coffees, countries, style_name):
    cfg = REGIONS[region_key]
    color = cfg["color"]
    style = STYLES[style_name]

    fig = plt.figure(figsize=(A3_W, A3_H), dpi=DPI, facecolor=PAPER)
    ax = fig.add_axes([0.04, 0.06, 0.92, 0.84])
    ax.set_facecolor(PAPER)

    pins = [c for c in coffees if c["country"] in cfg["highlight"]]
    pins.sort(key=lambda p: (p["country"], p.get("region") or "", p["filename"]))

    (lon_min, lon_max), (lat_min, lat_max) = cfg["extent"]
    label_pad_lon = (lon_max - lon_min) * cfg.get("label_pad_lon_frac", 0.22)
    ax.set_xlim(lon_min - label_pad_lon, lon_max + label_pad_lon)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    context_lw = style.get("context_outline_lw", 0.4)
    # Context countries — outline only
    for name in cfg["context"]:
        if name in countries:
            draw_country(ax, countries[name], fill=None,
                         edge=style["context_outline"], linewidth=context_lw, zorder=1)

    # Highlight countries — fill, with separate edge color (white in bold mode
    # so internal country boundaries show against the colored block)
    edge_color = style.get("country_outline_color") or color
    for name in cfg["highlight"]:
        if name in countries:
            draw_country(ax, countries[name],
                         fill=color, edge=edge_color,
                         linewidth=style["country_outline_lw"],
                         zorder=2, alpha=style["fill_alpha"])

    # Mask country fill that extends into the L/R label margins.
    xlim_lo, xlim_hi = ax.get_xlim()
    ax.fill([xlim_lo, lon_min, lon_min, xlim_lo],
            [lat_min - 5, lat_min - 5, lat_max + 5, lat_max + 5],
            color=PAPER, zorder=3, edgecolor="none")
    ax.fill([lon_max, xlim_hi, xlim_hi, lon_max],
            [lat_min - 5, lat_min - 5, lat_max + 5, lat_max + 5],
            color=PAPER, zorder=3, edgecolor="none")
    # Re-draw context outlines on top of the mask so they show in margins
    for name in cfg["context"]:
        if name in countries:
            draw_country(ax, countries[name], fill=None,
                         edge=style["context_outline"], linewidth=context_lw, zorder=4)

    # Pins — face/edge depends on style
    pin_face = color if style["pin_face"] == "color" else style["pin_face"]
    pin_edge = color if style["pin_edge"] == "color" else style["pin_edge"]
    for pin in pins:
        ax.plot(pin["lon"], pin["lat"], "o", markersize=style["pin_size"],
                color=pin_face, markeredgecolor=pin_edge,
                markeredgewidth=style["pin_edge_lw"], zorder=10)

    # Labels with callouts. Per-region min_step + optional force_side.
    place_labels(ax, pins, color, cfg["extent"], style,
                 min_step_lat=cfg.get("min_step_lat", 1.0),
                 force_side=cfg.get("force_side"))

    # Title block
    fig.text(0.5, 0.945, cfg["title"], ha="center", va="top",
             fontsize=34.5, color=color, fontfamily="sans-serif",
             fontweight=style["title_weight"])
    fig.text(0.5, 0.905, cfg["subtitle"], ha="center", va="top",
             fontsize=12, color=style["label_dark"],
             fontfamily="sans-serif", fontweight="light")

    # Footer — count + signature
    n = len(pins)
    fig.text(0.5, 0.035,
             f"{n}  COFFEES   ·   COLLECTED FROM SENZU COFFEE ROASTERS   ·   ROASTED IN PORTO",
             ha="center", va="bottom", fontsize=8, color=style["label_mid"],
             fontfamily="sans-serif")

    out = OUTPUT / f"map_{region_key}_{style_name}"
    fig.savefig(f"{out}.pdf", facecolor=PAPER, bbox_inches=None)
    fig.savefig(f"{out}.png", facecolor=PAPER, bbox_inches=None, dpi=DPI)
    plt.close(fig)
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--styles", nargs="+", default=["bold"],
                        choices=list(STYLES),
                        help="Which style preset(s) to render. Default: bold only.")
    args = parser.parse_args()

    coffees = json.loads((DATA / "coffees.json").read_text())
    countries = load_countries()
    print(f"Loaded {len(coffees)} coffees, {len(countries)} country geometries.\n")

    for region_key in REGIONS:
        cfg = REGIONS[region_key]
        n = sum(1 for c in coffees if c["country"] in cfg["highlight"])
        for style_name in args.styles:
            print(f"Rendering {region_key} ({n} pins) — {style_name}...")
            out = render_region(region_key, coffees, countries, style_name)
            print(f"  → {out}.pdf  +  {out}.png")


if __name__ == "__main__":
    main()
