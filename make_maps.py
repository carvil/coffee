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
        "extent": ((27.5, 43), (-3, 15.5)),  # (lon, lat) — tight on the highlands
        "color": "#82213A",
    },
    "central_america": {
        "title": "CENTRAL AMERICAN PACIFIC",
        "subtitle": "GUATEMALA · EL SALVADOR · HONDURAS · COSTA RICA · PANAMÁ",
        "highlight": ["Guatemala", "El Salvador", "Honduras", "Costa Rica", "Panama"],
        "context": ["Mexico", "Belize", "Nicaragua", "Colombia", "Cuba"],
        "extent": ((-93, -77), (6.5, 17.5)),  # crop most of Mexico
        "color": "#B5734F",
    },
    "south_america_asia": {
        "title": "SOUTH AMERICA · ASIA",
        "subtitle": "COLÔMBIA · BRASIL · INDONÉSIA",
        "highlight": ["Colombia", "Brazil"],
        "context": ["Venezuela", "Ecuador", "Peru", "Bolivia", "Paraguay",
                    "Argentina", "Panama", "Guyana", "Suriname", "French Guiana"],
        "extent": ((-79, -36), (-23, 12)),
        "color": "#4F7A2C",
        "inset": {
            "title": "INDONÉSIA · ACEH",
            "highlight": ["Indonesia"],
            "context": ["Malaysia", "Thailand", "Singapore"],
            "extent": ((94.5, 100), (2.5, 6.5)),
            "position": (0.71, 0.10, 0.26, 0.30),  # axes rect (l, b, w, h) in fig coords
        },
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


def place_labels(ax, pins, color, extent, label_pad_lon_frac=0.02, min_step_lat=1.4):
    """Alternate sides; on each side stack labels with a guaranteed minimum
    vertical spacing so they never collide. min_step_lat is in degrees latitude.
    """
    (lon_min, lon_max), (lat_min, lat_max) = extent
    mid_lon = (lon_min + lon_max) / 2

    left = [p for p in pins if p["lon"] < mid_lon]
    right = [p for p in pins if p["lon"] >= mid_lon]
    left.sort(key=lambda p: -p["lat"])
    right.sort(key=lambda p: -p["lat"])

    pad = (lon_max - lon_min) * label_pad_lon_frac
    left_col_x = lon_min - pad
    right_col_x = lon_max + pad

    def stack(group, col_x, anchor):
        if not group:
            return
        n = len(group)
        # Center labels around average pin latitude, evenly spaced with min_step_lat
        avg_lat = sum(p["lat"] for p in group) / n
        total_h = (n - 1) * min_step_lat
        top = avg_lat + total_h / 2
        # Clamp to map area (small fudge above/below)
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

            # Leader line: pin → kink near column → horizontal into label
            kink_x = col_x + (-pad * 0.5 if anchor == "left" else pad * 0.5)
            ax.plot([pin["lon"], kink_x, col_x],
                    [pin["lat"], ly, ly],
                    color=TEXT_MID, linewidth=0.32, zorder=4,
                    solid_capstyle="round", solid_joinstyle="round", alpha=0.7)

            ha = "right" if anchor == "left" else "left"
            ax.text(col_x, ly + 0.1, farm, fontsize=6.2, ha=ha, va="bottom",
                    color=TEXT_DARK, fontfamily="sans-serif", fontweight="medium", zorder=6)
            ax.text(col_x, ly - 0.05, label_sub, fontsize=4.8, ha=ha, va="top",
                    color=TEXT_MID, fontfamily="sans-serif", zorder=6)
            if variety:
                tracked = " ".join(variety.upper())
                ax.text(col_x, ly - 0.42, tracked, fontsize=3.7, ha=ha, va="top",
                        color=color, fontfamily="sans-serif", zorder=6)

    stack(left, left_col_x, "left")
    stack(right, right_col_x, "right")


def render_inset(fig, inset_cfg, coffees, countries, color):
    """Draw a small inset map (e.g. for Indonesia) on the same figure."""
    ax = fig.add_axes(inset_cfg["position"])
    ax.set_facecolor(PAPER)

    (lon_min, lon_max), (lat_min, lat_max) = inset_cfg["extent"]
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal", adjustable="box")
    for spine in ax.spines.values():
        spine.set_edgecolor(color)
        spine.set_linewidth(0.5)
    ax.set_xticks([])
    ax.set_yticks([])

    for name in inset_cfg.get("context", []):
        if name in countries:
            draw_country(ax, countries[name], fill=None, edge=CONTEXT_OUTLINE,
                         linewidth=0.4, zorder=1)
    for name in inset_cfg["highlight"]:
        if name in countries:
            draw_country(ax, countries[name], fill=color, edge=color,
                         linewidth=0.6, zorder=2, alpha=0.18)

    # Pins inside the inset extent
    pins = [c for c in coffees
            if c["country"] in inset_cfg["highlight"]
            and lon_min <= c["lon"] <= lon_max
            and lat_min <= c["lat"] <= lat_max]
    for pin in pins:
        ax.plot(pin["lon"], pin["lat"], "o", markersize=5.5,
                color=color, markeredgecolor="white", markeredgewidth=0.7, zorder=10)
        farm = pin.get("farm") or pin["country"]
        region = pin.get("region") or ""
        ax.annotate(f"{farm}\n{region}",
                    xy=(pin["lon"], pin["lat"]),
                    xytext=(8, -8), textcoords="offset points",
                    fontsize=5.5, color=TEXT_DARK, fontfamily="sans-serif",
                    fontweight="medium", zorder=11,
                    arrowprops=dict(arrowstyle="-", color=TEXT_MID,
                                    linewidth=0.32, alpha=0.7))

    # Inset title
    x0, y0, w, h = inset_cfg["position"]
    fig.text(x0 + w / 2, y0 + h + 0.005, inset_cfg["title"],
             ha="center", va="bottom", fontsize=8, color=color,
             fontfamily="sans-serif", fontweight="bold")


def render_region(region_key, coffees, countries):
    cfg = REGIONS[region_key]
    color = cfg["color"]

    fig = plt.figure(figsize=(A3_W, A3_H), dpi=DPI, facecolor=PAPER)

    # Layout: title (top 8%), map (middle 80%), footer (bottom 7%)
    ax = fig.add_axes([0.04, 0.06, 0.92, 0.84])
    ax.set_facecolor(PAPER)

    pins = [c for c in coffees if c["country"] in cfg["highlight"]]
    pins.sort(key=lambda p: (p["country"], p.get("region") or "", p["filename"]))

    (lon_min, lon_max), (lat_min, lat_max) = cfg["extent"]
    # Expand the visible extent so labels columns to L/R have room
    label_pad_lon = (lon_max - lon_min) * 0.20
    ax.set_xlim(lon_min - label_pad_lon, lon_max + label_pad_lon)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    # Context countries — outline only
    for name in cfg["context"]:
        if name in countries:
            draw_country(ax, countries[name], fill=None, edge=CONTEXT_OUTLINE,
                         linewidth=0.4, zorder=1)

    # Highlight countries — soft tint fill + saturated outline
    for name in cfg["highlight"]:
        if name in countries:
            draw_country(ax, countries[name], fill=color, edge=color,
                         linewidth=0.7, zorder=2, alpha=0.16)

    # Pins
    for pin in pins:
        ax.plot(pin["lon"], pin["lat"], "o", markersize=5,
                color=color, markeredgecolor="white", markeredgewidth=0.8, zorder=10)

    # Labels with callouts. Step-size grows with vertical extent.
    lat_span = lat_max - lat_min
    min_step = max(0.95, lat_span / 14)
    place_labels(ax, pins, color, cfg["extent"], min_step_lat=min_step)

    # Inset (e.g. Indonesia on the South America sheet)
    if "inset" in cfg:
        render_inset(fig, cfg["inset"], coffees, countries, color)

    # Title block
    fig.text(0.5, 0.945, cfg["title"], ha="center", va="top",
             fontsize=30, color=color, fontfamily="sans-serif", fontweight="bold")
    fig.text(0.5, 0.905, cfg["subtitle"], ha="center", va="top",
             fontsize=10.5, color=TEXT_DARK, fontfamily="sans-serif",
             fontweight="light")

    # Footer — count + signature
    n = len(pins)
    fig.text(0.5, 0.035,
             f"{n}  COFFEES   ·   COLLECTED FROM SENZU COFFEE ROASTERS   ·   ROASTED IN PORTO",
             ha="center", va="bottom", fontsize=7, color=TEXT_MID,
             fontfamily="sans-serif")

    out = OUTPUT / f"map_{region_key}"
    fig.savefig(f"{out}.pdf", facecolor=PAPER, bbox_inches=None)
    fig.savefig(f"{out}.png", facecolor=PAPER, bbox_inches=None, dpi=DPI)
    plt.close(fig)
    return out


def main():
    coffees = json.loads((DATA / "coffees.json").read_text())
    countries = load_countries()
    print(f"Loaded {len(coffees)} coffees, {len(countries)} country geometries.\n")

    for region_key in REGIONS:
        cfg = REGIONS[region_key]
        n = sum(1 for c in coffees if c["country"] in cfg["highlight"])
        print(f"Rendering {region_key} ({n} pins)...")
        out = render_region(region_key, coffees, countries)
        print(f"  → {out}.pdf  +  {out}.png")


if __name__ == "__main__":
    main()
