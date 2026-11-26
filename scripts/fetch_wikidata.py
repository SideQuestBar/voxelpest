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
OUT = Path("data/raw/wikidata.json")
rows = None
for attempt in range(4):  # the query service can also time out mid-answer: a 200 whose JSON stops short
    try:
        r = requests.get("https://query.wikidata.org/sparql", params={"query": Q},
                         headers={"Accept": "application/sparql-results+json",
                                  "User-Agent": "voxelpest/0.1 (open-data city model)"}, timeout=300)
        r.raise_for_status()
        rows = r.json()["results"]["bindings"]
        break
    except (requests.RequestException, ValueError, KeyError) as e:
        print("retry:", str(e)[:120])
        time.sleep(10 * (attempt + 1))
if rows is None:
    if OUT.exists():
        print(f"Wikidata did not answer; keeping the {OUT} from before")
        raise SystemExit(0)
    raise SystemExit("Wikidata did not answer; run this again later")
items = {}
for b in rows:
    qid = b["i"]["value"].rsplit("/", 1)[1]
    it = items.setdefault(qid, {"qid": qid, "kinds": []})
    lon, lat = map(float, b["coord"]["value"].removeprefix("Point(").rstrip(")").split())
    it.update(lon=lon, lat=lat)
    for k in ("hu", "en", "height", "inception", "huwiki", "enwiki"):
        if k in b and k not in it:
            it[k] = b[k]["value"]
    if "kindLabel" in b and b["kindLabel"]["value"] not in it["kinds"]:
        it["kinds"].append(b["kindLabel"]["value"])
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(list(items.values()), open(OUT, "w"), ensure_ascii=False)
print(len(items), "Wikidata items in the AOI")
