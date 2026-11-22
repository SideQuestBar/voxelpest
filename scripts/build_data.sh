#!/bin/sh
# Full data pipeline: download (cached in data/raw) -> resample onto the grid -> voxelize (+ the seasons) -> web/public/data
# ~700 MB of downloads on the first run; then ~40 min (peak ~8 GB of RAM: give it swap) for the 5.9 x 6.5 km map at 0.5 m.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=scripts
sh scripts/fetch_all.sh
uv run python scripts/prep.py
uv run python scripts/voxelize.py
# the seasons (small downloads, cached in data/raw/climate): snow by date, the trees and lawns through the year
uv run python scripts/climate.py
uv run python scripts/phenology.py
