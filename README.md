# Budapest in voxels

A 5.4 × 5.0 km diorama of central Budapest in 0.5 m voxels, built only from free data. Thirty-nine landmarks are built by
hand from reference photos and measured dimensions ([docs/landmarks.md](docs/landmarks.md)). You can fly over it, walk
its streets or drive a taxi through it, live in Budapest's own date, time and weather or on any day of the year at any
hour (the trees leaf out, turn and drop their leaves with the seasons), clear, cloudy, in rain or snow, in English or
Hungarian. It is made by [SideQuest Bar](https://side-quest.bar), and it runs as a Minecraft
server too: the viewer and the server are two separate deployments built from the same map.

The project was inspired by Piotr Migdał's [warsaw-vibe-voxel](https://github.com/stared/warsaw-vibe-voxel): it uses
that project's tile format, and parts of its data scripts (credits below). The viewer is this project's own.

The map covers:

- Margaret Bridge and the southern tip of Margaret Island, Nyugati and the Parliament at the top
- Széll Kálmán tér, Castle Hill (the Palace, Matthias Church, Fisherman's Bastion) and Gellért Hill with the Liberty
  Statue and the Gellért Baths
- the Chain, Elisabeth, Liberty and Petőfi bridges, and the boats moored along the quays
- Lipótváros and the Belváros, Terézváros, Erzsébetváros and Józsefváros down to Bálna and the Technical University
- east to Keleti, Heroes' Square, the whole Városliget, and the Puskás Aréna

The grid is EOV (EPSG:23700) turned 41.5° (`scripts/aoi.py`) so that Pest's main street grid lies on voxel faces.
`scripts/orient.py` measured that angle from OSM walls: 22 % of all wall length falls within 5° of a grid axis, against
10 % for a north-up grid.

## Quick start

Everything goes through `./bv` (`./bv help` lists it all). It needs [uv](https://docs.astral.sh/uv/), Node 22+ with
[Bun](https://bun.sh) for the packages and scripts, and for the Minecraft server Docker or podman (to run it) and JDK 25 with Maven (to rebuild
its plugin; Arch/CachyOS: `sudo pacman -S jdk25-openjdk maven`). The desktop app needs nothing more: Bun fetches
Electron.

```
./bv setup               # checks the tools, installs the dependencies, unpacks the shipped map
./bv web                 # the viewer at http://localhost:5173
./bv server              # the Minecraft server on this machine (asks once about the Minecraft EULA)
```

After changing the map:

```
./bv voxelize            # rebuild the map from the cached sources (~25 min; ./bv map downloads them first)
./bv pack                # pack it into the shipped 19 MB parts, for git
./bv minecraft           # rebuild the Minecraft world from it (~5 min); ./bv server picks it up and restarts
./bv publish-web         # publish the viewer to Cloudflare Pages (~/.config/voxelpest/web.env)
./bv publish-minecraft   # publish the Minecraft server   (~/.config/voxelpest/minecraft.env)
./bv desktop             # the viewer as a Linux desktop app: build/voxelpest-VERSION-x86_64.AppImage
```

The prebuilt tiles come as 19 MB parts (`web/public/voxelpest-data.tar.gz.part-*`), which `./bv unpack` unpacks to
`web/public/data/`.

## The viewer (`web/`)

Three ways to see the city, switched at the top right (or with the keys 1, 2, 3):

| Mode | Controls |
| --- | --- |
| **Map** | drag to turn, right-drag (or Shift-drag) to move, scroll to zoom; W A S D or the arrows fly along the ground, Q / E down and up, Shift faster. Click a name to fly there. On a touch screen: one finger moves the map (a flick glides on), pinch zooms, twisting two fingers turns it, two fingers moving up or down tilt it; double-tap zooms in, a two-finger tap out |
| **Walk** | click the map to look round with the mouse (Esc lets go); W A S D walk, Shift runs, Space jumps. Kerbs and stairs are climbed, walls stop you, the Danube makes you swim |
| **Drive** | five vehicles, picked under the switches (or V, Shift+V back): a Budapest taxi, a Trabant 601, a Rendőrség (police) Škoda Octavia, a MOL Bubi bike and a BKK bus. W / S or ↑ / ↓ for gas, brake and reverse, A / D or ← / → to steer, Space to brake, Shift for more speed, R to get back on the road, L the police car's blue lights; drag the view to swing the camera round the vehicle (all the way round, and up or down), and after a moment without that it eases back behind. It follows the ground, takes kerbs, bounces off walls and drops off quay edges |

On phones, walking has a stick on the left and a look pad on the right (double-tap to jump); driving has the stick to
steer and two pedals, and a drag anywhere else on the screen swings the camera round. The viewer fills the whole screen (under the notch and the home bar, with every control kept
clear of them, in portrait and landscape); added to the home screen it opens as a full-screen app. Elsewhere the
button at the right end of the bottom bar makes the page full screen (where the browser can: iPhone Safari can't, and
there the home-screen app is the way).

While the map loads, a small voxel Budapest (Buda Castle, the Chain Bridge, the Parliament) builds itself block by
block as the tiles arrive. The first time the map opens, a short animated guide shows how to move round, for the
device in hand (touch, mouse and keys, or a controller); the **?** button in the bottom bar shows it again. Tiles
still loading show as a "loading N tiles" chip at the bottom in the middle, with a thin progress line, and a tile that
gives way to a finer (or coarser) one dissolves into it rather than popping.

**Controllers** (Xbox, PlayStation, Switch Pro: any the browser reports in the standard layout) work in every mode:
on the map the left stick moves, the right stick turns, the triggers zoom and the bumpers go down and up; walking,
the left stick walks (click it to run), the right stick looks, A jumps; driving, RT is the gas, LT brake and reverse,
the left stick steers, the right stick swings the camera round, A the handbrake, B more speed, Y back on the road, RB / LB the next or previous vehicle, X the
blue lights. View switches the mode. Menu opens a menu made for the controller (D-pad or left stick to move, A to
choose, B to go back): the places, the date, the time of day and the weather (◀ ▶ step the date, the hour and the weather, A turns Live
on or off), SideQuest Bar, the help box and full screen. Mouse, touch and keys work in it too.

Walking and driving start on the street nearest to what the map is looking at (from far out, in front of SideQuest
Bar); switching between them keeps you where you are. Choosing a place while walking or driving takes you to the nearest street in front of it (the
Parliament and Kossuth tér: the square by the flag, facing the Parliament); a start is always on the street network,
never in a building, on a roof, in the river or in a closed inner courtyard.

On phones the round button over **Places** shows where you are: only when pressed, it asks the browser for your
position (which stays on the phone), and if you're on the map puts a blue dot there with the accuracy round it and
flies over; tap the dot to walk from the nearest street. Outside the map it says so.

**The vehicles** are built in code to their real sizes, from boxes, cylinders and extruded side outlines (a few draw
calls each: one mesh per material, the wheels instanced, the lettering on one small canvas), and each drives in its
own way:

| Vehicle | Look | Handling |
| --- | --- | --- |
| Taxi | yellow, the check along the doors, the TAXI sign lit at night; a faint breath from the tailpipe pulling away or on a cold day | quick, 90 km/h (137 with Shift) |
| Trabant 601 | 3.56 × 1.50 m, pale blue with a white roof, round headlamps, slatted grille, chrome bumpers, thin wheels; the two-stroke's blue-grey smoke, puffing at idle and pouring out under throttle | slow to get going, 94 km/h |
| Rendőrség | the current Škoda Octavia livery: white, blue door panels and bonnet band with RENDŐRSÉG, the yellow-green check; a blue and red light bar that flashes (L, X, or the button beside the picker; off at first, no siren); like the taxi, a faint exhaust | the quickest, 108 km/h (162) |
| Bubi | the lime 2021 MOL Bubi: step-through frame, front carrier with its plate, the rear panel; a rider whose legs follow the pedals | 21 km/h pedalled (30 sprinting), tight turns, leans into them; the camera close behind |
| BKK bus | a blue 12 m Mercedes Citaro C2: three double doors on the right, black window band, route 7 on its LED displays (to Újpalota, Nyírpalota út, front and side), the mirrors on stalks; no exhaust smoke | 54 km/h, wide turns; the camera well back |

Switching keeps the place and the heading (the bigger ones go back on the road if they don't fit where you were).
The choice is kept for the next visit.

The speedometer is true: a vehicle covers exactly what it shows (90 km/h is 25 m every second, in a city of real
metres). Speed shows as driving games show it: the view widens as you speed up, the camera comes lower and closer,
hangs back a little as you pull away and closes in as you brake, and shakes slightly near the top speed; faint
streaks of air flow past the edges of the screen above about 45 km/h, and the wheels blur rather than seem to stand
still or turn backwards. The exhaust is a few hundred soft puffs at most (fewer on phones) in one draw call, lit by the
sky, the city's glow at night and the tail lamps.

The bottom bar holds the clock: its button (the weather's icon, the date when it isn't today, and the time) opens a
card with the **date** and the **time of day**: the sun's real position over Budapest on that day (shadows, golden
hour, the long winter shadows and the high summer sun, lit windows and street lamps at night, stars; the hour slider's
strip shows that day's daylight), and the **seasons**. The date slider runs over the year (month initials; its thumb
has a leaf in the colour of the city's trees that day, a bare twig in winter, over a strip of the trees through the
year): each kind of tree (maple, lime, ash, robinia, oak, horse chestnut, beech, birch, rowan, larch, willow, alder,
plane, other broadleaves, conifers) leafs out light green in spring on its own dates, a little apart tree by tree,
is full green in summer, turns its own autumn colour, drops its leaves onto the lawns and pavements under it (they
fade away by December) and stands bare, its branches showing, in winter; conifers stay green, and the lawns change
colour month by month. Then the weather: **Clear**, **Cloudy** (a grey cloud deck, soft light, faint shadows),
**Rain** (streaks falling round you, a darker sky, wet streets and roofs with puddles that shine under the lamps at
night) and **Snow** (snowfall round you, and the city slowly turning white), offered only around dates it has snowed
on in Budapest (mid-October to early May). By default it is **Live**: the date and the clock follow Budapest's
(Europe/Budapest) and the weather Budapest's current weather from [Open-Meteo](https://open-meteo.com) (refreshed
every 12 minutes; only the city's fixed coordinates are sent; offline, the sky stays clear). Moving a slider or
picking a weather stops it, the Live switch in the card's corner brings it back. The sliders take a drag or a tap, and
the arrow keys (the date: a day, Shift a week, Page Up / Down a month; the hour: 15 minutes, Shift or Page Up / Down an
hour).
Beside it the **Names** toggle (the place names over the map), the guide, About and full screen. **Places** (bottom right) lists every view; its first entry takes
you to SideQuest Bar: the map flies to it, the walker stands at its door, the vehicle stops in front. The language
follows the browser (Hungarian if any of its languages is Hungarian), and the EN / HU switch keeps the choice.

The URL takes `view` (overview, parliament, kossuth, castle, chainbridge, chainarch, basilica, gellert, heroes, fishermans,
matthias, hilton, liberty, elisabeth, market, rakoczi, synagogue, statue, citadella, varosliget, szechenyi, puskas, szell,
margaret, petofi, opera, erkel, keleti, nyugati, westend, ethnography, balna, zoo, eye, gellerthotel, bme, museum, a38, blaha,
sidequest, sidequest_inside), `mode` (map, walk, drive), `vehicle` (taxi, trabant, police, bubi, bus: for this visit;
the picker's choice is remembered), `date` (`MM-DD`, e.g. `10-20`, or a day of the year), `hour` (0-24) and `weather`
(clear, cloudy, rain, snow; the older `snow=1` still works), any of which starts on that date, at that hour and sky
instead of live (the others then today, noon or clear), `live=0` (today, noon and clear rather than Budapest's time
and weather), `lang` (en, hu), `ui=0`,
`promo=0` (no Minecraft and bar overlays), `minecraft=1` or `0` (the Minecraft card's feature flag), `tutorial=1` (show
the first-run guide even if it was dismissed) or `0` (never), `fps=1` (frame rate, frame time, draw calls, triangles
and tiles in a corner), `shadow` (the shadow map's size, 4096 by default) and `err` (how many pixels a voxel may cover
before finer tiles load: 2.2 by default),
e.g. `?view=parliament&date=10-20&hour=16.5&weather=rain&lang=hu`.

How it works:

- `engine/tiles.ts`: a quadtree over the five tile levels (16, 8, 4, 2 and 1 voxel cells). The coarsest level is
  always there; a tile gives way to its four children once they are all meshed, wherever one of its cells would cover
  more than `err` pixels. Walking and driving keep the finest tiles round you, with their columns, for collisions.
- `engine/mesher.worker.ts`: meshing in workers, straight from the runs: a column's top and bottom faces merged into
  rectangles per height, its side faces the stretches of its runs its neighbour doesn't cover, merged along the row,
  with ambient occlusion at the corners.
- `engine/material.ts`: one shader for every voxel, which reads the palette's colour and material and draws the detail
  in 0.5 m steps: windows and shop fronts on the plain walls (their rhythm follows the wall colour, and fades to the
  facade's average far away), curtain walls, water, lamps, lit windows at night, the lamps' light on the street, snow,
  wet streets and roofs, and the seasons: leaves that come, turn and drop per tree, fallen leaves, lawns by month.
- `engine/foliage.ts`: the trees' classes per 2 m (`data/foliage.bin`, from the build) and their dates
  (`data/phenology.json`) for the shader; `season.ts`: the day of the year, the date in the URL, and when snow can fall
  (`data/climate.json`).
- `engine/sky.ts`: the sun from a solar ephemeris, the sky's colours from its height, shadows that follow the camera,
  the cloud deck; `engine/weather.ts`: the four weathers eased into each other, with `engine/snow.ts` (the snowfall)
  and `engine/rain.ts` (the rain); `live.ts`: Budapest's clock and Open-Meteo's weather; `engine/world.ts`: the voxels
  as solid matter.
- `controls/`: the map (three.js OrbitControls for the mouse, its own touch gestures, keyboard flight), the walker and
  the vehicles (`drive.ts` the physics, `chase.ts` the chase camera, `exhaust.ts` the fumes, `streaks.ts` the speed
  streaks, `vehicles.ts` their sizes and handling, `models.ts` and `kit.ts` the models); `ui/`: the page, the vehicle picker, the time card, the first-run guide, the place names, the Minecraft and SideQuest Bar
  overlays, the FPS counter; `i18n.ts`: English and Hungarian. The loading screen is in `index.html`, so it shows
  before the code has arrived.

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

**Bridges**: the five Danube bridges in the box are built by hand (below). Every other mapped bridge (over railways,
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
known are drawn from their photos (`scripts/landmarks_statues.py`, docs/landmarks.md).

## Landmarks (`scripts/landmarks*.py`)

Thirty-nine landmarks are drawn by hand at 0.5 m, from reference photos and measured dimensions, on the positions, outlines
and heights OSM gives:

| Landmark | What's drawn |
| --- | --- |
| Parliament | 16-sided drum with buttresses and pinnacles, ribbed red dome, lantern and spire; the two stone needle towers on the river front; Gothic turrets; copper and tile roofs as aerial photos show them; buttress strips, pinnacles, windows storey by storey and gables on every wing; the riverside arcade; the main entrance's steps, arches and lions |
| Kossuth tér | the national flag on its 33 m mast, the dark granite square, the Rákóczi and Andrássy horsemen, the Tisza and Kossuth memorials, Attila József on the embankment steps |
| Chain Bridge | triumphal-arch pylons on cutwater piers, two chains a side with bulbs, hangers, lattice girders, the four lions |
| Liberty Bridge | the green cantilever trusses, portals, four masts with the Turul birds, tram tracks |
| Elisabeth Bridge | white pylons, main cables, hangers and back-stays; the deck on the road's axis with its six lanes marked |
| Fisherman's Bastion | arcaded, crenellated terrace walls and seven conical towers |
| Matthias Church | the 78 m Gothic tower in its storeys of blind arches and the Béla tower with its tiled helm, Zsolnay-tiled roofs in zigzags and diamonds over the cross gables, the south stair turret, the apse and its buttresses, pointed windows, the portals |
| Hilton Budapest | the white Baroque front of the Jesuit college on Hess András tér (fifteen bays, pilasters, pedimented windows, the steep tiled roof, the canopy), the St Nicholas tower with its octagon and spire, the 1970s wings with bronze glass strips behind the Fisherman's Bastion, the Dominican church's ruins in the court |
| St Stephen's Basilica | the colonnaded drum, ribbed copper dome, lantern; the bell towers' belfries and cupolas; the west front's steps, paired Corinthian columns, arched entrance with its gold mosaic, inscription and pediment |
| Buda Castle | the National Gallery's dome on its drum of paired columns; the palace at its real height with copper hipped roofs and rows of windows; the Lions' Court level with the Hunyadi court |
| Liberty Statue | the pedestal, the 14 m figure with the palm leaf facing down the new east cut, the side figures on their plinths, the white cross of 2025, the level terrace |
| Citadella | the fortress as renewed in 2020-26: battered walls with their walk, the Rondella with its court and glass foyer, the white concrete mouths and the east cut, the park on top, and the 12 × 6 m national flag on its 36 m mast |
| Heroes' Square | the colonnades with statues and chariots, Gabriel's column, the seven chieftains |
| Great Market Hall | brick walls in bands, the tiled roof with its glazed ridge, the front gable and towers |
| Rákóczi tér market hall | the crossing naves with aisles and corner pavilions, yellow brick with red bands, the main gable's great arched window in blue iron, the clock, the cornice and the city's arms, the wings' balustrades and obelisks |
| Dohány Street Synagogue | the striped brick towers and their gilded onion domes |
| Margaret Bridge | the two halves meeting at 150° on the island pier, six ochre segmental arches with lattice spandrels, limestone piers with prows and winged figures above the deck, the obelisks and crown on the island pier, the branch to the island along its road, lane markings, the Pest ramp running on as the street to Jászai Mari tér |
| Petőfi Bridge | four grey lattice girders, deepest over the piers, 112 + 154 + 112 m; the tram down the middle |
| Puskás Aréna | the leaning steel-mesh facade between 30 white lattice pylons, the roof with its white edge and translucent inner band, three tiers of red seats with glazed boxes, the striped pitch |
| Hungarian State Opera | the carriage porch, the five-arch loggia between paired columns, the balustrade of composers, corner pavilions with Muses in niches and square slate domes, Liszt and Erkel, the mansard with its iron crest; behind it one long pale zinc roof over the auditorium and the stage with two lanterns, low roofs with rows of skylights either side (as aerial photos show), the carriage drives |
| Erkel Theatre | the curved travertine front: seven glass bays between stone piers with banners, the white canopy, the ERKEL letters and the window strips under the parapet; the auditorium's vault, the stage house and the wings |
| Keleti Station | the barrel-vaulted shed, the great arched window on Baross tér with its clock and statues, the corner pavilions with Watt and Stephenson |
| Nyugati Station | the shed's glazed gable in its blue-grey iron grid between two domed towers, the slate roof with its glazed ridge |
| WestEnd City Center | the tilted glass canopy on its steel tree over the entrance on Nyugati tér, the glazed front between granite piers and the glass wedge, the hotel and offices along Váci út, the cinema hall, the roof garden with its pond, the Millennium garden's deck and the car park with its solar panels |
| Széchenyi Baths | the stone 1913 front with three ribbed domes, the yellow wings round the court, the three outdoor pools |
| Museum of Ethnography | two wings dipping to the path between them and rising outwards like ramps, the roof garden, the pixel grille of folk motifs |
| Zoo | the Great Rock, the Elephant House's Zsolnay dome and minaret, the main gate with its elephants |
| Bálna | the glass and steel whale between two brick warehouses |
| Ferencváros church | the 66.7 m tower with clocks, belfry and copper spire, between two stair turrets, before a brick basilica |
| Budapest Eye | the 65 m wheel with 42 gondolas, its legs and lights |
| Soviet War Memorial | the obelisk with its star and arms, the bronze reliefs |
| Gellért Hotel and Baths | the Art Nouveau front at the foot of the hill, its middle tower with the name, a steep red roof and a copper lantern, the two corner pavilions' green domes, the baths' rotunda under a dark ribbed dome, the swimming hall's glass vault; up the hill the open-air baths: the sun terrace's white arcade bent round the half-moon garden, the wave pool's terracotta deck and stepped end, the warm adventure pool, the children's pool |
| BME Building K | the ladder of brick ranges round light courts under steep slate roofs, the stone entrance pavilion with three arched doors, six giant columns, a balustrade, a crested roof and two spired turrets, the pyramid-roofed end pavilions, the aula's glass roof |
| Hungarian National Museum | the Classicist block round two courts, the portico of eight Corinthian columns on its stair with the figures in the pediment, pedimented windows, giant corner pilasters, the low dome over the Dome Hall |
| Kálvin tér skybridge | the glazed gallery on a flat arch across Kecskeméti utca, with planters on its roof |
| Corvin Palace | the old Corvin department store on Blaha Lujza tér with its stone front back: the arcade of round arches, giant fluted pilasters, the frieze, the cornice and the roof balustrade |
| Europeum | the cream stone shopping centre and hotel across the square: the glazed retail base, the grid of windows, the open stone frame at the corner, the red letters on the roof |
| Danube boats | every ship moored along the quays from its outline: pointed bows upstream, white decks with window bands and sun decks, awnings on the restaurant boats; the A38 (a Ukrainian stone carrier with its wheelhouse aft and a glass pavilion on deck) and its exhibition barge; the Kossuth paddle steamer with its paddle boxes and yellow funnel |
| SideQuest Bar | the bar that made the map, inside and out: the shopfront on Klauzál utca, the room, the bar, the steel stair, the mezzanine with the foosball table, the darts corner, the corridor and the toilets, all walkable |

[docs/landmarks.md](docs/landmarks.md) has the dimensions each one uses and links to the photos. The toolkit is
small: boxes, lathes (any profile turned about an axis, round or as an n-gon), roofs, arches, capsules, slabs that
follow a deck, extruded OSM polygons, and fields drawn from distances to an OSM outline (the stadium bowl). Each solid fills, carves, paints or fills only empty voxels.

**Curated** (`scripts/overrides.json`, keyed by OSM id, each with a source note): the Buda Castle palace gets its
height, hipped copper roofs and pale stone; Anker-ház on Deák tér its height, ochre stone and two domed corner towers;
Vörösmarty n°1 its pale blue glass (from street photos beside renders from the same spots).

## Publishing: two separate deployments

**The web viewer**: a static site on Cloudflare Pages. `./bv publish-web` builds it (`web/dist`, about 8 800 files
and 105 MB, without the map's tarball parts) and deploys it with wrangler (`bunx wrangler@4`). Pages stores files by
their hash, so only what changed is uploaded. The first run logs in to Cloudflare in the browser and creates the
project. Settings: `~/.config/voxelpest/web.env` (from `web/deploy/web.env.example`): the project name and
branch, optionally an API token. The site is at `https://<project>.pages.dev`; a custom domain is added once in the
dashboard. `web/public/404.html` makes missing files real 404s (without it Pages answers them with `index.html`) and
`web/public/_headers` caches the hashed bundles and the tiles for good: the build writes a hash of the tiles into
`meta.json` and the viewer asks for each tile with it (`?v=`), so a new map is never served from an old cache. On a
custom domain, set the zone's Browser Cache TTL (Caching > Configuration) to "Respect Existing Headers": by default it
raises Pages' `max-age=0` to 4 hours for the file types it caches. Pages takes up to 20 000 files of up to 25 MiB each: the
script checks both before deploying.

**The Minecraft server** (`minecraft/`): the same map at 1 block = 1 m, for Java and Bedrock players, at
**mc.side-quest.bar**. Nobody can break it; there are commands to fly and to teleport to the landmarks (`/lm opera`).
`./bv publish-minecraft` builds the world and uploads it; the server restarts on the new map by itself. Settings:
`~/.config/voxelpest/minecraft.env` (from `minecraft/minecraft.env.example`). The setup, the commands, how
updates reach the server and how the conversion works are in [minecraft/README.md](minecraft/README.md).

Neither depends on the other: they can run on different machines, and either can be published alone.

**Analytics** are off by default. With `UMAMI_URL` (your [Umami](https://umami.is) server) and `UMAMI_ID` (the website's id) in `web.env`, the published site loads Umami's script and reports visits and what people do: the mode, the vehicle, the places chosen, the date, time and weather set, the bar's card and pin, the help, the menu. It never sends a position (the locate button reports only whether it found you on the map), nor the page's query string, and it respects the browser's Do Not Track.

**The desktop app** (`desktop/`): the web viewer in an [Electron](https://www.electronjs.org) window, for WebGPU
(Chromium has it on Linux, on Vulkan; the system webviews don't), as a Linux AppImage that carries the map (about
210 MB, the map and Chromium). `./bv desktop` builds the site as `./bv site` does, with the same settings, and writes
`build/voxelpest-<version>-x86_64.AppImage`; nothing is uploaded. The app starts
full screen. Esc, or a controller's Menu button, opens a menu to leave full screen (F11 too), go to SideQuest Bar or
quit. Its bottom bar names the map's data sources where the website shows the help line; the help (the ? button)
covers the map, walking and driving for the mouse and keys, a touch screen or a controller. The viewer's URL
parameters can be given as arguments: `./voxelpest-0.1.0-x86_64.AppImage view=parliament hour=20 lang=hu`. Links
open in the desktop's browser. For a kiosk, `fullscreen=always` takes leaving full screen out of the menu (and the
app refuses it), and `nolink=true` turns every link out of the app into plain text (and the app opens none).
`./bv desktop dev` runs it on the viewer's dev server, in a window, with devtools on F12. It runs on Wayland as it
is; if it ever stays on the loading screen, `--ozone-platform=x11` runs it through XWayland.

The viewer shows a card for **SideQuest Bar**, who made the map, with a pin over the bar on Klauzál utca. The bar is
built inside and out, from its owner's photos and its evacuation plan: its door is open, so you can walk in, look
round the room, climb the steel stair to the mezzanine and its foosball table, and find the toilets
(`view=sidequest_inside` starts inside, on the map or with `mode=walk` on foot; `/lm sidequest_inside` in Minecraft). The **Play
in Minecraft** card (the number of players online, and how to join) is behind a feature flag, off by default:
`MINECRAFT=true` in web.env turns it on for the published site (`VITE_MINECRAFT` at build time), and `?minecraft=1`
or `?minecraft=0` in the URL overrides it. Its count comes from `MC_STATUS_URL` if you publish the plugin's status
endpoint, else from api.mcstatus.io.

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
  under the bridgeheads, dug down for headroom (docs/landmarks.md, "Bridge ends").
- **Landmarks** are built to the photos' proportions, not to plans, so their details are close rather than exact.
  The Fisherman's Bastion's tower positions are read off its OSM outline.
- **Sentinel-2 is 10 m.** It sets the tone of large roofs and parks; small roofs and street detail stay generic. An
  orthophoto (e.g. Lechner's 2023 25 cm imagery) in `data/raw/ortho/` would be the next step.
- **Licences.** GlobalBuildingAtlas is CC BY-NC 4.0, FABDEM and Sentinel-2 cloudless CC BY-NC-SA 4.0 and Mapillary
  CC BY-SA 4.0, so the generated tiles are non-commercial and share-alike. Check the terms before publishing them.

## Licences and credits

- **Code**: MIT. Inspired by [warsaw-vibe-voxel](https://github.com/stared/warsaw-vibe-voxel) by Piotr Migdał
  (MIT, © 2026): this project uses its tile format (`scripts/tiles.py`, read by `web/src/engine/mesher.worker.ts`), and
  `scripts/tiles.py`, `scripts/osm.py`, `scripts/osm_pbf.py` and `scripts/style.py` (`parse_colour`, the ground palette)
  started from its scripts. The viewer (`web/src/`) is this project's own code; it uses three.js's OrbitControls. Its
  rain streaks (`engine/rain.ts`), the cloud deck's noise (`engine/sky.ts`) and the wet streets (`engine/material.ts`)
  follow warsaw-vibe-voxel's `weather.ts`, `sky.ts` and voxel material; the seasons (`scripts/phenology.py`,
  `scripts/climate.py`, `engine/foliage.ts`, the trees and lawns in `engine/material.ts`) follow its phenology, climate,
  foliage and voxel material, and use its phenology table (DWD and iNaturalist dates, autumn colours and lawns from
  Commons photos).
- **Weather**: [Open-Meteo](https://open-meteo.com) (CC BY 4.0), asked for Budapest's current weather in live mode;
  its historical archive (ERA5, Copernicus Climate Change Service) for the climate and the phenology's shift.
- **Phenology**: Deutscher Wetterdienst, Climate Data Center (phenological observations, via warsaw-vibe-voxel);
  iNaturalist leaf annotations.
- **Data**:
  - © OpenStreetMap contributors (ODbL)
  - Copernicus DEM GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS
    by the European Union and ESA
  - FABDEM V1-2 (Hawker et al. 2022, University of Bristol, CC BY-NC-SA 4.0)
  - Sentinel-2 cloudless – https://s2maps.eu by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2023,
    CC BY-NC-SA 4.0)
  - Mapillary map features (CC BY-SA 4.0)
  - GlobalBuildingAtlas (Zhu et al. 2025, TUM, CC BY-NC 4.0)
  - Copernicus Urban Atlas Building Height 2012, as joined by Átló (atlo.team/boda)
  - Wikidata (CC0)
  - BKK GTFS
