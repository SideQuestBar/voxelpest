# Building the map

How the map is made from free data: the downloads, the build steps, and how the sources are fused into voxels. The
hand-built landmarks are in [landmarks.md](landmarks.md).

## The grid

The grid is EOV (EPSG:23700) turned 41.5° (`scripts/aoi.py`) so that Pest's main street grid lies on voxel faces.
`scripts/orient.py` measured that angle from OSM walls: 22 % of all wall length falls within 5° of a grid axis, against
10 % for a north-up grid.

## Rebuild the data

```
./bv map                   # ~650 MB of downloads on the first run (cached in data/raw), then ~28 min, fits in 7 GB RAM
```

(`./bv map` runs `scripts/build_data.sh`; a Mapillary token for the street furniture goes in
`~/.config/voxelpest/env` as `MAPILLARY_TOKEN=...`, and without one that step is skipped.)

| Step | Script | Output |
| --- | --- | --- |
| OSM | `fetch_osm.sh` → `osm_pbf.py` | `data/raw/osm.json`. Default source is BBBike's weekly Budapest extract; `GEOFABRIK=1` uses Geofabrik's daily Hungary extract, `OVERPASS=1` the Overpass API |
| Terrain (1) | `fetch_dem.py` | Copernicus DEM GLO-30 tiles from the AWS open-data bucket: a surface model, roofs and trees included |
| Terrain (2) | `fetch_fabdem.py` | FABDEM V1-2, the same DEM with buildings and forest removed: bare earth. One 1° tile read out of Bristol's 10° zip with range requests |
| Colour | `fetch_s2.py` | Sentinel-2 cloudless 2023 (EOX), web-mercator tiles at zoom 15 mosaicked into one GeoTIFF |
| Street furniture | `fetch_mapillary.py` | Objects Mapillary has located in its street photos (lights, signals, signs, benches, bins, racks, hydrants, zebras), from its vector tiles. Needs a free token in `MAPILLARY_TOKEN`; skipped without one |
| Heights (1) | `fetch_heights.py` | Átló's Budapest Open Data Atlas "Épületmagasság": OSM footprints with Urban Atlas 2012 heights → `atlo_heights.json` (OSM id → m) |
| Heights (2) | `fetch_gba.py` | GlobalBuildingAtlas GBA.Height, the 0.2° GeoTIFF read out of TUM's 107 GB zip with HTTP range requests (`rangezip.py`, ~170 MB) |
| Labels | `fetch_wikidata.py` | Wikidata items in the box (names hu/en, kind, height, inception, Wikipedia links) |
| Transit | `fetch_gtfs.sh` | BKK's static GTFS (for trams later) |
| Grid | `prep.py` | `data/prep.npz`: the DEMs, GBA and Sentinel-2 resampled onto the 1 m grid; EOV orthophotos dropped into `data/raw/ortho/` are picked up too |
| Voxels | `voxelize.py`, `landmarks.py`, `tiles.py` | `web/public/data/{meta.json, tiles/}`, plus `data/debug/{report.json, topdown.png}` |
| Snow by date | `climate.py` | `web/public/data/climate.json`: per day of the year, from Open-Meteo's ERA5 archive for Budapest (1995-2024): whether any snow fell within ten days of it in thirty years, and the shares of clear, cloudy, rainy and snowy days |
| Seasons | `phenology.py` | `web/public/data/phenology.json`: per tree class the days of leaf-out, autumn colour and leaf fall in Budapest (below), the autumn colours, the lawns by month |

`./bv bench parliament` builds only a 192 × 192 m window round that landmark into `data/debug/bench_parliament.npy`
(`./bv bench city,szell` a list, `./bv bench 1` all of them), which is quicker when you work on a landmark.
`scripts/preview.py` draws such a window as a picture, without the browser.

**Phenology.** The dates are warsaw-vibe-voxel's (its `scripts/phenology.py`): per kind of tree the median day of leaf
unfolding, autumn colouring and leaf fall, and how far trees of one kind spread round it, from the German Weather
Service's phenological network east of 12.5° E (Brandenburg, Berlin, Saxony; 1995-2024) and, where it has no series,
iNaturalist's leaf annotations; the autumn colours and the lawns' months from dated Commons photos. Budapest is
warmer, so `phenology.py` moves them by **thermal time**, from ERA5 daily mean temperatures (Open-Meteo's archive,
1995-2024) for that region (Berlin and Dresden) and for Budapest: leaf-out on the day Budapest has the same
degree-days over 5 °C since 1 January as the region on its day (the usual growing-degree-day rule), colouring and leaf
fall on the day Budapest's mean temperature falls to what the region's is then. In ERA5 Budapest's March and April are
1.9 °C warmer than that region's (8.8 against 6.9 °C) and its October 1.1 °C warmer: leaf-out comes 9-10 days earlier
(horse chestnuts round 9 April, maples 16 April, limes 27 April), colouring about 6 days and leaf fall about 5 days
later; half the city's trees are in colour by about 22 October and half bare by about 7 November. The plane tree
(Budapest's avenues; not in Warsaw's table) leafs out with the ash, colours with the lime (iNaturalist's European
annotations put them a day apart) and keeps its brown-yellow leaves ten days longer. ERA5's cell is the city's
average: the inner city's heat island makes the real spring a few days earlier still. The trees' classes per 2 m
(`foliage.bin`, which `meta.json` announces as `foliage`) come from the tree build; without it the trees stay green
and only the lawns change.

## Two grids

The heights, roofs, ground and bridges are worked out on a 1 m grid. The voxels are 0.5 m: `build()` draws one
128 × 128 m window at a time, and in it

- footprints, building parts, roads, rails, zebras and bridge decks are rasterized again at 0.5 m, so walls and kerbs
  are no longer 1 m steps;
- the ground and every roof surface are interpolated, so slopes rise in 0.5 m steps;
- plastered and stone buildings with pitched roofs get a cornice, one voxel out from the wall under the eaves;
- trees, lamps, railings and the landmarks are drawn at 0.5 m.

Each window is built once. `tiles.py` writes its four finest tiles and keeps a compressed downsampled copy for every
coarser level (1, 2, 4 and 8 m cells), from which the coarse tiles are assembled at the end.

## How the data is fused (`scripts/voxelize.py`)

| Source | Used for |
| --- | --- |
| **OpenStreetMap** | Footprints and 957 building parts (the Parliament, Basilica and Matthias Church are mapped in 3D). Also: heights, levels, roof shapes and colours, surfaces, roads, rails, trams, zebras, water, bridge outlines, piers and pylons, 6 000+ trees and tree rows, street lamps, names |
| **GlobalBuildingAtlas** (3 m) | A measured height for every footprint: the 75th percentile inside it, because GBA under-reads roofs |
| **Urban Atlas BH 2012** via Átló | A second measured height, per OSM building id |
| **FABDEM** and **Copernicus DEM GLO-30** | The ground (see below) |
| **Sentinel-2 cloudless** | Roof colours of the larger buildings; grass and trees in courtyards and on land OSM leaves blank |
| **Mapillary** | Street lights, traffic lights, signs, benches, bins, bike racks, hydrants and zebra crossings OSM doesn't map |

**Building height**, in order of trust:

1. OSM `height`.
2. OSM `building:levels` × a storey height taken from the measurements, clamped to 3.0–4.4 m (Pest's 19th-century storeys are ~4 m).
3. The mean of GBA and Urban Atlas.
4. A default for the building type.

On the current data: 9 045 come from levels, 11 495 from measurements, 372 from tags and 1 831 from defaults. Where tags
or levels disagree with GBA by more than 40 %, the building is listed in `data/debug/report.json`.

**Roofs**:

- Pitched roofs are built from a distance transform. Each roof cell rises with its distance from the nearest street or
  courtyard edge (37°) until it reaches the roof height. So a Pest perimeter block gets one continuous roof along the
  street, ridge parallel to the facade, with hips at the corners.
- `roof:shape` dome, pyramidal, mansard, flat and skillion are honoured. Flat roofs over 150 m² get a parapet.
- Buildings stand on the median ground under them, with walls reaching down the slope.

**Ground**: GLO-30 is a surface model, so over Pest it stands 5–15 m above the street, and taking the buildings back
out of it flattened Castle Hill. FABDEM is the same DEM with buildings and forest removed by a trained model, so it
keeps the hills, but it smooths them and errs by a few metres.

- The ground starts from FABDEM.
- Where the surface model sees open ground (squares, streets, parks), the difference between the two is taken as
  FABDEM's error and spread to the cells around (Gaussian-weighted, 16 and 48 m). "Open" means away from buildings and
  trees, and farther still from tall ones: the 30 m surface model blurs a 51 m stadium roof well past its walls.
- Pest is a plain, but FABDEM wanders 104–120 m under its dense blocks, so the Pest bank is smoothed at ~160 m. On
  gentle ground elsewhere it is smoothed at ~30 m, and the hills keep their shape.
- OSM's RTK survey points (52 in the box, ~5 cm accuracy) then set the level. Pest's points set the bank's level over
  ~600 m, then each point pulls its own neighbourhood (~150 m). Before this the ground was off by a median 3.6 m
  (11 m on Szent István tér, in front of the Basilica); afterwards it is within 1 m of every point.
- OSM's surveyed summits (`natural=peak` with `ele`) are put back: Gellért Hill tops out at 235 m.
- Castle Hill's squares sit at 160–171 m (Szent György tér, Dísz tér, Szentháromság tér), Pest at 106–111 m.
- The Danube is one flat surface at the DSM's median over it (98.0 m). Quays stay at least 2.5 m above it, and their
  exposed sides are granite.

**Streets**: a carriageway is as wide as OSM's lanes, parking and tram tracks say (`lanes`, `parking:*`,
`cycleway:*`, `embedded_rails`; 3.0–3.5 m lanes, 2.2 m parking strips), but never wider than the street canyon: each
12 m stretch is narrowed to stay 2 m off the buildings and clear of a mapped pavement. Lanes get dashed lines (solid
between opposing directions on four-lane roads), parking strips a darker grey, and kerbs a pale stone edge where the
pavement meets the road. After [warsaw-vibe-voxel](https://github.com/stared/warsaw-vibe-voxel):

- No lane lines cross a junction: none within the widest street's half-width plus 4 m of a node where three or more
  street segments meet (driveways don't count), nor over a junction area.
- A carriageway of paving stones is a darker granite than the pavement, so it doesn't vanish into it. A service road
  or driveway with no surface of its own takes the surface of the square it crosses.
- `area:highway` junctions, bus bays and crossings are carriageway.
- The build checks every street's centreline against the finished ground and lists the ones a square or area cuts
  (`carriageway_cut` in `data/debug/report.json`).

**Underpasses** (also after warsaw-vibe-voxel): every footway OSM maps one level under the street outside a building
is carved as a corridor 3 m high, its floor 4 m under the street (smoothed over 21 m), with pale stone walls and
ceiling. The stairs mapped between the street and that level are open stairwells, stepped from the street down to the
passage, with a parapet round them. Deeper levels (the metro's) stay solid, and the passages by the river are left to
the quay tunnels.

**Satellite colours**: each roof with at least ~30 m² of interior seen by Sentinel-2 takes its colour from the image,
mapped onto the palette's range so a 10 m pixel's haze doesn't turn every roof grey; small buildings keep the
palette's colours. Green the satellite sees in courtyards and on unmapped land becomes grass, with trees on it.

**Street furniture**: where photos are dense, Mapillary finds the same object many times over, so its detections are
thinned to the spacing such things really have (lamps 18 m apart, signs 22–30 m, bins 10 m), traffic lights are kept only
at junctions OSM marks as signalised, and everything is moved off the road and out of walls. Then drawn: lamp posts
(except where OSM has one within 15 m), traffic lights, signs (red, blue or white plates), benches, bins, bike racks
and hydrants. Zebra crossings it saw
where OSM maps none are painted across the road.

**Bridges**: the five Danube bridges in the box are built by hand ([landmarks.md](landmarks.md)). Every other mapped bridge (over railways,
roads, the Városliget lake) gets a deck that rises from its two ends, with the ways mapped on it painted on top and
railings along the edges. OSM's `bridge:support=pier` areas become piers under it, and a lamp stands every 28 m on
both kerbs. A flyover mapped as a chain of ways (the Nyugati tér flyover) is laid as one deck with one profile, rising
from both ends at most 6.5 % to clear the streets under it, on columns every 26 m.

**Raised buildings**: a building or part with `min_height` or `building:min_level` floats only if it is a bridge, a
roof, a canopy, a balcony or a gallery, or a road or railway passes under it; anything else is stood on the ground
(OSM often marks the upper part of a building this way without the part under it). Walls reach down to the ground on
the downhill side of a slope.

**Trees** (`scripts/trees.py`):

- Where they stand: mapped `natural=tree` nodes and `tree_row` lines; woods filled at ~6.5 m spacing, parks at ~11 m on
  grass only, scrub as bushes, green courtyards on a 9 m lattice; and street trees OSM doesn't map: where Sentinel-2
  sees green over a pavement and the road beside it (an avenue's crowns), a tree on the pavement 1-3 m off the
  carriageway every 9 m (about 3 600 of them: Andrássy út's outer rows, Bartók Béla út, the villa quarter's streets).
  Dense Pest streets with no crowns stay bare.
- What they are: 43 kinds in 15 classes (maple, lime, ash, robinia with Sophora and Gleditsia, oak, horse chestnut,
  beech and hornbeam, birch, rowan, larch, willow, alder, other deciduous, conifers, plane). A tree's own tags come first:
  OSM names a species for 255 of the map's 5 000 mapped trees (`species`, `genus`, `taxon`, `taxon:genus`, the Hungarian and
  English names, `species:wikipedia` / `:wikidata`) and a leaf type for 69 % (`leaf_type`, `leaf_cycle`:
  needle-leaved trees become conifers, broad-leaved ones never do). The rest are drawn, by a hash of their position,
  from a mix for where they stand (a tree row keeps one species):
  - streets: FŐKERT's typical street genera, Tilia, Acer, Fraxinus, Celtis, Robinia, Styphnolobium, Gleditsia
    ([Hudomiet, FŐKERT, 2023](https://thegreencities.eu/wp-content/uploads/2023/09/6.-Hudomiet.pdf)), with the plane
    (nearly 4 000 of them, [We Love Budapest 2024](https://welovebudapest.com/cikk/2024/08/29/budapest-platanfak-tortenete-jovoje-kornyezetvedelem-fokert/)),
    horse chestnut, ornamental pear and Koelreuteria, which the city's 26 800 street trees are mostly made of
    ([index.hu 2016](https://index.hu/belfold/budapest/2016/06/07/budapest_azt_se_tudjuk_hany_fank_van/)); a few
    Ailanthus. Street trees are smaller than in a park, their crowns no wider than their spacing and the pavement
    allow, and about one in ten is a young replacement, 5-8 m tall;
  - narrow streets (a facade within 4.5 m): small crowns, mostly globe robinias, of which FŐKERT's register holds
    2 928 ([Szabó et al. 2025](https://www.mdpi.com/2223-7747/14/2/228)), Callery pears, manna ash, Koelreuteria;
  - parks and squares: planes, chestnuts, limes, maples, ash, oak, Celtis, hornbeam, birch, poplars, a few pines,
    spruces, thujas and a cedar;
  - courtyard gardens: Ailanthus, Celtis, robinia, box elder, fruit trees, walnut, mulberry, birch, thuja;
  - the Buda hills' woods (Gellért Hill): oak, hornbeam, robinia, ash and manna ash, field maple, lime, Celtis, some
    pine and rowan, after the hill's remnant hornbeam-oak and lime-ash woods and its park trees
    ([MTVSZ, Gellért-hegy](https://mtvsz.hu/uploads/files/kiadvany-termvedgellert-hegy.pdf));
  - Margaret Island: planes (its tallest is 42 m), poplars, oaks, chestnuts, willows, a few conifers;
  - within 12-25 m of the Danube or a pond: weeping and white willows, poplars, alder.
  The tolerant street trees (Ailanthus, Celtis, Koelreuteria, robinia, Sophora) and the sensitive ones (chestnut,
  lime, Norway maple, plane) follow [Ripka & Reiderné Saly 1991](https://agris.fao.org/search/zh/records/6471e5f777fd37171a7074d3).
- How they look: heights and crowns within each species' range (smaller in streets, yards and on the hills, crowded
  in woods; mapped `height` and `diameter_crown` win); plane trees broad and tall with mottled pale trunks, limes dense
  ovals, chestnuts broad domes, Lombardy poplars and fastigiate oaks and hornbeams columns, birches narrow and airy on
  white trunks, weeping willows wide with curtains to the ground, robinia, ash and Ailanthus open and clumped, spruces,
  larches and cedars tiered cones, pines a flat crown high on a bare trunk, globe robinias a ball on a stem. A crown is a
  body and a few lobes, roughened by noise and opened by clumped gaps, in five shades of its kind's green (lighter on
  top, darker inside and underneath). The trunk (two voxels wide on big trees) runs into the crown, and a few limbs and
  forks branch inside it, in bark colours: a bare tree in winter still reads as a tree. Over a road nothing but the trunk
  comes lower than 4.5 m; a crown close to a facade leans away from it.
- `web/public/data/foliage.bin` tells the viewer's seasons which tree each 2 m cell's crown belongs to (its class and a
  byte of the tree), for leafing out, autumn colours and bare winter trees.

**Monuments**: OSM monuments that have a height but no building tag are built in stone. Tall ones with a wide
footprint become a column on a pedestal with a bronze top. Church parts are stone, without the office-window grid;
they get round-headed windows instead. Every statue, bust and sculpture OSM maps stands on a pedestal, and the best
known are drawn from their photos (`scripts/landmarks_statues.py`, [landmarks.md](landmarks.md)).

## Curated buildings

**Curated** (`scripts/overrides.json`, keyed by OSM id, each with a source note): the Buda Castle palace gets its
height, hipped copper roofs and pale stone; Anker-ház on Deák tér its height, ochre stone and two domed corner towers;
Vörösmarty n°1 its pale blue glass (from street photos beside renders from the same spots).

## Known limits

- **No LiDAR.** Roofs are shaped by rule, not measured, and so are the ground's smaller features. The 30 m DEMs
  can't show the quays' stone walls or the cut of a street. Away from the survey points the ground can still be a few
  metres off. Lechner's DFM/nDFM (~50k HUF for the core) would fix both. The
  city's 2016 survey behind the Budapest Solar Map would be better still, if it can be had.
- **Trees.** Positions in woods and parks are generated, and crowns are generic.
- **Windows** are procedural: the shader draws them on the plain OSM walls in 0.5 m steps, so they don't follow real
  facades; landmarks have their own.
- **Bridges**: the five Danube bridges are built by hand; smaller bridges over roads and railways are a generic deck
  on piers. Their ends meet a two-level embankment: the lower quays' roads and the mapped tunnels and covered ways pass
  under the bridgeheads, dug down for headroom ([landmarks.md](landmarks.md), "Bridge ends").
- **Landmarks** are built to the photos' proportions, not to plans, so their details are close rather than exact.
  The Fisherman's Bastion's tower positions are read off its OSM outline.
- **Sentinel-2 is 10 m.** It sets the tone of large roofs and parks; small roofs and street detail stay generic. An
  orthophoto (e.g. Lechner's 2023 25 cm imagery) in `data/raw/ortho/` would be the next step.
- **Licences.** GlobalBuildingAtlas is CC BY-NC 4.0, FABDEM and Sentinel-2 cloudless CC BY-NC-SA 4.0 and Mapillary
  CC BY-SA 4.0, so the generated tiles are non-commercial and share-alike. Check the terms before publishing them.
