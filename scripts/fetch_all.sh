#!/bin/sh
# Every free source the model is built from, cached under data/raw (re-running only fetches what's missing or stale).
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=scripts
sh scripts/fetch_osm.sh
uv run python scripts/fetch_dem.py
uv run python scripts/fetch_fabdem.py
uv run python scripts/fetch_s2.py
uv run --with mapbox-vector-tile python scripts/fetch_mapillary.py   # needs MAPILLARY_TOKEN, else skipped
uv run python scripts/fetch_heights.py
uv run python scripts/fetch_gba.py
uv run python scripts/fetch_wikidata.py
sh scripts/fetch_gtfs.sh
