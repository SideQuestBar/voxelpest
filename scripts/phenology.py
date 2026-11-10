"""When each kind of tree leafs out, colours and drops its leaves in Budapest, for the viewer's seasons
(FOLIAGE-CONTRACT: classes 1-15, web/public/data/phenology.json).

The table is warsaw-vibe-voxel's (MIT, © 2026 Piotr Migdał; its scripts/phenology.py): per class the median day of
leaf unfolding, autumn colouring (half the leaves coloured) and leaf fall (half fallen), with the spread between trees,
from the German Weather Service's phenological network (stations east of 12.5° E: Brandenburg, Berlin, Saxony,
1995-2024) and, where the DWD has no series, iNaturalist leaf annotations; autumn colours measured on Commons photos.
Budapest is warmer than that region, so its dates move:

- leaf-out by thermal time: the growing degree-days (base 5 °C, summed from 1 January) that the DWD region has on a
  class's day are reached earlier in Budapest; that day is Budapest's. Degree-days per year from ERA5 daily mean
  temperatures (Open-Meteo's archive, 1995-2024), averaged per day of the year;
- colouring and leaf fall by the same rule on the way down: the day Budapest's mean temperature (the 30-year mean per
  day, smoothed over a month) falls to what the DWD region has on the class's day.
The DWD region is the mean of two ERA5 points, Berlin and Dresden (the network's north and south there); the
spread between trees stays Warsaw's. ERA5's cell is the city's average: the inner city's heat island would make the
real dates a few days earlier still in spring.

Class 15, the plane tree (Platanus × hispanica, common on Budapest's avenues; Warsaw has none): leafs out with the ash
(the latest in the DWD's series), colours with the lime (iNaturalist's European leaf annotations put the two within a
day: coloured outnumber green on day 308 and 307), and holds its brown-yellow leaves 10 days longer than the usual gap.
Class 13 (other deciduous: Celtis, Ulmus, Populus, Prunus, ...) is Warsaw's median of the classes.

Lawns: Warsaw's monthly tint (dated Commons photos of Warsaw lawns), divided by its June-August mean so that
Budapest's summer grass keeps the palette's colour (matched to Budapest street photos), and moved by the same shifts
(the spring months by the leaf-out shift, the autumn months by the colouring shift). Summer leaves: no tint ([1, 1, 1]),
the palette's greens are Budapest's already.
`city`: the day by which half of the map's deciduous crown cells (foliage.bin, when the build has written it; else
every class alike) have reached a phase.

  uv run python scripts/phenology.py      # -> web/public/data/phenology.json (downloads cached in data/raw/climate)
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from climate import BUDAPEST, CACHE, DAILY, OUT, archive, day_of_year  # noqa: E402

PHASES = ("leaf", "colour", "fall")
# warsaw-vibe-voxel's web/public/data/phenology.json (Oct 2026): (leaf, colour, fall) as (day of year, sd between trees)
# at the DWD region's dates, and the autumn colour
WARSAW = {
    1: ("maple (Acer)", ((115.2, 8.1), (279.9, 11.7), (296.9, 11.3)), "#eab34f"),
    2: ("lime (Tilia)", ((127.4, 8.1), (301.9, 11.7), (318.9, 11.3)), "#d0a851"),
    3: ("ash (Fraxinus)", ((124.0, 8.9), (288.8, 11.7), (305.8, 11.3)), "#b8b76b"),
    4: ("robinia (Robinia, Styphnolobium, Gleditsia)", ((113.8, 8.1), (288.8, 11.7), (305.8, 11.3)), "#c7b272"),
    5: ("oak (Quercus)", ((120.0, 8.0), (292.0, 11.1), (309.0, 11.3)), "#b28d5e"),
    6: ("horse chestnut (Aesculus)", ((108.0, 7.6), (275.0, 11.7), (293.0, 10.7)), "#bc9156"),
    7: ("beech and hornbeam (Fagus, Carpinus)", ((115.0, 8.1), (286.0, 11.9), (303.0, 10.7)), "#cdac59"),
    8: ("birch (Betula)", ((107.0, 7.1), (283.0, 11.8), (301.0, 11.3)), "#d6b372"),
    9: ("rowan (Sorbus)", ((108.0, 8.0), (263.2, 11.7), (291.0, 11.5)), "#c28855"),
    10: ("larch (Larix)", ((102.0, 8.9), (299.0, 11.6), (316.0, 11.6)), "#e1b670"),
    11: ("willow (Salix)", ((112.5, 8.1), (329.9, 11.7), (346.9, 11.3)), "#a49764"),
    12: ("alder (Alnus)", ((109.0, 10.0), (288.8, 11.7), (305.8, 11.3)), "#849363"),
    13: ("other deciduous (median of the classes)", ((113.8, 8.1), (288.8, 11.7), (305.8, 11.3)), "#c7ac5e"),
    14: ("evergreen conifers", None, None),
}
PLANE = 15
# Warsaw's lawns by month, a factor on the grass green in linear RGB
LAWNS = [[1.33, 0.582, 1.291], [1.607, 0.706, 1.476], [1.578, 0.792, 1.529], [1.22, 0.766, 1.046], [1.137, 0.741, 0.822],
         [1.48, 0.906, 1.332], [1.496, 0.981, 1.586], [1.319, 0.883, 1.315], [1.333, 0.839, 1.277], [1.223, 0.747, 1.238],
         [1.072, 0.597, 1.254], [1.092, 0.52, 1.28]]
DWD_REGION = {"berlin": (52.52, 13.40), "dresden": (51.05, 13.74)}


def climatology(daily):
    """per day of the year (365): the mean temperature, smoothed over a month, and the mean degree-days since 1 January"""
    t = np.array([v if v is not None else np.nan for v in daily["temperature_2m_mean"]], float)
    doy, years = day_of_year(daily["time"]), np.array([int(s[:4]) for s in daily["time"]])
    mean = np.array([np.nanmean(t[doy == d]) for d in range(365)])
    k = np.ones(31) / 31
    smooth = np.convolve(np.r_[mean[-15:], mean, mean[:15]], k, "valid")
    gdd = np.zeros(365)
    ys = np.unique(years)
    for y in ys:
        m = years == y
        a = np.zeros(365)
        np.add.at(a, doy[m], np.nan_to_num(np.maximum(t[m] - 5, 0)))
        gdd += np.cumsum(a)
    return smooth, gdd / len(ys)


def shifts(cache):
    ref = [climatology(archive(lat, lon, "temperature_2m_mean", cache, name)) for name, (lat, lon) in DWD_REGION.items()]
    t_ref, g_ref = np.mean([r[0] for r in ref], axis=0), np.mean([r[1] for r in ref], axis=0)
    t_bud, g_bud = climatology(archive(*BUDAPEST, DAILY, cache, "budapest"))  # climate.py's download
    days = np.arange(1, 366, dtype=float)
    peak_r, peak_b = int(np.argmax(t_ref)), int(np.argmax(t_bud))

    def spring(day):
        return float(np.interp(np.interp(day, days, g_ref), g_bud, days))

    def autumn(day):
        temp = np.interp(day, days, t_ref)
        down = t_bud[peak_b:]  # falling from the summer's peak
        i = int(np.argmax(down <= temp))
        return float(peak_b + i + (down[i - 1] - temp) / (down[i - 1] - down[i])) if i > 0 else day

    print(f"mean temperature, DWD region / Budapest: spring (Mar-Apr) {t_ref[59:120].mean():.1f} / {t_bud[59:120].mean():.1f} °C, "
          f"autumn (Oct) {t_ref[273:304].mean():.1f} / {t_bud[273:304].mean():.1f} °C (peaks on days {peak_r + 1}, {peak_b + 1})")
    return spring, autumn


def class_counts(path):
    if not path or not Path(path).exists():
        return None
    a = np.frombuffer(gzip.decompress(Path(path).read_bytes()), np.uint8)
    return np.bincount(a[: len(a) // 2], minlength=16)


def city_median(classes, counts, ph):
    days = [(c[ph]["day"], counts[int(k)] if counts is not None else 1) for k, c in classes.items() if c[ph]]
    d, w = np.array(days, float).T
    o = np.argsort(d)
    return round(float(d[o][np.searchsorted(np.cumsum(w[o]), w.sum() / 2)]))


def lawns(spring_shift, autumn_shift):
    lawn = np.array(LAWNS) / np.mean(LAWNS[5:8], axis=0)
    mid = (np.arange(12) + 0.5) * 365 / 12
    # Budapest on a day looks like the photos' lawns some days later in spring, some days earlier in autumn
    at = mid + np.where(mid < 200, -spring_shift, -autumn_shift)
    ext = np.r_[lawn[-1:], lawn, lawn[:1]]
    xs = np.r_[mid[-1] - 365, mid, mid[0] + 365]
    return [[round(float(np.interp(d % 365, xs, ext[:, c])), 3) for c in range(3)] for d in at]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--foliage", default=None, help="foliage.bin for the city medians (default: OUT/foliage.bin)")
    a = ap.parse_args()
    spring, autumn = shifts(a.cache)
    classes = {}
    for k, (name, dates, colour) in WARSAW.items():
        if dates is None:
            classes[str(k)] = dict(species=name, leaf=None, colour=None, fall=None, autumn=None)
            continue
        move = (spring, autumn, autumn)
        classes[str(k)] = dict(species=name, autumn=colour, **{ph: dict(day=round(move[i](d), 1), sd=sd, warsaw=d)
                                                               for i, (ph, (d, sd)) in enumerate(zip(PHASES, dates))})
    ash, lime, med = WARSAW[3][1], WARSAW[2][1], WARSAW[13][1]
    gap = med[2][0] - med[1][0]
    plane = (ash[0], lime[1], (lime[1][0] + gap + 10, med[2][1]))
    classes[str(PLANE)] = dict(species="plane tree (Platanus)", autumn="#b8975a",
                               **{ph: dict(day=round((spring if i == 0 else autumn)(d), 1), sd=sd, warsaw=d)
                                  for i, (ph, (d, sd)) in enumerate(zip(PHASES, plane))})
    ds = {ph: np.median([c[ph]["day"] - c[ph]["warsaw"] for c in classes.values() if c[ph]]) for ph in PHASES}
    print("median shift, days:", {k: round(float(v), 1) for k, v in ds.items()})
    counts = class_counts(a.foliage or Path(a.out) / "foliage.bin")
    city = {ph: city_median(classes, counts, ph) for ph in PHASES}
    out = Path(a.out) / "phenology.json"
    json.dump(dict(
        city=city,
        sources=["warsaw-vibe-voxel's phenology (MIT, © 2026 Piotr Migdał): DWD phenological network east of 12.5° E 1995-2024, "
                 "iNaturalist leaf annotations, autumn colours and lawns from Wikimedia Commons photos",
                 "moved to Budapest by thermal time: ERA5 daily mean temperatures 1995-2024 (Open-Meteo archive), "
                 "degree-days over 5 °C for leaf-out, the same mean temperature in autumn",
                 "plane tree: leaf-out as ash, colouring as lime (iNaturalist, Europe), leaves held 10 days longer"],
        shift={ph: round(float(v), 1) for ph, v in ds.items()},
        classes=classes, grass=lawns(ds["leaf"], ds["colour"]), leaf=[1.0, 1.0, 1.0],
    ), open(out, "w"), indent=1, ensure_ascii=False)
    for k, c in classes.items():
        print(k, c["species"], {ph: round(c[ph]["day"]) for ph in PHASES if c[ph]})
    print(out, "city:", city, "(weighted by foliage.bin)" if counts is not None else "(classes alike)")


if __name__ == "__main__":
    main()
