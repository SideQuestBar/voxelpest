#!/bin/sh
# BKK's static GTFS (Budapest public transport: routes, stops, shapes, timetables), updated daily.
# For the tram and metro layers later; the real-time feed (vehicle positions) needs a free BKK API key.
set -e
cd "$(dirname "$0")/.."
mkdir -p data/raw/gtfs
P=data/raw/gtfs/budapest_gtfs.zip
if [ ! -s $P ] || [ -n "$(find $P -mtime +6)" ]; then
  curl -sS -L -A "voxelpest/0.1" -o $P.part https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip && mv $P.part $P
fi
ls -la $P
