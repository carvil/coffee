"""Extract structured data from Senzu coffee card photos.

Reads images from cards/, sends each to Claude with a JSON schema, and writes
data/coffees.json and data/coffees.csv. Idempotent — re-running only processes
new cards (keyed by filename).

Usage:
    .venv/bin/python extract_cards.py            # process new cards
    .venv/bin/python extract_cards.py --redo F   # reprocess one filename
    .venv/bin/python extract_cards.py --all      # reprocess everything
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

ROOT = Path(__file__).parent
CARDS_DIR = ROOT / "cards"
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "coffees.json"
CSV_PATH = DATA_DIR / "coffees.csv"

MODEL = "claude-opus-4-7"
MAX_LONG_EDGE = 1568  # plenty for text + graphic detail; keeps payload small

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "country": {"type": "string", "description": "Country of origin (e.g. 'Kenya', 'Guatemala'). Use English even if card is in Portuguese."},
        "region": {"type": ["string", "null"], "description": "Region or town within country (e.g. 'Nyeri', 'Tarrazú', 'Huila'). Null if not stated."},
        "farm": {"type": ["string", "null"], "description": "Farm or washing station name (e.g. 'Finca Monte Alto', 'Santa Rita'). Null if not stated."},
        "producer": {"type": ["string", "null"], "description": "Producer or family name (e.g. 'Gerardo Arias', 'Família Cerquera'). Null if not stated."},
        "variety": {"type": "string", "description": "Coffee variety/varieties as printed (e.g. 'Caturra', 'Ruiru 11, SL 28, and SL 34')."},
        "tasting_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tasting notes as a list. Use English even if card is Portuguese (e.g. 'Caramelo claro' -> 'Light caramel'). Preserve order from the card.",
        },
        "altitude_min_m": {"type": ["integer", "null"], "description": "Lower bound of altitude in meters."},
        "altitude_max_m": {"type": ["integer", "null"], "description": "Upper bound of altitude in meters. If a single number, set both min and max to that value."},
        "process": {"type": "string", "description": "Process method (e.g. 'Washed', 'Natural', 'Washed Fermented'). English."},
        "blurb": {"type": "string", "description": "The full descriptive paragraph from the card, transcribed verbatim. Translate to English if originally Portuguese."},
        "card_color_hex": {"type": "string", "description": "Hex code of the dominant color block on the left side of the card (e.g. '#B5734F' for terracotta, '#9C1B27' for crimson). 6-digit hex including the '#'."},
        "stamp_motif": {"type": "string", "description": "Short description of the white stamp silhouette on the colored panel (e.g. 'cookie with chocolate chips', 'cherry pair', 'puzzle pieces', 'wrapped candy')."},
        "language": {"type": "string", "enum": ["en", "pt"], "description": "Language the card was printed in."},
    },
    "required": [
        "country", "region", "farm", "producer", "variety", "tasting_notes",
        "altitude_min_m", "altitude_max_m", "process", "blurb",
        "card_color_hex", "stamp_motif", "language",
    ],
}

PROMPT = """This is a coffee card from Senzu Coffee Roasters in Porto. Extract the printed information into the schema.

Notes:
- The card has a colored panel on the left (with a country name, a white stamp-style silhouette, and the SENZU logo) and a metadata panel on the right (origin/farm, variety, tasting notes, altitude, process, a descriptive paragraph, and a QR code).
- Some cards are in Portuguese ("VARIEDADE", "PROCESSO", "A TUA RECEITA"). Translate field values to English, but record the original language in `language`.
- For `card_color_hex`, look at the saturated background of the left panel (not the white stamp). Estimate a reasonable hex.
- Be precise with the blurb — transcribe the full paragraph, translating only if Portuguese."""


def load_existing() -> dict[str, dict]:
    if not JSON_PATH.exists():
        return {}
    with JSON_PATH.open() as f:
        return {row["filename"]: row for row in json.load(f)}


def prepare_image(path: Path) -> str:
    """Return a base64-encoded JPEG of the card, downscaled to MAX_LONG_EDGE."""
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    long_edge = max(img.size)
    if long_edge > MAX_LONG_EDGE:
        scale = MAX_LONG_EDGE / long_edge
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.standard_b64encode(buf.getvalue()).decode()


def extract_one(client: anthropic.Anthropic, path: Path) -> dict:
    image_b64 = prepare_image(path)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["filename"] = path.name
    return data


def write_outputs(rows: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    rows = sorted(rows, key=lambda r: r["filename"])
    with JSON_PATH.open("w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    fieldnames = [
        "filename", "country", "region", "farm", "producer", "variety",
        "tasting_notes", "altitude_min_m", "altitude_max_m", "process",
        "card_color_hex", "stamp_motif", "language", "blurb",
    ]
    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = {**row, "tasting_notes": ", ".join(row.get("tasting_notes") or [])}
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="reprocess everything")
    parser.add_argument("--redo", help="reprocess this single filename")
    parser.add_argument("--workers", type=int, default=4, help="parallel workers")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        print("Set it with: export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        return 2

    if not CARDS_DIR.exists():
        print(f"ERROR: {CARDS_DIR} not found", file=sys.stderr)
        return 2

    existing = load_existing()
    all_paths = sorted(p for p in CARDS_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".heic"})

    if args.all:
        existing = {}
        todo = all_paths
    elif args.redo:
        existing.pop(args.redo, None)
        todo = [p for p in all_paths if p.name == args.redo]
        if not todo:
            print(f"ERROR: {args.redo} not found in {CARDS_DIR}", file=sys.stderr)
            return 2
    else:
        todo = [p for p in all_paths if p.name not in existing]

    print(f"Found {len(all_paths)} cards. {len(existing)} already extracted, {len(todo)} to process.")
    if not todo:
        print("Nothing to do. Pass --all to reprocess.")
        return 0

    client = anthropic.Anthropic()
    rows = list(existing.values())
    failures: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(extract_one, client, p): p for p in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            path = futures[fut]
            try:
                data = fut.result()
                rows.append(data)
                print(f"[{i:>2}/{len(todo)}] {path.name}: {data.get('country')} / {data.get('farm') or data.get('region') or '?'}")
                # Save after each success so a crash doesn't lose progress
                write_outputs(rows)
            except Exception as e:
                failures.append((path.name, str(e)))
                print(f"[{i:>2}/{len(todo)}] {path.name}: FAILED — {e}", file=sys.stderr)

    print(f"\nDone. {len(rows)} cards in dataset.")
    if failures:
        print(f"\n{len(failures)} failures:")
        for name, err in failures:
            print(f"  {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
