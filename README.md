# coffee

A personal art project: turning a [Senzu Coffee Roasters](https://www.senzucoffee.com/)
subscription into a wall set of pieces — maps, posters, hand-carved stamps,
typography. The repo holds the dataset, the generators, and the print-ready
outputs.

Each Senzu shipment includes a card with the coffee's origin, farm,
producer, variety, tasting notes, altitude, process, and a short blurb.
After 37 cards I had enough material to make something with — the
generators in this repo turn those cards into structured data first, then
into art.

## Pieces

| # | Piece | Format | Generator | Output |
|---|---|---|---|---|
| 1 | **Three regional maps** — A3 triptych: East Africa, Central America, South America. Country outlines + finca pins + fine-print callouts in the Senzu colour palette. | A3 × 3, PDF | `make_maps.py` | `output/maps/` |
| 2 | **Espresso micrography** — top-down view of an espresso cup on a saucer, with offset shadow + spoon. The shadow, cup interior, and crema disc are filled with all 37 coffees written line-by-line. | A3, PNG | `make_micrography.py` | `output/micrography/` |
| 3 | **Tasting-notes word cloud** — every flavour from the dataset packed into a coffee-bean silhouette, sized by frequency, layered against a backdrop of countries / varieties / processes. | A3, PNG | `make_wordcloud.py` | `output/wordcloud/` |
| 4 | **Stamp library** — eight linocut designs (bean, cherry, leaf, V60, blossom, hourglass, espresso cup, gooseneck kettle) ordered easiest-to-hardest, with a contact sheet and a materials guide. | SVG + PNG, A4 contact | `make_stamps.py` | `output/stamps/` |
| 5 | Cards-as-collage cutout guide | TODO | — | — |

## Dataset

`data/coffees.json` — 37 entries, one per Senzu card I've received. Built
in two passes:

1. **Vision extraction** (`extract_cards.py`): photograph each card →
   convert HEIC → send to Claude with a JSON schema → save the structured
   row. Captures origin, farm, producer, variety, tasting notes, altitude,
   process, blurb, card colour, stamp motif, and language.
2. **Geocoding** (`geocode_coffees.py`): adds `lat`/`lon`/`geocode_precision`
   to each row. Nominatim (OpenStreetMap) does the heavy lifting; manual
   overrides in `data/geocode_overrides.json` cover the cases where it
   misfired (wrong-country matches, washing stations not in OSM, etc.).

`data/coffees.csv` is the same dataset flattened for spreadsheets.
`data/ne_50m_admin_0_countries.geojson` is the country outline data
(public domain, Natural Earth) used by `make_maps.py`.

## Running

```bash
# Setup (once)
python3 -m venv .venv
.venv/bin/pip install anthropic pillow pillow-heif matplotlib wordcloud

# Build / refresh the dataset
.venv/bin/python extract_cards.py     # only when new cards arrive (needs ANTHROPIC_API_KEY)
.venv/bin/python geocode_coffees.py   # idempotent; only fills missing rows

# Generate the art
.venv/bin/python make_maps.py
.venv/bin/python make_micrography.py
.venv/bin/python make_wordcloud.py
.venv/bin/python make_stamps.py
```

## Layout

```
.
├── data/
│   ├── coffees.json            # the dataset
│   ├── coffees.csv             # flattened
│   ├── geocode_overrides.json  # manual lat/lon corrections
│   └── ne_50m_admin_0_countries.geojson
├── cards/                      # gitignored — the original card photos
├── output/
│   ├── maps/                   # gitignored
│   ├── micrography/            # gitignored
│   ├── wordcloud/              # gitignored
│   └── stamps/                 # committed — these are deliverables
├── extract_cards.py            # photos → structured data (Claude vision)
├── geocode_coffees.py          # add coordinates to each coffee
├── make_maps.py
├── make_micrography.py
├── make_wordcloud.py
├── make_stamps.py
└── README.md
```

Output folders are gitignored except `output/stamps/`, which contains the
linocut design templates — those are intended deliverables you'd actually
print and carve, so they're under version control.

## Senzu palette

Each piece pulls from a small palette extracted from the cards themselves:

| | Hex | From card |
|---|---|---|
| Deep wine | `#82213A` | El Panal (Guatemala) |
| Terracotta | `#B5734F` | Quénia / Nyeri |
| Forest olive | `#4F7A2C` | Mengeche Derso (Ethiopia) |
| Dark espresso | `#261612` | composite |
| Crema gold | `#C28840` | composite |
| Paper | `#FAFAF7` | warm off-white |

The maps assign one colour per region. The micrography pairs espresso +
crema for two-tone fill. The word cloud uses black / wine / terracotta
for the three frequency tiers, plus a muted tan for the context backdrop.
