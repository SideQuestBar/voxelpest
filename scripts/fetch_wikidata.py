"""Places with coordinates inside the AOI from Wikidata (CC0): Hungarian and English names, what they are, height,
inception, and their Hungarian/English Wikipedia articles (for ranking labels by page views later).

Output: data/raw/wikidata.json
"""
import json
import time
from pathlib import Path

import requests

from aoi import wgs_bounds

w, s, e, n = wgs_bounds(0)
Q = f"""
SELECT ?i ?hu ?en ?kindLabel ?coord ?height ?inception ?huwiki ?enwiki WHERE {{
  SERVICE wikibase:box {{
    ?i wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point({w} {s})"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point({e} {n})"^^geo:wktLiteral .
  }}
  OPTIONAL {{ ?i rdfs:label ?hu FILTER(LANG(?hu) = "hu") }}
  OPTIONAL {{ ?i rdfs:label ?en FILTER(LANG(?en) = "en") }}
  OPTIONAL {{ ?i wdt:P31 ?kind }}
  OPTIONAL {{ ?i wdt:P2048 ?height }}
  OPTIONAL {{ ?i wdt:P571 ?inception }}
  OPTIONAL {{ ?huwiki schema:about ?i ; schema:isPartOf <https://hu.wikipedia.org/> }}
  OPTIONAL {{ ?enwiki schema:about ?i ; schema:isPartOf <https://en.wikipedia.org/> }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,hu". }}
}}"""
for attempt in range(4):
    r = requests.get("https://query.wikidata.org/sparql", params={"query": Q},
                     headers={"Accept": "application/sparql-results+json", "User-Agent": "voxelpest/0.1 (open-data city model)"},
                     timeout=300)
    if r.ok:
        break
    print("retry", r.status_code)
    time.sleep(10 * (attempt + 1))
r.raise_for_status()
items = {}
for b in r.json()["results"]["bindings"]:
    qid = b["i"]["value"].rsplit("/", 1)[1]
    it = items.setdefault(qid, {"qid": qid, "kinds": []})
    lon, lat = map(float, b["coord"]["value"].removeprefix("Point(").rstrip(")").split())
    it.update(lon=lon, lat=lat)
    for k in ("hu", "en", "height", "inception", "huwiki", "enwiki"):
        if k in b and k not in it:
            it[k] = b[k]["value"]
    if "kindLabel" in b and b["kindLabel"]["value"] not in it["kinds"]:
        it["kinds"].append(b["kindLabel"]["value"])
Path("data/raw").mkdir(parents=True, exist_ok=True)
json.dump(list(items.values()), open("data/raw/wikidata.json", "w"), ensure_ascii=False)
print(len(items), "Wikidata items in the AOI")
