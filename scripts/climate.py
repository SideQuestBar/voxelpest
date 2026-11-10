"""What Budapest's weather is like on each day of the year, so the viewer offers snow only when it can fall.
After warsaw-vibe-voxel's scripts/climate.py (MIT, © 2026 Piotr Migdał).

Open-Meteo's historical archive (ERA5 reanalysis, 1995-2024) for central Budapest, over a window of ±10 days round
each day of the year:
  clear / cloudy / rain / snow: the share of days of each kind (snow: >= 1 cm fresh; rain: >= 2 mm; cloudy: mean
         cloud >= 75%; clear: the rest), summing to 1 (for a "typical" weather per date, not used by the viewer yet)
  cover: the share of days with >= 2 cm of snow lying
  snowy: whether any snow fell (> 0.2 cm) in the window in 30 years: the viewer offers snow only then

Output: web/public/data/climate.json. `archive()` is also phenology.py's source of temperatures.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from aoi import RAW  # noqa: E402

API = "https://archive-api.open-meteo.com/v1/archive"
YEARS = (1995, 2024)
BUDAPEST = (47.4979, 19.0402)
OUT = Path(__file__).parent.parent / "web/public/data"
CACHE = Path(RAW) / "climate"
WINDOW = 10
DAILY = "weather_code,snowfall_sum,rain_sum,cloud_cover_mean,snow_depth_mean,temperature_2m_mean"


def archive(lat, lon, daily, cache=CACHE, name=None):
    """Open-Meteo's daily archive for one point, 1995-2024, cached; asked for five years at a time (a 30-year request
    can take longer than a proxy waits), waiting out its per-minute limit."""
    stem = f"{name or f'{lat:.3f}_{lon:.3f}'}_{daily.replace(',', '-')}"
    path = Path(cache) / f"{stem}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        out = {}
        for y0 in range(YEARS[0], YEARS[1] + 1, 5):
            part = Path(cache) / f"{stem}.{y0}.part"
            if not part.exists():
                url = (f"{API}?latitude={lat}&longitude={lon}&start_date={y0}-01-01&end_date={min(y0 + 4, YEARS[1])}-12-31"
                       f"&daily={daily}&timezone=GMT")
                for attempt in range(16):
                    try:
                        part.write_text(json.dumps(json.load(urllib.request.urlopen(url, timeout=60))["daily"]))
                        break
                    except OSError as e:
                        if attempt == 15:
                            raise
                        time.sleep(65 if getattr(e, "code", 0) == 429 else 5 * (attempt + 1))
                print("archive", stem, y0)
            for k, v in json.loads(part.read_text()).items():
                out.setdefault(k, []).extend(v)
        path.write_text(json.dumps(out))
        for p in Path(cache).glob(f"{stem}.*.part"):
            p.unlink()
    return json.loads(path.read_text())


def day_of_year(times):
    return np.minimum([dt.date.fromisoformat(t[:10]).timetuple().tm_yday for t in times], 365) - 1


def per_day(times, x, window=WINDOW):
    doy = day_of_year(times)
    k = np.ones(2 * window + 1)
    wrap = lambda a: np.convolve(np.r_[a[-window:], a, a[:window]], k, "valid")
    return wrap(np.bincount(doy, x, minlength=365)) / wrap(np.bincount(doy, minlength=365))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cache", default=CACHE)
    a_ = ap.parse_args()
    d = archive(*BUDAPEST, DAILY, a_.cache, "budapest")
    a = lambda k: np.array([v if v is not None else 0 for v in d[k]], float)
    sf, rain, cloud, depth = a("snowfall_sum"), a("rain_sum"), a("cloud_cover_mean"), a("snow_depth_mean")
    snow = sf >= 1
    wet = ~snow & (rain >= 2)
    grey = ~snow & ~wet & (cloud >= 75)
    kinds = {k: per_day(d["time"], v.astype(float)) for k, v in dict(clear=~(snow | wet | grey), cloudy=grey, rain=wet, snow=snow).items()}
    snowy = per_day(d["time"], (sf > 0.2).astype(float)) > 0
    r = lambda p: [round(float(x), 3) for x in p]
    out = Path(a_.out) / "climate.json"
    json.dump(dict(source=f"Open-Meteo historical weather API (ERA5), central Budapest, {YEARS[0]}-{YEARS[1]}",
                   **{k: r(v) for k, v in kinds.items()}, cover=r(per_day(d["time"], (depth >= 0.02).astype(float))),
                   snowy=[bool(x) for x in snowy]), open(out, "w"))
    none = np.nonzero(~snowy)[0] + 1
    print(f"{out}: no snow at all on days {none[0]}-{none[-1]}" if len(none) else f"{out}: snow possible all year")


if __name__ == "__main__":
    main()
