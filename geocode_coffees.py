"""Geocode each coffee in data/coffees.json using OpenStreetMap Nominatim.

Strategy per coffee, first hit wins:
  1. Manual override (data/geocode_overrides.json keyed by filename)
  2. Nominatim "<farm>, <region>, <country>"
  3. Nominatim "<region>, <country>"
  4. Nominatim "<country>" (last resort — flagged for review)

Polite to Nominatim: 1 req/sec, real User-Agent, results cached. Idempotent —
already-geocoded entries are skipped unless --redo or --all is passed.

Adds fields to each coffee record:
  lat, lon                   (floats)
  geocode_precision          "farm" | "town" | "region" | "country" | "manual"
  geocode_query              the string we sent
  geocode_display_name       Nominatim's formatted address (for sanity check)
  geocode_source             "nominatim" | "manual"

Usage:
  .venv/bin/python geocode_coffees.py            # geocode missing entries
  .venv/bin/python geocode_coffees.py --redo IMG_0730.jpg
  .venv/bin/python geocode_coffees.py --all
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
COFFEES = DATA / "coffees.json"
OVERRIDES = DATA / "geocode_overrides.json"
CACHE = DATA / ".geocode_cache.json"

USER_AGENT = "coffee-art-project/1.0 (personal art project; carlos.vilhena@tru.id)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
RATE_LIMIT_SEC = 1.1  # be polite


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def nominatim_search(query: str, cache: dict) -> dict | None:
    """Hit Nominatim (or cache). Returns first result dict or None."""
    if query in cache:
        return cache[query]
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1, "addressdetails": 1})
    req = urllib.request.Request(f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  ! Nominatim error for {query!r}: {e}", file=sys.stderr)
        return None
    time.sleep(RATE_LIMIT_SEC)
    result = data[0] if data else None
    cache[query] = result
    save_json(CACHE, cache)  # checkpoint so a crash doesn't lose progress
    return result


def geocode_one(coffee: dict, overrides: dict, cache: dict) -> dict:
    """Return geocoding fields for a coffee, trying strategies in order."""
    fname = coffee["filename"]

    # 1. Manual override wins
    if fname in overrides:
        o = overrides[fname]
        return {
            "lat": o["lat"],
            "lon": o["lon"],
            "geocode_precision": o.get("precision", "manual"),
            "geocode_query": o.get("note", "manual override"),
            "geocode_display_name": o.get("display_name", ""),
            "geocode_source": "manual",
        }

    country = coffee.get("country", "")
    region = coffee.get("region")
    farm = coffee.get("farm")

    candidates = []
    if farm and region and country:
        candidates.append((f"{farm}, {region}, {country}", "farm"))
    if region and country:
        candidates.append((f"{region}, {country}", "town"))
    if country:
        candidates.append((country, "country"))

    for query, precision in candidates:
        result = nominatim_search(query, cache)
        if result:
            return {
                "lat": float(result["lat"]),
                "lon": float(result["lon"]),
                "geocode_precision": precision,
                "geocode_query": query,
                "geocode_display_name": result.get("display_name", ""),
                "geocode_source": "nominatim",
            }
        print(f"  · no hit for {query!r}, falling back", file=sys.stderr)

    return {
        "lat": None,
        "lon": None,
        "geocode_precision": "failed",
        "geocode_query": candidates[0][0] if candidates else "",
        "geocode_display_name": "",
        "geocode_source": "nominatim",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="re-geocode everything")
    parser.add_argument("--redo", help="re-geocode this filename")
    args = parser.parse_args()

    if not COFFEES.exists():
        print(f"ERROR: {COFFEES} not found", file=sys.stderr)
        return 2

    coffees = json.loads(COFFEES.read_text())
    overrides = load_json(OVERRIDES, {})
    cache = load_json(CACHE, {})

    if args.all:
        todo = coffees
    elif args.redo:
        todo = [c for c in coffees if c["filename"] == args.redo]
        if not todo:
            print(f"ERROR: {args.redo} not in dataset", file=sys.stderr)
            return 2
    else:
        todo = [c for c in coffees if c.get("lat") is None or "lat" not in c]

    print(f"{len(coffees)} coffees, {len(overrides)} manual overrides, {len(todo)} to geocode")

    for i, coffee in enumerate(todo, 1):
        print(f"[{i:>2}/{len(todo)}] {coffee['filename']}: {coffee.get('farm') or coffee.get('region')}, {coffee['country']}")
        geo = geocode_one(coffee, overrides, cache)
        coffee.update(geo)
        if geo["lat"] is None:
            print(f"  ✗ FAILED")
        else:
            tag = f"({geo['geocode_precision']})"
            short = geo["geocode_display_name"][:80]
            print(f"  ✓ {geo['lat']:.4f}, {geo['lon']:.4f}  {tag}  {short}")
        # Save after each success
        save_json(COFFEES, coffees)

    failures = [c for c in coffees if c.get("lat") is None]
    print(f"\nDone. {len(coffees) - len(failures)} geocoded, {len(failures)} failed.")
    if failures:
        print("Failed entries (add to data/geocode_overrides.json):")
        for c in failures:
            print(f"  {c['filename']}: {c.get('farm')}, {c.get('region')}, {c['country']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
