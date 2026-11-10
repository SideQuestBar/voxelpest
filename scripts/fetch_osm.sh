#!/bin/sh
# OSM for the AOI (scripts/aoi.py) + 150 m margin, as Overpass-style JSON (`nwr(bbox); out body geom(bbox);`) in
# data/raw/osm.json. Default: BBBike's weekly Budapest extract (~60 MB), cut locally by scripts/osm_pbf.py.
# GEOFABRIK=1 uses Geofabrik's daily Hungary extract instead (~350 MB, fresher); OVERPASS=1 asks the public servers.
set -e
cd "$(dirname "$0")/.."
BB=$(PYTHONPATH=scripts uv run python scripts/aoi.py)
echo "bbox $BB"
mkdir -p data/raw/osm
if [ -n "$OVERPASS" ]; then
  Q="[out:json][timeout:600][maxsize:1073741824];nwr($BB);out body geom($BB);"
  for u in https://overpass-api.de/api/interpreter https://overpass.private.coffee/api/interpreter https://overpass.kumi.systems/api/interpreter; do
    curl -s -m 900 -A "voxelpest/0.1" --data-urlencode "data=$Q" "$u" -o data/raw/osm.json.part
    if head -c 20 data/raw/osm.json.part | grep -q '{'; then mv data/raw/osm.json.part data/raw/osm.json; echo "OK $u"; exit 0; fi
    echo "fail $u"
  done
  exit 1
fi
if [ -n "$GEOFABRIK" ]; then
  P=data/raw/osm/hungary-latest.osm.pbf; URL=https://download.geofabrik.de/europe/hungary-latest.osm.pbf
else
  P=data/raw/osm/Budapest.osm.pbf; URL=https://download.bbbike.org/osm/bbbike/Budapest/Budapest.osm.pbf
fi
if [ ! -s $P ] || [ -n "$(find $P -mtime +6)" ]; then
  curl -sS -L -A "voxelpest/0.1" -o $P.part "$URL" && mv $P.part $P
fi
ls -la $P
uv run python scripts/osm_pbf.py $P $BB data/raw/osm.json
