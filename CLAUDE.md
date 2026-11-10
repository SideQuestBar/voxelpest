# Budapest in voxels: notes for Claude Code

A 5.4 × 5.0 km voxel diorama of central Budapest at 0.5 m, from free data (OSM, Copernicus DEM, FABDEM,
GlobalBuildingAtlas, Urban Atlas heights via Átló, Sentinel-2 cloudless, Mapillary map features, Wikidata), shown in
this project's own three.js viewer (map, walk and drive modes, EN/HU, keyboard, touch and game controllers). Inspired by
[warsaw-vibe-voxel](https://github.com/stared/warsaw-vibe-voxel), whose tile format it uses. Thirty-nine landmarks are
hand-built in `scripts/landmarks.py` and the `scripts/landmarks_*.py` modules (table below). `README.md` is the
user-facing description, `docs/landmarks.md` the per-landmark dimensions and photo sources. This file is the working
knowledge needed to pick the work up.

## Commands

`./bv` is the entry point (`./bv help`): setup, unpack/pack, map/voxelize/bench, web/site/check/publish-web,
minecraft/plugin/server/publish-minecraft, desktop (the viewer as a Linux AppImage, `desktop/`, below). The web viewer and the Minecraft server are **two separate
deployments**: `scripts/publish_web.sh` (a static site on Cloudflare Pages through wrangler; settings
`~/.config/voxelpest/web.env`, example in `web/deploy/`) and `scripts/publish_minecraft.sh` (`minecraft.env`,
`minecraft/docker-compose.yml`). Nothing in one refers to the other; they share only `web/public/data`. There is no
Docker for the web. JavaScript packages and scripts are Bun's (`bun.lock` in `web/` and `desktop/`; Node is still what Vite, electron-builder and wrangler run on). Underneath:

```
sh scripts/build_data.sh                               # fetch (cached in data/raw) + prep + voxelize, ~28 min
PYTHONPATH=scripts uv run python scripts/voxelize.py   # voxelize only (needs data/prep.npz and data/raw)
BENCH=parliament PYTHONPATH=scripts uv run python scripts/voxelize.py   # one 192 m window -> data/debug/bench_*.npy, ~1 min
uv run python scripts/preview.py data/debug/bench_parliament.npy out.png --az 220 --el 18 --zmin 20
uv run python scripts/elevation.py data/debug/bench_margit.npy out.png --at 2379.6,680.6 --ang 0.6849 --u=-260:20 --v=-60:60
NOTILES=1 ...                                          # everything up to the tile export
cd web && bun install && bun run dev                  # viewer on http://localhost:5173
cd web && node tools/shot.mjs out.png "view=parliament&hour=14"   # screenshot (Playwright; SWIFTSHADER=1 without a GPU)
cd web && bunx tsc --noEmit -p .                       # type-check the viewer
./bv desktop                                           # the desktop app (Electron) -> build/voxelpest-VERSION-ARCH.AppImage
cd desktop && bun test                                # its scheme's path guard, arguments, link environment
uv run python scripts/minecraft.py                     # the Minecraft world -> build/minecraft (~5 min, 411 MB)
uv run python scripts/minecraft.py --only 4:6,4:6      # a few regions; --landmarks-only: just landmarks.yml/map.yml
cd minecraft/plugin && JAVA_HOME=/opt/jdk25 mvn -q package && cp target/voxelpest.jar ../  # the plugin
PYTHONPATH=scripts uv run python scripts/sidequest.py  # the bar's pin and view into a built meta.json
```

BENCH spots are in `voxelize.py` (`spots`, lon/lat): parliament, chain, basilica, matthias, statue, heroes, market,
city, elisabeth, liberty, castle, synagogue, varosliget, puskas, szell, oktogon, margit, petofi. `BENCH=1` builds all
of them, `BENCH=city,szell` a list, `BENCH_SIZE=1024` a bigger window (default 384 voxels = 192 m). The run ends with the
peak memory. `elevation.py` draws a bench window square-on (orthographic, looking along a frame's +v): the best check
for bridges and facades, since `preview.py`'s splats blur thin lattice work.

Prebuilt tiles ship as `web/public/voxelpest-data.tar.gz.part-*` (19 MB parts, ~87 MB in all, so each part fits
a 20 MB file limit). After a rebuild: `./bv pack`. `./bv unpack` (and every command that needs the data) unpacks
them when `web/public/data` is missing or older than the parts.

## Pipeline

| File | Role |
| --- | --- |
| `aoi.py` | The grid. EOV (EPSG:23700) turned THETA = 41.5° so Pest's street grid lies on voxel faces (`orient.py` measured it). W × D = 5376 × 4992 m (Széll Kálmán tér to the Puskás Aréna). `to_grid` / `to_world`. |
| `fetch_*.py/.sh`, `osm_pbf.py`, `rangezip.py` | Downloads. OSM from BBBike's Budapest extract; GBA and FABDEM read by HTTP range requests out of big zips; Sentinel-2 from EOX's WMTS; Mapillary from its vector tiles. |
| `prep.py` | DSM, FABDEM (`dtm`), GBA and Sentinel-2 (`s2`, uint8 RGB) resampled onto the 1 m grid -> `data/prep.npz`. |
| `osm.py` | OSM JSON -> shapely geometries in grid coordinates (x = column, y = row, metres). |
| `style.py` | Palette (`pal(rgb, material)` -> id) and material ids, matching `web/src/meta.ts` `MAT`. |
| `voxelize.py` | Heights, roofs, ground, bridges on the 1 m analysis grid; `build(r0, r1, c0, c1)` makes the 0.5 m voxels of one window. |
| `trees.py` | Every tree's species (`SPECIES`: class, form, sizes, leaves, bark) from OSM's tags (`RULES`, `species_of`) or a mix per setting (`MIX`), its size and crown (`make_crown`, cached per species / radius / crown height / variant), drawing (`Forest.draw`: wood first, then leaves) and the foliage grid (`Forest.plane`, `check`). Classes are the viewer's seasons' (contract below). |
| `landmarks.py` | `Plan(osm)` says which OSM buildings a landmark replaces (dropped before fusion); `build(ctx)` returns a `Scene` of solids that `build()` draws into each window. |
| `landmarks_more.py` | The third batch: Gellért Hotel and Baths, BME Building K, the National Museum, the Kálvin tér skybridge, the Danube boats (every `building=ship`/`houseboat`, generic hull + decks, A38 and Kossuth special). Same `NAMES` / `drop_ids(osm)` / `BUILDERS` hooks. Helpers: `front_frame` (a frame whose +v faces a direction), `front_profile` (the outline's front line per u: finds projections such as porticos and pavilions), `wall_coord` (the coordinate along the nearest wall, for bays), `pool_basin`, `Hull`, `UProfile` (a solid between two height profiles). |
| `landmarks_kossuth.py` | Kossuth tér: the 33 m flag mast and the flag, the dark granite square on the dome's axis, the main entrance's steps, arches and lions, the Rákóczi and Andrássy horsemen (`horseman`), the Tisza and Kossuth memorials, Attila József. Positions are OSM's nodes; the dome's axis comes from the Parliament's outline. Runs after `parliament`, which leaves its wall ids in `ctx["parl_walls"]`. |
| `landmarks_hilton.py` | The Hilton Budapest on Castle Hill: the Baroque front of the Jesuit college on Hess András tér (bays, pilasters, pedimented windows, the tiled roof), the St Nicholas tower with its 1970s octagon and spire, the 1970s wings as a Field from the outline (fins, bronze glass strips, slate hoods and mansards, `wall_coord` for the bays), the Dominican church's nave as an open court with its ruins. `front(g, theta)` is the frame along the Baroque front; voxelize.py uses it for the `hilton` view. |
| `landmarks_citadella.py` | The Citadella on Gellért Hill as renewed in 2020-26: walls (a Field from the distance to the outline: battered face, parapet, walk, railing), the Rondella with its terrace, court and glass foyer, the reception square, the casemate ranges, the white concrete mouths and east cut, the park, the Liberty Statue's terrace (`statue_frame`: the statue faces down the cut, between its side figures), grass and young trees round the walls, and the 36.3 m mast with its 12 × 6 m flag (`landmarks_kossuth.flag`, the hoist drawn from the mast's voxels). `ground()`, called from voxelize.py's ground model, sets the park (229 m), the square, the Rondella's court, the statue's terrace and the promenades round the walls (FABDEM dug the fortress out; the summit node raised the plaza west of it). Same `NAMES` / `DROP` / `BUILDERS` hooks. |
| `landmarks_matthias.py` | Matthias Church drawn whole (`landmarks.matthias` calls it; `parts(osm)` lists the OSM parts it replaces, all of them): the hall, choir and apse, the cross roofs over the aisle bays, both towers, the west front, the annexes on OSM's part outlines, laid out in the nave's frame (u along the axis, v towards the square). Tile patterns per face: `roof_tiles` (a `Roof`'s long slopes and hipped ends) and `facet_tiles` (an n-gon `Lathe`) give a pattern `f(s, z, h)` the coordinate along each face's eaves; `chevrons`, `rosettes`, `apse_diamonds`, `bela_tiles`. `window` (a recessed traceried lancet), `buttress`, `gable_wall`, `Disc` (a cylinder along u: roses, roundels). |
| `landmarks_erkel.py` | The Erkel Theatre: one `Field` over OSM's outline (a zone and a roof height per 0.5 m cell: front range, end blocks, the auditorium's vault, stage house, wings) and the front on the circle its corners lie on (`front_arc`, also used for the `erkel` view). `Ring` is an annular sector about a frame's axis: the bays, canopy, banners and the ERKEL letters (a 4 x 5 pixel `FONT`) follow the curve. Same `NAMES` / `DROP` / `BUILDERS` hooks, but `DROP` is empty: a dropped outline leaves the ground model free to read its roofs in the 30 m surface model as ground (it lifted the square round the theatre by up to 1 m), so the outline stays and a carve `Field` clears the generic building first. |
| `landmarks_rakoczi.py` | The Rákóczi tér market hall: two crossing naves with aisles, links and four corner pavilions on OSM's outline (`spans`: where a frame line crosses it, for the arms' ends and the pavilions' steps); the main gable (arched window, sign, clock, raking entablature, the city's arms), wings with balustrades and obelisks, simpler gables on the other three sides. Same `NAMES` / `drop_ids(osm)` / `BUILDERS` hooks, and `KEEP_GROUND` (-> `Plan.ground_cover`, see the gotchas). |
| `landmarks_blaha.py` | Blaha Lujza tér: the Corvin Palace (the stone front to the square and its returns, element by element from each corner: `front_layout`, `return_layout`, `stone_face`; the back ranges as a `Field` with rounded corners and a court) and the Europeum (one `Field`: per cell the nearest street front, `fac`, and the coordinate along it give the bays, the corner cut away behind its open frame, the top storeys; the roof sign from `GLYPHS`, a pixel font). `straight_runs` merges an outline's collinear edges into walls, `north_front` finds the front to the square. Same `NAMES` / `DROP` / `BUILDERS` hooks. |
| `landmarks_sidequest.py` | SideQuest Bar inside and out, to walk into: the shopfront, the room, bar, stair, mezzanine and toilets from the owner's photos and the bar's evacuation plan (docs/landmarks.md has the plan as ASCII and what each photo showed). `layout(osm)` puts the frame (u along the street, v inwards, w up from the floor) on the street front from `sidequest.py`'s door, the building's corner and the gateway's entrance node; carves stay a voxel inside the outline (`Within`). Every way people walk lies on whole metres: Minecraft's 1 m blocks give a half-metre wall beside it the whole block, and turn chairs into posts. Fills `INSIDE` for voxelize.py: the `sidequest_inside` view (with `walk`) and a `meta.lamps` entry that lights the room at night. Check walkability on a bench with a BFS under walk.ts's rules (a 0.6 m body, every column under it) and on the 1 m downsample: a first version left the far end, the corridor and the toilet reachable only by jumping off the landing. |
| `landmarks_westend.py` | The WestEnd City Center by Nyugati: the mall, hotel, offices and cinema hall as one `Field` of zones (heights, brick, glass and metal facades, the roof garden's surfaces), the Millennium deck and the car park as fields with columns and decks, the tilted glass canopy as a `Quad` (a parallelogram plate) with its beams as a second `Quad` under it (straight lines on a turned grid), trusses and the steel tree as voxel lines; the entrance front's layout (`PIER`, `GLASS_TO`, `WEDGE`) is across the canopy's frame. Positions are measured from the outline's west corner (`NW0`); `view()` gives voxelize.py its `westend` view. Clears the generated trees inside the complex (`Scene.clear`). |
| `landmarks_city.py` | The second batch (Opera, stations, baths, zoo, museum, Bálna, church, wheel, memorial) on landmarks.py's toolkit: `DROP` and `NAMES` feed `Plan`, `BUILDERS` feeds `build`. Helpers: `base_under`, `facing`, `named_near`, `grid_of`/`dist_in` (Field grids), `windows`, `statue`, `Vault` (barrel vault shell), `Gable` (arched gable wall), `rock` (artificial mountain). |
| `landmarks_statues.py` | Runs last (it reads what the others drew in `S.prims`). `church_windows`: round-headed windows on every church and church part not already painted by a landmark (a paint prim targeting its wall id over its bbox). `statues`: every OSM statue/bust/sculpture node or small area on a pedestal, facing the nearest way (or the river), skipping facades, other levels and spots a landmark already fills (small fill prims within 3 m); `MONUMENTS` (by OSM id) are the curated ones, `gellert`, `turul`, `vorosmarty` custom builders. Both ideas from warsaw-vibe-voxel. |
| `tiles.py` | Export. Each 256 × 256 voxel window is built once: four level-1 tiles are written, compressed downsampled copies are kept for levels 2/4/8/16 and assembled at the end. |
| `sidequest.py` | SideQuest Bar (who made the map) from OSM by its website: the viewer's pin (`meta.sidequest`) and the `sidequest` view. |
| `climate.py` | Budapest's weather per day of the year from Open-Meteo's ERA5 archive (1995-2024, ±10 days): `climate.json`'s `snowy` (any snow in 30 years: none on days 124-285) gates the viewer's Snow, plus the shares of clear / cloudy / rain / snow days and lying snow for a "typical" weather later. `archive()` asks five years at a time and waits out Open-Meteo's per-minute limit (a 30-year request outlasts the proxy). After warsaw-vibe-voxel's. |
| `phenology.py` | `phenology.json` (FOLIAGE-CONTRACT): warsaw-vibe-voxel's per-class leaf-out / colouring / fall table (DWD east of 12.5° E, iNaturalist; vendored in `WARSAW`) moved to Budapest by thermal time from ERA5 daily means (Berlin and Dresden for the DWD region, Budapest's cell): leaf-out where Budapest reaches the region's degree-days over 5 °C, colouring and fall where its smoothed mean temperature falls to the region's; class 15 (Platanus) added; Warsaw's monthly lawn tints normalised to its summer and shifted the same way; `city` medians weighted by foliage.bin's cells when it exists. Both run at the end of `build_data.sh`. |
| `minecraft.py`, `minecraft_blocks.py` | The tiles as a Minecraft world, and the blocks' colours (minecraft/README.md). |
| `publish_web.sh`, `publish_minecraft.sh` | The two deployments: the viewer to Cloudflare Pages (`wrangler pages deploy`, the project created first), the Minecraft server by rsync + ssh + `docker compose up -d`. |
| `overrides.json` | Hand fixes keyed by OSM id (the palace's height, hipped copper roofs and pale stone; Anker-ház; Vörösmarty n°1) and `add` parts (Anker-ház's two domed towers). |

**Mapillary token.** `fetch_mapillary.py` reads `MAPILLARY_TOKEN` from the environment and never writes it anywhere.
Keep it out of the repo (no `.env` in the project). Its output, `data/raw/mapillary/features.json`, is cached, so
rebuilds don't need the token. Run it with `uv run --with mapbox-vector-tile`.

**Two grids.** Analysis at 1 m (`W, D`; arrays `g`, `G`, `bz*`, `dtop`, `odist`, ...). Rendering at `VOX = 0.5`
(`F = 2`, `WF, DF` = 9216). In `build()`: footprints, parts and decks are rasterized again at 0.5 m (`fine_buildings`),
the ground (`ground_fine`) and roof distance fields are interpolated, roads (`gcol`) are painted at 0.5 m globally,
cornices are added under pitched eaves, then trees, point voxels (`PV`: lamps, railings, landmark lines) and
`LMS.apply()` (landmark solids). z is in voxels above `BASE` (94 m); `g` (1 m) is in metres.

**Tile format** (Warsaw's): gzip of counts uint16[(N+2)²], ground uint8[(N+2)²] (metres!), runs (z0, len, palette)
uint16, then detail voxels (x, y, z, palette) for levels 2/4/8 (thin things lost by downsampling, drawn at full size).
N = 128 cells per tile, 1-cell apron. Levels 1, 2, 4, 8, 16 voxels per cell.

## landmarks.py

- `Frame(ox, oy, oz, ang)`: origin on the 1 m grid, `oz` metres above BASE, +u at angle `ang` on the grid, +v at
  +90°, +w up. `fr.at(u, v, w, turn)` makes a child frame.
- Solids (`Prim` subclasses): `Box`, `TBox` (tapered), `Lathe` (profile `f(t)` turned about w, round or n-gon;
  `cyl`, `cone`, `dome`, `onion` profiles; `inner` hollows it), `Roof` (pitched, `hip`), `Arch` (round or pointed,
  opening along u), `Ellipsoid`, `Capsule`, `Slab` (between `zf(u)+a` and `zf(u)+b`: decks that follow a road), `Poly`
  (an OSM polygon extruded between absolute heights), `Field` (2D fields precomputed on the 0.5 m grid, e.g.
  distances to OSM rings, plus `fn(fields, w) -> ids`; absolute heights; the Puskás Aréna's bowl, roof and facade).
- Modes: `fill` (default), `carve`, `paint` (recolour only voxels whose palette id is in `targets`: windows on a
  wall), `under` (fill empty voxels only: pilasters that must not cut into a neighbour). `col` can be a function
  `f(u, v, w) -> ids` (0 = leave alone): ribs on domes, Zsolnay tiles (`zsolnay()`), rustication, stripes.
- Long thin things are voxel lines: `S.line`, `S.polyline` (chains, cables, hangers, truss members).
- Solids apply in insertion order; carve after fill. `Scene.apply` only evaluates a solid over its bounding box.
- **Height convention, a past bug:** in a frame standing on a base (`Frame(x, y, b0, ...)`) heights are relative;
  `Poly`, and frames with `oz = 0` (`seg_frame(a, b, n, 0)`, bridges), take absolute heights. Mixing them put the
  market hall's roof 16 m in the air once.
- Bases: `feat_base(ctx, osm_id)` is the median ground under an OSM building, in metres above BASE;
  `ctx["ground_m"](x, y)` is the ground at a point.
- Landmarks depend on hard-coded OSM ids (in `Plan` and each builder). If OSM changes one, that landmark is skipped
  with a log line `landmark X: skipped, OSM feature N missing`, and the rest still build. The Fisherman's Bastion's
  tower positions are lon/lat in `BASTION_TOWERS`.
- Hand-built bridges: add the OSM bridge name to `Plan.bridges` so voxelize.py skips its generic deck and piers (the
  ways on it are not painted either: `deck_col` paints tram, lanes and pavements). Give its geometry to
  `bridge_decks()` too: voxelize.py digs the roads that cross under each deck and keeps its bridgehead out of the lower
  quay. Over land, `approach()` fills solid wherever the headroom would be under 2.5 m and stands the deck on columns
  over the dug roads; `bank_pier()` opens over a road along the bank. Axes come from OSM's piers;
  `wet_extent` finds where the river ends along an axis; `circ_arch` makes a segmental arch; `figure` a simple statue.
  Lamps go through `ctx["lamp_post"]` so they light the night shader.
- Materials: `CLASSIC` (stone, no window grid), `ROOF`, `METAL`, `WINDOW` (21: dark glass, lit at night), `LAMP`
  (glows). Avoid `METAL` for reddish colours: the shader makes red metal glow at night.

## voxelize.py: ground, streets, colours

- **Ground** ("ground: bare earth"): FABDEM, plus a correction where the DSM sees open ground (no buildings or canopy
  within reach, on land): DSM − FABDEM clipped to −6..25 m, spread by normalized convolution (σ 2 and 6 cells of 8 m).
  Open excludes the blur of tall roofs (12 m + 0.8 × height). Then smoothing: gentle ground at σ 4 cells, the Pest bank
  (the land component east of the river, `pest8`) at σ 20 cells within itself. Then OSM `natural=peak` `ele` raises
  (Gaussian σ 40 m). Then OSM's RTK points (`triangulation_point=yes` / `survey_point` / `source=RTK`, not within 12 m
  of a bridge): a Pest-wide pass (σ 600 m, Pest points, applied in `pest8` only), then a local one (σ 150 m). The log
  prints the fit before and after (3.6 m → 0.1 m median) and the ground on named squares (Szent István tér 109, Deák
  tér 106.6, Szent György tér ~160). Without `dtm` in prep.npz it falls back to the old DSM-minus-buildings model.
  A landmark's dropped outline is open ground to this test unless `Plan.ground_keep` lists it (outline, height): the
  Hilton's roofs, read as ground, lifted Hess András tér 6 m.
- **Roads**: `road_profile(tags, kind)` -> lanes, lane width, parking each side, cycle lanes, tram, total width.
  `canyon()` cuts each way into 12 m pieces and narrows each to the room between buildings (`d_bld` − 2 m) and mapped
  sidewalks (`d_sw` − 0.9 m), min half-width 1.6 m. Then parking strips (`parking_lane`), lane lines (`mark`), kerbs.
  `gcol` (0.5 m) holds it all; the road mask must list every road class (asphalt, sett, parking, parking_lane, mark,
  kerb, rail, trambed, ballast).
- **Sentinel-2**: per-building median over the interior (≥3 m from the edge), z-scored over all buildings and mapped
  onto the palette's pitched/flat roof statistics; `f["s2_roof"] = (z, weight)`, used in `fuse()` when no OSM/override
  colour. Unmapped paving that S2 sees as green (≥40 m² patches) becomes garden with trees on a 9 m lattice.
- **Trees**: placed in the "trees" section (OSM nodes and rows, woods, parks, scrub, green courtyards, Sentinel-2 street
  trees, all with one seeded `rng`: one more draw moves every later tree); each tuple carries its source, tags and OSM id.
  Their first sizes only feed `canopy` (the ground model's open-ground test). Species, final sizes and shapes come after
  the ground, in "trees: species, shapes, the foliage grid" (`trees.Forest`), so tree work never moves the ground. The
  setting per tree: Margaret Island (`place=island`), park / wood polygons, Buda (`~pest8`) for the hills' mix, the
  distance to water (4 m blocks) for banks, the distance to buildings (`near_mask`, 10 m) for narrow streets and for
  crowns leaning off facades. Everything per tree is a hash of its position or OSM id (rows: the row's id), no `rng`.
  `Scene.clear` uses the final crown radius. In `build()` the trees near a window (`FOREST.reach` voxels) are drawn in
  index order, wood first (trunk, limbs: bark ids, in `leaf_ids` so the coarse levels skip them as detail), then
  leaves; over road cells (`ROADLUT` on `gcol`) nothing but the trunk is lower than 4.5 m above the trunk's foot (drive
  mode's buses). Crown shapes are cached (~3 400 keys, 35 MB of int8 offsets, ~20 s to make them all).
- **Foliage grid** (the contract with the viewer's seasons: `FOLIAGE-CONTRACT`, classes in trees.py's docstring):
  `foliage.bin` = gzip of two uint8 planes `cols × rows` (2 m cells, `ceil(W/2) × ceil(D/2)` metres): the class of the
  tree whose crown is highest in the cell (from each crown's cached footprint), and a byte of that tree's id (1-255);
  `meta.foliage = {cell: 2, cols, rows}`. Every leaf colour belongs to one class (`style.FOLIAGE`, asserted in trees.py),
  so a leaf voxel's class can be read back from its palette id. A bench writes `bench_<name>_foliage.npy` (the cells over
  the window; `foliage.j0/i0` in its json) and logs the check: the share of tree-leaf columns whose cell has a class and
  has that leaf's class.
- **Mapillary** ("street furniture seen by Mapillary"): last seen after 2019. Dense photo coverage multiplies
  detections (12 700 "lights" in one km² of the Belváros; traffic lights come as -front/-side/-back), so each kind is
  thinned with a KD-tree to a real spacing (lights 18 m, signals 15 m, signs 22–30 m, bins 10 m, benches and racks 6 m; most
  recent kept). Signals only within 30 m of an OSM `traffic_signals` node. Moved to a free cell within 4 m (`blocked` =
  buildings, roads, water, decks) or dropped; lights within 15 m of an OSM lamp are skipped. Zebras not within 12 m of
  an OSM crossing are painted 4 m wide across
  the nearest car road. Utility poles, bollards and catenary poles are in the data but not drawn.

## Minecraft (minecraft/, scripts/minecraft*.py, scripts/publish_minecraft.sh)

Full description in `minecraft/README.md`. Working knowledge:

- **Converter** reads the level-2 tiles (1 m cells, z in metres above BASE), one 512 × 512 region at a time with a
  one-cell apron from the neighbouring tiles. y = metres asl − 36: BASE 94 → y 58, water → y 62. Chunks are written
  in 26.x's layout (`world/dimensions/minecraft/overworld/region`), palette entries as compounds, `isLightOn 0`, no
  heightmaps (the server makes them). `minecraft_blocks.json` (from `minecraft_blocks.py`, which reads the client
  jar's textures) is all it needs from Mojang.
- Materials map to block families (`FAMILY`); WATER and JET become water. Water once fell through to the generic
  family and the Danube came out as grey terracotta: check the preview's river when touching the mapping.
- **Plugin** (`bar.sidequest.voxelpest`, Paper API 26.3, Java 25): `VoxelpestPlugin` (landmarks, commands, flight,
  bounds, time, the map watcher that restarts the server on a new `map.yml` and reloads `config.yml` when it
  changes), `Protection` (every block-changing event cancelled unless `voxelpest.build`), `StatusServer`
  (`com.sun.net.httpserver` on 8765, counts only). Settings come from `$VOXELPEST_CONFIG` (the uploaded project file)
  with the jar's config.yml as defaults; `MAP_URL`, `BAR_URL`, `MC_ADDRESS` from the environment win.
- **Server**: `itzg/minecraft-server:stable-java25` (`TYPE=PAPER`, settings mapped from minecraft.env to the image's
  names in docker-compose.yml, e.g. `WHITELIST` -> `ENABLE_WHITELIST`: the image's own `WHITELIST` is a player list).
  `server/start.sh` is the entrypoint: it swaps the map, copies the plugin, writes what the image doesn't cover
  (bukkit.yml's allow-end, Geyser's auth-type), chowns what it wrote to `UID` (the image only chowns when /data itself
  isn't owned by it), sets `MODRINTH_PROJECTS` (`geyser:beta`, `viaversion:beta+`, `viabackwards:beta+`: Geyser only
  has betas on Modrinth, `beta+` prefers a release) and `PLUGINS` (Floodgate from GeyserMC: no Paper build on
  Modrinth), then `exec /start`. The status port is bound to 127.0.0.1 unless `STATUS_BIND` is set. `./bv server` runs
  the same compose file on `build/minecraft` + `build/mc-data` (`MC_MAP`, `MC_DATA`; `MC_UID=0` under rootless podman,
  whose root is you, else your uid); `restart: unless-stopped` brings it back when the plugin stops it for a new map.
  Aikar's old `-XX:G1RSetUpdatingPeriodMillis` stops Java 25; the image's `USE_AIKAR_FLAGS` doesn't use it.
- **Geyser** writes `auth-type: online` into its config; start.sh sets `floodgate` on every start.
- **Testing without a client**: mineflayer (`npm i mineflayer`) speaks up to 26.1. Against 26.3 through
  ViaBackwards, a 26.1 or 1.21.x bot gets kicked for "invalid player movement"; `version: '1.20.6'` works (ignore its
  PartialReadErrors). Use `ONLINE_MODE=false` for bots. Run `./bv server` and send console commands with
  `docker exec voxelpest-minecraft rcon-cli <command>`; `forceload add x z` before `execute if block`.
- The publish scripts can be tested without a server: put an `ssh` shim first in PATH that drops the options and
  the host and runs the rest with `sh -c`; rsync then copies locally. `XDG_CONFIG_HOME` points them at test settings.
- Page screenshots with the HTML overlays (`page.screenshot`) time out in SwiftShader while the render loop runs:
  render once, `renderer.setAnimationLoop(null)`, then take it.

## Viewer (web/src): this project's own

- World units are **metres**; tiles are in voxels: `Tiles.group` is scaled by `meta.vox`. three.js axes: x = grid
  column, y = height above `meta.base`, z = grid row. `meta.json`: `W, D, H` in voxels; labels, views, lamps in metres;
  views `[column, height, row]`; `views[k].label_hu`; `views[k].walk` (the camera stands on a floor indoors: walk mode
  goes there instead of to the nearest pavement); `sidequest.door` (the pavement in front of the bar) and `heading`.
- `engine/tiles.ts`: quadtree LOD (split where a cell covers more than `err` px, default 2.2; a tile shows until all
  four children are meshed), a worker pool, tiles unused for 10 s freed. `setFocus(x, z, r)` forces the finest level
  within r m of the walker or car; finest tiles come back with their columns (`columns(x, z)`). Tile URLs must be
  absolute (`new URL(..., document.baseURI)`): a relative one resolves against the worker's script and 404s. A tile
  leaving the view (its children or its parent took its place) dissolves over its replacement for 450 ms (`fading`):
  material.ts's eight `fading` copies define `FADE` and drop a growing share of pixels in a screen-space pattern, with
  their own program so the opaque one has no `discard`; drawn last (`renderOrder` 1), casting no shadow. `warm()`
  compiles that program ahead (`compileAsync`) at the start and whenever the sun sets or rises: `sun.visible` changes
  the light count, and three.js then recompiles every lit program. (`compile` where KHR_parallel_shader_compile is
  missing, Firefox: three.js warns otherwise.)
  **Shared index**: every tile draws with one quad index (`indexFor`, grown by doubling). `geometry.dispose()` deletes
  the index buffer too, and three.js doesn't rebind it in vertex arrays it thinks unchanged: the vertex array bound at
  the time (the last tile drawn) lost it, and that tile stopped drawing (Firefox: "drawElementsInstanced: Index buffer
  not bound"). `free()` counts each index's users (`users`) and detaches it before disposing unless it is the last.
  Chromium hides this in a slow SwiftShader run (the bound one is usually a dissolving tile's, not drawn again): to
  test, check `ELEMENT_ARRAY_BUFFER_BINDING` before each draw with a mesh drawn before the stale one.
- `engine/mesher.worker.ts`: faces from the runs (tops/bottoms merged per height where fully lit, sides as uncovered
  stretches merged along rows; AO in the merge key; faces out through the tile edge always drawn, the neighbour may be
  at another level). Vertex: position Int16 (voxels), `va` Uint8×4 (face 0-5, AO 0-3, ground m, level), `vp` palette.
  `job.see` (with foliage: `tiles.see`, 1 for LEAF palette ids): a leaf hides no other voxel's face, so the trunk and
  branches inside a crown and a wall behind a tree are meshed and show when the leaves drop (leaf faces against
  leaves stay culled: a bare crown is a shell of twigs round its branches).
- `engine/material.ts`: MeshStandardMaterial + onBeforeCompile. Procedural detail in voxel steps keyed on the
  material id (style.py): windows/shops on WALL/TENEMENT/CONCRETE (bay and storey from a hash of the palette index,
  faded to the facade average by `fwidth`), curtain walls, WINDOW, water, lamps, snow on up-faces (`look.snow`),
  wet surfaces in the rain (`look.wet`: darker, glossier, puddles on the street that mirror `look.sky` and glint
  under the lamps), lamp pools from `meta.lamps` (a canvas texture, 2 m/texel). No metalness: there is no environment
  map, so glass and water fake their sky reflection with emission. **Seasons** (`look.season`, filled by
  `engine/foliage.ts`; after warsaw-vibe-voxel's voxelMaterial.ts): `uGrass` tints green lawn palettes by month (flowers
  keep theirs); with `FOLIAGE` defined (only when `meta.foliage` exists, so the program without foliage has no
  `discard`), each LEAF voxel reads its 2 m cell's class and per-tree byte (`foliageAt`: that tree's date is the
  class's plus a triangular spread of ±2.45 sd) and is bare (dropped by `discard`, a share kept as dark twigs, more in
  a far tile's coarse blocks: `vS` is the tile level), fresh light green for a month after leaf-out, green, or turned
  to the class's autumn colour voxel by voxel; class 0 (hedges, roof gardens, planting off the tree map) never drops
  and dulls with the lawns; fallen leaves (`litter`) lie on the ground under deciduous crowns from leaf fall to 50 days
  after, thinner on paving. `makeMaterial` also returns `depth`, the shadow pass's material with the same drop
  (`tiles.depth` -> `customDepthMaterial`).
- `engine/sky.ts`: a solar ephemeris for Budapest (`sky.day`, the chosen day of Budapest's year; `instant(hour, day)`
  the slider's clock hour that day, CET/CEST), sky dome, sun
  with a camera-following shadow box (texel-snapped), hemisphere, moon, fog. `set(hour, weather.levels)`: snow makes it
  overcast as before; `cloud` (cloudy, rain) greys the sky (sodium orange at night), weakens the sun and draws it
  towards the zenith, and fades and softens its shadows (`shadow.intensity`, `shadow.radius`: uniforms, no
  recompile; the sun's `visible` never follows the weather), `rain` darkens it and thickens the haze; `deck` and
  `cover` draw the cloud deck (fbm in the dome's shader, only when `uCloud > 0`). `engine/weather.ts`: `Weather`
  (`set(kind, cover?, now?)`, levels eased in `update`), owning `engine/snow.ts` (flakes in a box that wraps round the
  camera) and `engine/rain.ts` (line segments in a 70 m box, the same wrap; fewer on small screens and at a low pixel
  ratio). Ported in spirit from warsaw-vibe-voxel's weather.ts / sky.ts (MIT, credited in the files and README).
- `season.ts`: the day of the year (`budapestDay()`, Budapest's date, not the browser's; `dateOf`, `dayOf`,
  `yearDays`), `parseDay` (`?date=MM-DD`, `YYYY-MM-DD` or a day of the year), `dayName` (Intl, "15 Apr" /
  "ápr. 15."), `snowy(day)` from `data/climate.json` (13 Oct to 3 May without it). main.ts's `setDay(d)` sets
  `sky.day`, `look.season.day` and the card, and turns a manual Snow into Rain on a date it can't snow (live weather
  is what it is). `engine/foliage.ts`: `loadSeasons(meta, season)` reads `phenology.json` (grass, classes) and, when
  `meta.foliage` exists, `foliage.bin` (gzip, DecompressionStream) into an RG8 texture, then `season.on`; missing
  files leave the trees (or everything) as they were. `treeColour(day, city)`: the city's trees on a day, for the date
  slider. To develop without the build's foliage.bin, any file in the contract's format will do (a dev-server
  middleware serving it and adding `meta.foliage` to meta.json).
- `live.ts`: live mode, the default. `budapestHour()` (the hour on Budapest's clock), `reading()` (WMO code → clear /
  cloudy / rain / snow: 0-2 clear, with `cloud_cover` drawing some clouds; 3, 45, 48 cloudy; drizzle, rain, showers,
  thunderstorms rain; 71-77, 85, 86 snow), `Live` (Open-Meteo `current=` for Budapest's fixed coordinates, no
  referrer or cookies, every 12 min while live and visible, again on `online`; a failure keeps the last reading for an
  hour, then clear). main.ts: `hour` follows `budapestHour()` every frame while live (`ui.setHour` once a minute,
  and the date at Budapest's midnight); the sliders, a weather button, the menu's Date, Hour and Weather rows and
  `__three.setHour/setDay/setWeather/setSnow` call `manual()`. `?hour=`, `?date=`, `?weather=` (or `?snow=1`) and
  `?live=0` start manual, at today / noon / clear unless given; `tools/shot.mjs` adds `live=0`.
- `engine/world.ts`: collision queries on the finest columns (leaves and fountain jets are not solid; water is a floor).
- `controls/walk.ts`: 0.6 × 1.8 m body, step 0.6 m, gravity, jump, pointer lock; `controls/drive.ts`: the vehicles
  (arcade: wheel heights → pitch/roll, 4 wheels or the bike's 2, which leans by v·ω/g instead; bumper tests across
  the leading end every ≤ 0.6 m, and points along the sides that only count if they were clear before the step, so a
  long bus can't cut a corner yet never sticks; R or water → nearest road; `Car(scene, camera, world, input, canvas,
  weather.levels)`). Speeds are m/s, `kmh` = |speed| × 3.6, and the position moves by speed × dt in world metres:
  measured flat out on Andrássy út, distance / integrated speedometer = 1.0000 (main.ts clamps dt to 0.1 s, so only
  below 10 fps does the world run slow). The wheels turn at most 0.42 of the rim's symmetry (`Model.period`) a frame,
  past which the wagon-wheel effect made them seem still or turning backwards at 50-90 km/h; `Model.blur`, discs over
  the rims sharing the wheels' instance matrices, fades in instead. `controls/chase.ts`: the chase camera (it owns
  `camera.fov` in drive mode): orbits round a pivot at the look height, `yaw` (positive: the camera to the vehicle's
  left) and `pitch` added to the spec's elevation, from a mouse drag on the canvas, a touch drag on the canvas or a
  `.label` (not the stick, pedals or buttons: their pointerdown targets differ) or the right stick (the left one
  steers); 1.5 s after the last input it eases back (faster when moving). Its heading lags the vehicle's; speed adds
  `feel.fov` degrees (6 more with the boost), comes 13 % closer and 22 % lower, `lag` hangs back with the acceleration,
  `feel.shake` near the top speed. A march from the pivot through `world.blocked` brings it in front of walls at once
  and lets it out slowly; `floor` keeps it 0.9 m over the ground. `controls/exhaust.ts`: puffs from `spec.exhaust`
  (the pipe's end and direction in the model's frame, `smoke` two-stroke / petrol / diesel), CPU-simulated in a pool
  (220, 90 on touch screens) and drawn as one instanced camera-facing quad set with a ShaderMaterial: no three.js
  lights, it finds the scene's hemisphere and directional lights once and sums them into `uLight`, plus the city's
  night glow and the tail lamps' red (`uTail`); the road's height per puff softens where it meets the road. `cold`
  is the month's (`WINTER`) or snow. `controls/streaks.ts`: streaks in a box that wraps round the camera (the rain's
  way), each the trail a still point leaves in a 0.09 s exposure, drawn as a quad 2 CSS px wide at its head (GL lines
  are 1 device pixel: invisible on a phone), faded towards the screen's middle; above 12 m/s. `controls/vehicles.ts`: `SPECS` (real
  sizes, axles, wheel radius, top speed, acceleration, turning radius, camera, `feel`, `exhaust`, `ground` 'road' |
  'bike' for where R puts it and where it starts: main.ts's `streetSpot`), `?vehicle=` > `voxelpest-vehicle` > taxi. `controls/models.ts` builds
  the five models with `controls/kit.ts` (vertex-coloured boxes, cylinders, tubes, extruded side outlines with arches
  cut by `archedBottom`, flat panels; `build()` merges per material, so a vehicle is 7-10 draw calls; shared
  materials in `mats()`, whose `lamp` / `tail` glow with the night, `tail` brighter while braking; wheels are one
  InstancedMesh, the rider's legs
  and cranks another (two-bone IK to the pedals); lettering on one CanvasTexture `Atlas` per vehicle, alpha-tested,
  the bus displays emissive: route `ROUTE` (7, to `DEST`), the destination beside it on the front and side). Decals and flat panels must stay inside the extrusion's flat face (outline minus the
  bevel), or they float over the rounded edge. Police lights are emissive only (a new light would recompile every
  program). `ui/vehicles.ts`: the picker (`#vehicles`, a `.seg` shown in drive mode under the switches; V / Shift+V,
  L lights, pad RB / LB / X via `poll()` in the drive frame).
- `engine/streets.ts` (`main.ts`'s `streetSpot(x, z, kind, R = 80)`, kind `'foot' | 'road' | 'bike'`; `findSpot` calls
  it): where to start. Per 0.5 m column, the footing: a run's top within 2 m of the ground byte with 1.8 m of headroom
  (under decks and arcades too; no roofs, no building insides, no water). A start: the surface within 1.2 m of the
  ground, a kind's surface by palette class (style.py's colours, rounded to 4 like Python: carriageway, cycle lane,
  track, soft ground, anything else hard is pavement), the same flat surface round it (±0.5 m on foot, ±1.5 m of road
  for a car), the nearest by distance plus a penalty (a walker prefers pavement to road by 4 m; anything overhead, an arcade or
  a deck, adds 25 m: the Parliament's riverside arcade was the nearest footing to its middle). Then it must lead
  out: a 4-way flood over footings (steps ≤ 0.6 m; cars: carriageway and tracks, ≤ 0.75 m) has to cover 5000 m²
  (cars 3000) or meet unloaded tiles 30 m away; Pest's inner courts are paved like pavements, at street level, and fail
  this (the Parliament's courts are 150-600 m²). Components are cached per call. Needs the finest tiles loaded round
  the point (`groundLoaded`); `setMode` tries 200 m if nothing turns up within the first radius (the river).
- `controls/orbit.ts`: OrbitControls for the mouse only (`ctl.touches` are null); touch is its own: pointer events on
  the window (so a drag may start on a `.label` or `#sq-pin`, which have `touch-action: none`), applied once a frame in
  `update()`. One finger: the ground-plane point (the pivot's height) under the finger stays under it, a flick glides
  (`glide`); two fingers: classified once they move 8 px, `tilt` (both vertical, same way, barely spreading) or
  `free` (zoom by the spread and turn by the angle round the point between them, then carry that point under the
  fingers' centre); double-tap zooms in, a two-finger tap out (`flyTo(..., arc = false)`). `bounds` keeps the pivot
  within 400 m of the map, for every input. Limits are OrbitControls' (distance 8-9000 m, polar ≤ 0.49π).
- `controls/input.ts`: keys, touch sticks and the Gamepad API (`poll()` once a frame, `pressed(b)` for a button's
  edge, `move()` for keys / touch stick / left stick together; `PAD` names the standard layout's buttons). Space and the
  arrows never reach the page (no scrolling, and Space after clicking a button jumps rather than pressing it again),
  except Space on a button reached with Tab (`:focus-visible`). `mute()` hides the controller from everything after it
  in this frame (sticks, triggers, buttons) without a held button counting as a new press once it ends. main.ts's
  `padButtons()` handles View (mode) and Menu (the menu); while the menu or the help box is open they get the pad and
  then mute it. The D-pad does nothing outside the menu.
- `ui/menu.ts` (`Menu`, the `#app-menu` dialog, website and desktop app alike): Resume, Places and Time & weather
  (submenus), SideQuest Bar, Help (the tutorial), Full screen (`ui/fullscreen.ts`'s API where `#fs-btn` shows, the
  bridge's in the app), Quit (app only). The pad's Menu button opens and closes it; Esc opens it only in the desktop
  app (a capture listener: not when a card or dialog is open or the pointer is locked), and goes back or closes it
  everywhere (keydown default prevented, so a submenu's Esc doesn't close the dialog). D-pad or left stick ▲▼ (held:
  380 ms, then every 110 ms; a direction held across a page change waits to be let go), A or ▶ opens / chooses, B or
  ◀ goes back, LB / RB jump 8; mouse hover focuses, the ◀ ▶ glyphs of a row step. Time & weather is built from
  main.ts's `timeRows` (`MenuRow`: label, value, `step(d)`, `press()`, `on()` for a switch): a new row is one entry.
  A website full screen from the pad's A is refused by browsers (no user activation): a note says so in the menu.
- Mode switches: from the map, walk and drive start on the street nearest to the point the map looks at (`mapStart`;
  from more than 1.5 km out, at the bar: `atBar(m)`); between walk and drive the position is kept (`here()`); a place
  chosen while walking or driving goes in front of the view (`towards`), the Parliament and Kossuth tér to `meta.spawn` (the square by the flag, facing the Parliament; also the Minecraft spawn).
  `camera.updateMatrixWorld()` runs before labels and the pin are projected (they shook while the map turned: they
  used the previous frame's matrices whenever `tiles.update` skipped its own update).
- `i18n.ts`: EN/HU strings; `?lang=` > localStorage > `navigator.languages`. Place names: OSM `name` (Hungarian)
  vs `name:en`. The loading screen's inline script repeats the detection and its three HU words (it runs first).
- **Loading screen** (`index.html`, inline CSS and script so it shows before the bundle): a 64 × 26 block skyline
  (`ART`) drawn on a canvas block by block (placed blocks baked to an offscreen canvas), paced in time rather than
  frames (1.5 s for the whole skyline at most, 0.45 s for the rest once done: SwiftShader's 2 s frames once held the
  fade back for a minute). `window.bvLoader.progress(p, text)` from main.ts: 0.12 code running, 0.2 meta.json in,
  then 0.2 + 0.8 × meshed / (meshed + loading) (`tiles.meshed` counts every tile meshed); `done(then)` once
  `__ready`, finishes the skyline, fades, removes itself and calls `then` (the tutorial); `fail(text)` if meta.json or
  WebGL fails.
- **Full screen on phones**: `viewport-fit=cover`; `body` fixed at `100dvh` (fill-available before that), no
  scroll, `touch-action: manipulation`, `gesturestart` prevented (iOS ignores user-scalable=no). The renderer is sized
  from `#app` (ResizeObserver; `setSize(w, h, false)`, the canvas is 100 % by CSS), and the labels, the pin and the
  LOD use those `vw, vh`, not `innerWidth/innerHeight`. Every fixed element adds `--sat/--sar/--sab/--sal` (from
  `env(safe-area-inset-*)` on `:root`; a test can set them on `<html>` to emulate a notch). Phones and landscape
  phones (`max-width: 700px, max-height: 500px`) get one bottom row: the bar shrink-wraps, Places beside it. On touch
  the speedometer sits above the pedals, and in landscape (`max-height: 500px`) the stick and pedals sit lower, clear
  of the overlays at the top; there everything at the bottom sits `--by` from the edge (beside the home indicator), the
  vehicle picker (a child of `#switches`, fixed under it elsewhere) joins the top row between the modes and the language,
  and the speed is in the middle at the bottom. The title and the switches stay on one row (nowrap; smaller under 400 px), with the bar's
  card (`#promo`, SideQuest Bar first, then the Minecraft card) right under the title. The bottom bar is a little more
  compact with a fine pointer at desktop sizes (`#time-card`'s offsets follow its padding); under 480 px the Names
  toggle shows only its icon.
- `ui/fullscreen.ts`: `#fs-btn` at the bar's right end (Fullscreen API or webkit's; the icon follows
  `fullscreenchange`, Esc included). Hidden without the API (iPhone Safari) and in the home-screen app;
  `fullscreenButton()` returns `{ on, toggle }` for the menu then, else null.
- `ui/locate.ts` (touch only, map mode): `#locate` over Places calls `geolocation.getCurrentPosition` when pressed,
  never before; `geo.ts` (`wgsToGrid`, a quadratic in lon/lat fitted to pyproj's EPSG:4326 -> 23700 turned by THETA by
  `scripts/geo_fit.py`, under 1 mm off; rerun it if `aoi.py` changes) puts it on the grid; inside the map a `#me-pin`
  dot and a translucent accuracy disc, and the map flies over; tapping the dot walks from the nearest street. Toasts
  for outside the map, denied and failed. Test with Playwright's `context.setGeolocation` and
  `grantPermissions(['geolocation'])`.
- `ui/time.ts`: the date and time card behind `#time-btn` (`data-w`: the weather's icon, sun or moon by the sun's
  height when clear; `#time-date` when the date isn't today, hidden under 480 px; then the time). `#live` in the card's
  head is an `aria-pressed` pill (red dot when on). `#date` and `#hour` are `role="slider"` divs styled as a `.seg`
  whose thumb is the pressed button with the value on it (`slide()`: pointer and keys for both; `--f` the fraction,
  ticks at `--d` / `--h`; the same calc in CSS and in `slide()`; a tick the thumb covers, or nearly, gets `.hid`).
  The date's ticks are month initials (`T().months`) mid-month, its thumb a leaf in `treeColour` (a twig when the
  city's trees are bare), its strip the trees through the year (`setCity` with phenology's city dates); keys ±1 day,
  Shift ±7, PageUp/Down a month, Home/End. The hour's strip is that day's daylight (`daylight(day)` from `sunAt`);
  arrows ±15 min (stopPropagation, or they fly the map), Shift/PageUp ±1 h, Home/End. `#weather` is a four-button
  `.seg` (icon over name, `data-w`); `offerSnow` disables Snow on dates it can't fall. Closes on a pointerdown outside
  or Esc; `peek()` shows it for 1.6 s (unused since the D-pad's keys went into the menu).
- `pwa.ts` (website only, not the desktop app): registers `public/sw.js` in production builds (the page and hashed bundles for a quick or offline start; never `data/`) and shows `#install-btn` in the About box when the browser fires `beforeinstallprompt`. `manifest.webmanifest`: display fullscreen, the desktop app's icon (`desktop/icons/icon.png` resized to `icon-512/192/180.png`; `favicon-16/32/48.png` and `favicon.ico` are the same picture with rounded corners). `_headers` keeps `sw.js` uncached. Bump `CACHE` in sw.js if the shell's caching rules change.
- `analytics.ts`: Umami, off unless `VITE_UMAMI_URL` and `VITE_UMAMI_ID` are set at build time (`UMAMI_URL`, `UMAMI_ID` in web.env through ./bv site and publish_web.sh; the dev server only with `UMAMI_DEV=1`). `initAnalytics()` adds Umami's script (no query string, no hash, Do Not Track respected) once the map is ready; `track(name, data)` / `trackSoon` (sliders: the last value after 2.5 s) send events: start, mode, vehicle, place, bar (flying there), bar-site (the card's link), time, date, weather, live, names, lang, help, menu, fullscreen, controller, minecraft, locate (the outcome only). `clean()` drops any value that isn't a short word, a whole number up to 1000 or a boolean, so no coordinate can be sent; never pass positions to it anyway.
- **Vehicles at night**: `kit.lampLit(lamps)` patches the vehicles' materials to add the city's lamp-pool texture (`makeMaterial().lamps`) to what they give back, as on the voxels (no lights: one would light and recompile the whole city); `underShadow` in models.ts is a soft dark patch under each vehicle (the sun's shadow map is coarse and there is none at night). The Bubi's rider is modelled after the mayor (glasses, navy jacket, white shirt).
- **Phones' memory** (iOS kills a page that holds too much: random reloads, then "a problem repeatedly occurred"): tiles.ts drops each geometry's arrays once uploaded (`onUpload`; they doubled the map's memory, so nothing may read a tile's attributes later), counts `bytes` (48 per quad) and on touch screens keeps them under `budget` (160 MB; the overview alone is 95): over it, tiles nobody asked for this pass go at once and `tight` scales `err` up until it fits, easing back under 85 %. Two mesher workers on touch, the lamp texture at 4 m per texel. Measure with `__three.tiles.bytes` / `.tight` per view.
- **Version**: the about box shows `v` + the version (`#version`): `web/package.json`'s on the website (vite.config.js defines `__APP_VERSION__`), `desktop/package.json`'s in the app (`app.getVersion()` over the bridge's `version()`; `appVersion()` in ui/desktop.ts). Bump both together.
- **Bar and help (Nov 2026)**: the bottom bar always names the data sources (`#credits`, two lines; hidden on phones) and has no help line; the help box has three tabs (map, on foot, vehicles: `Tutorial.show(tab)`, the walk and drive tabs list the `helpWalk` / `helpDrive` family split at ` · `), `first(tab)` opens a mode's tab on its first use (`voxelpest-tutorial-walk` / `-drive`), a pad's D-pad ◀▶ or LB / RB change tabs. `#fs-btn` sits beside the language switch. main.ts's `rescue()`: under `FELL` (6 m below the base) a walker goes back to the street nearest to where it last stood, a vehicle through `car.onReset`.
- `ui/tutorial.ts`: a `<dialog>` (showModal: Esc and the backdrop close it); tiles of a city patch (`.mw`, a CSS
  transform between `--a` and `--b` from one `tv-go` keyframes) under fingers / a mouse / keycaps / a controller (SVG).
  The set follows `isTouch()` and `input.pad.on`. Closing stores `voxelpest-tutorial=1` (in `close()`, and on
  the dialog's `close` event for Esc); `?tutorial=1` forces it,
  `?tutorial=0` and `?ui=0` skip it, and it only opens by itself when starting in map mode. A or B on a pad closes it
  (its button shows the A). Under the tiles, walking and driving in a line each (the `helpWalk` / `helpDrive` family
  of strings, also the website's help line; the `helpPad*` ones without "Controller:" and "View: mode", which ui.ts
  adds for the line); the footer's text follows the input and the desktop app (Esc / Menu: menu).
- `Ui.tiles(loading, meshed)`: `body.tiles-loading` (the `#status` chip at the bottom in the middle, over the bar by its
  height `--bar-h` from a ResizeObserver, with the `#tilebar` line along its edge) while `lod.loading > 0`,
  off after 400 ms idle; the bar is the share of this batch meshed. `?fps=1`: `ui/stats.ts` (fps, mean and worst
  frame ms, `renderer.info` draws and triangles, tiles), top right under the switches, or under the bar's card on
  phones narrower than 480 px.
- `ui/promo.ts`: the SideQuest Bar card and pin, and the "Play in Minecraft" card behind a feature flag
  (`minecraftEnabled()`: `?minecraft=1/0`, else `VITE_MINECRAFT`; off by default, and then no status requests). Its
  count from `VITE_MC_STATUS`, `api/minecraft` in dev (Vite's proxy to a local server), then api.mcstatus.io.
  `?promo=0` hides the overlays, `?ui=0` everything.
- Hosting (Cloudflare Pages): `public/404.html` must stay (without it Pages answers a missing tile with
  `index.html` and a 200, which the worker can't read; a 404 is an empty tile), `public/_headers` sets the caching,
  `vite.config.js` drops the map's tarball parts from `dist`. Limits: 20 000 files, 25 MiB each (the map is ~8 750).
  **Tile caching**: tile URLs are the same for every map, and map.side-quest.bar's Cloudflare zone turned Pages'
  `max-age=0` into 4 hours for `.bin` (its Browser Cache TTL), so a phone kept the old map's tiles under the new
  meta.json. The build (`versionTiles` in vite.config.js) writes a hash of every tile's path and bytes into dist's
  `meta.json` as `tiles.v`; tiles.ts asks for `...bin?v=<hash>`, `_headers` caches `/data/tiles/*` for a year, and
  `loadMeta` fetches with `cache: 'no-cache'`. `bun run dev` has no `v` (public/ is untouched). Check the live headers
  with `curl -sI` on both `voxelpest.pages.dev` and the custom domain: the zone only touches the latter.
- `window.__three` exposes `lod` (loading/shown/update), `render()`, `setMode`, `goBar`, `map` (MapControls), `tutorial`, `menu`,
  `weather`, `live`, `setHour`, `setDay(day of year)`, `day()`, `season` (the shader's season uniforms), `setWeather(kind, now)`, `setLive`, `car` (`setKind`, `update(dt)`, `chase.yaw/pitch`),
  `vehicles` (the picker) for `tools/shot.mjs` and tests (mock Open-Meteo with `page.route('https://api.open-meteo.com/**')`);
  `window.__ready` turns true once the coarse map is in (the loading screen then fades).
- Testing touch: Playwright with `hasTouch`/`isMobile` (Chromium then matches `pointer: coarse`) and CDP
  `Input.dispatchTouchEvent` with two `touchPoints` for pinch / twist / tilt. Drive mode: stop the loop
  (`renderer.setAnimationLoop(null)`) and step `car.update(1 / 30)` by hand with keys in `car.input.down`; a controller
  is an init script whose `navigator.getGamepads` returns a fake standard pad (`input.poll()` reads it). Vite keeps its dependency cache in
  `node_modules/.vite`: in a worktree whose node_modules is a symlink, run it with a config whose `cacheDir` is
  elsewhere, or it rewrites the main tree's cache.

## Desktop app (desktop/)

Electron (45, Chromium 156) for WebGPU: Chromium has it on Linux, on Vulkan; WebKitGTK (Tauri, the first version,
Nov 2026) has none. Linux AppImage only, by electron-builder (config in `desktop/package.json`). `./bv desktop`: runs
`./bv site` (same env as publish-web), `bun test` (`site.test.mjs`, written for node:test, which Bun runs), `electron-builder`, then
copies `desktop/out/voxelpest-VERSION-x86_64.AppImage` to `build/` (~20 s). `./bv desktop dev [ARG=VALUE...]` loads
the dev server in a window (`VOXELPEST_DEV_URL`; reuses a Vite already on 5173, else starts `./bv web` in a session
of its own and stops it after), F12 for devtools. `cd desktop && bun run start ARGS` runs the release path from the
source tree (`../web/dist`). Files: `main.mjs` (main process), `preload.cjs` (the bridge), `site.mjs` (plain logic,
tested). Electron's binary comes on first use (`electron --version` fetches it).

- **Serving**: `web/dist` is an extra resource (`resources/web`, outside the asar), served from disk by the app's own
  `voxelpest://` scheme (`protocol.handle`, privileged as standard + secure + fetch + CORS: an origin of its own,
  module workers, a secure context for WebGPU). A missing file is a real 404 (the worker reads it as an empty tile);
  `resolve` decodes, then refuses `..`, `\` and NUL.
- **The bridge**: `preload.cjs` (sandboxed, context-isolated) exposes `window.voxelpestDesktop` (`quit()`,
  `fullscreen(on?)`) over `ipcMain.handle`, which only answers frames on the app's origin (or the dev URL).
  `web/src/ui/desktop.ts` reads it; with it the menu (`ui/menu.ts`, the website's too) adds Full screen and Quit: Esc (a capture listener: not when a card or
  dialog is open or the pointer is locked, so that Esc keeps closing those first) and the pad's Menu button open it;
  F11 toggles full screen. Keys inside it stop at the dialog, and main.ts mutes the pad while it is open. In the
  app the bottom bar has no help line (`#help`, the website's) and no full-screen button (`#fs-btn`, the website's
  Fullscreen API one) but the data sources (`#credits`); the help box (`ui/tutorial.ts`) carries the walk and drive
  help instead. `Menu.setApplicationMenu(null)`: no menu bar and none of its shortcuts (reload, zoom, devtools).
- **Arguments**: `key=value` ones become the page's query string; `--` ones are Chromium's/Electron's
  (`--remote-debugging-port=9333`, `--ozone-platform=x11`). Kiosk ones are read by both sides (`parseArgs` in
  site.mjs, `fullscreenAlways` / `noLinks` in desktop.ts): `fullscreen=always` (no menu item, no F11, the
  `fullscreen` handler won't leave it, and `leave-full-screen` puts it back) and `nolink=true` (`stripLinks`: every
  `a[href]` off the page's origin loses its href, kept so by a MutationObserver as the page rewrites them; the app
  opens nothing for a blocked navigation or `window.open`). Quit stays in the menu.
- **Links** (`will-navigate`, `setWindowOpenHandler`; http, https, mailto, minecraft only) go to `xdg-open` in
  `linkEnv`'s environment: the AppImage's (`APPDIR` and every variable pointing into the mount, `OWD` as the
  directory) and Chromium's own (`CHROME_DESKTOP`, `NO_AT_BRIDGE`, `FC_FONTATIONS`, `EGL_PLATFORM`,
  `ORIGINAL_XDG_CURRENT_DESKTOP`) undone.
- **WebGPU**: `--enable-unsafe-webgpu` only. Not `--enable-features=Vulkan` as often quoted: that is Vulkan for
  compositing, which native Wayland refuses ("'--ozone-platform=wayland' is not compatible with Vulkan") and the GPU
  process crashed in a loop. On the hybrid laptop: `requestAdapter` gives the Intel Iris Xe (gen-12lp) for
  low-power, the RTX 3070 Ti (ampere) for high-performance; WebGL (ANGLE, GL ES) runs on the NVIDIA.
- **Wayland**: native by default (Electron's `--ozone-platform-hint=auto`). In the nested headless KWin below,
  Chromium's frames stall (rAF fires a few times, then never; tiles stop) unless that KWin composites on the NVIDIA
  (`__EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json` for both) or the app runs on
  XWayland (`--ozone-platform=x11`, with `kwin_wayland --xwayland`): both 60 fps. In software (no `KWIN_COMPOSE=O2`)
  it always stalls. A test compositor's limit, most likely; if the app ever stays on the loading screen on a real
  desktop, `--ozone-platform=x11` is the way round.
- **Testing**: off the user's screen, in a nested headless KWin, always focused: `KWIN_COMPOSE=O2 dbus-run-session
  -- kwin_wayland --virtual --width 1440 --height 900 --socket voxeltest --exit-with-session script.sh` (the script
  runs the app with `--remote-debugging-port=9333` and a CDP client: `Runtime.evaluate`, `Input.dispatchKeyEvent`
  for trusted Esc and F11, `Page.captureScreenshot` with the overlays). A window behind the lock screen (or fully
  covered) is suspended on KDE Wayland: no frames, no tiles. Gamepads: Chromium and WebKit give input only to the
  focused window, after a first button press. A virtual pad tests the real path: python-evdev's `UInput` with the
  Xbox controller's ids (045e:0b12, USB), keys and axes (D-pad: ABS_HAT0X/Y); /dev/uinput and the real pad are the
  user's only while the session is active (logind's uaccess), so not while it is locked.

## Gotchas learned the hard way

- **Bridges in the surface model.** FABDEM removes buildings and trees, not bridges, and the DSM sees a deck over land
  as open ground: both lifted the streets under the bridgeheads to the deck ("merged" over/underpasses). The ground
  step now masks the bridges (`br8`) and fills under them from around. If a bridgehead looks merged again, check
  that first (`scratchpad`-style tools: a vertical slice of a bench window along the bridge, a height map of the
  first free voxel per column).
- **A hand-built deck under the ground** shows as steps, loose balustrades and trenches: voxelize.py digs the ways
  crossing it down for headroom and bares the buried deck. Margaret's Pest bank pier was set from the water while
  Jászai Mari tér stands 2.5 m higher (painting the deck onto the ground hid it). Print the voxel runs per column along
  the axis: the deck must be the top run everywhere past the bank.
- **A dropped outline is free ground to everything before the landmarks**: Sentinel-2 green (a grey-green roof reads
  as a courtyard garden and gets trees), tree placement (one more random draw shifts every later tree), street lamps
  and furniture, and the ground model's open ground (`cov`; the roof in the surface model lifts FABDEM round it). The
  Rákóczi hall did all of these. `Plan.ground_cover` (a module's `KEEP_GROUND`) feeds voxelize.py's `held` mask, which
  stands in for `bmask` there; only the Rákóczi hall is in it so far.
- **OSM parts inside a replaced outline** keep drawing unless dropped: Keleti's head facade is a separate 31 m part
  that hid the hand-built gable; Nyugati's entrance canopy (`building=roof`) hid the glass front. `Plan` drops the
  parts inside the Opera's and the baths' outlines; the stations list theirs in `landmarks_city.DROP`.

- **Hashes in the shader**: `hash3`'s `fract(sin(dot(...)))` of voxel coordinates (thousands of voxels) came out
  exactly 0 for about one voxel in six in SwiftShader, so a "hash > leaf" test kept those leaves in January. Decisions
  that must be uniform (which leaves drop, which turn first, fallen leaves) use `ihash` (integer hashing, material.ts);
  the older `hash3` uses (colour jitter, window lights) are left as they were.
- **Memory**: the full build peaks near 5 GB; a container with 7 GB OOM-kills it if headless Chromium (SwiftShader)
  runs at the same time. Don't render screenshots during a full build.
- Screenshots in a cloud container run in SwiftShader: minutes each. Use `shadow=1024` and a small viewport.
  `tools/shot.mjs` renders synchronously before reading the canvas. Every new three.js program (and a change in the
  light count, the sun setting or rising, recompiles them all) holds SwiftShader's GPU process for a minute or more
  when other jobs load the CPU: `page.screenshot` and even `page.goto` then time out. Keep browser tests in daylight
  unless night is the point, and wait for two animation frames before a screenshot. Playwright from Node: `require('playwright')` in a
  `.cjs` file (an ESM import doesn't find the global install).
- **Floating buildings on slopes** came from the lower-wall band: `bl` (a part's lower wall) defaulted to the median
  ground, and its colour is 0 for outlines, so the band from the downhill ground to the median was empty. `bl` now
  equals the bottom unless a part has a real lower wall. `data/debug` gap checks: count columns with a building voxel
  over an empty gap above the ground (only cornices should remain).
- **Lower quays**: only Pest's trams seed the low quay (line 2 runs down there); Buda's run on the upper quay. Seeding
  them sank Szent Gellért tér and left Liberty Bridge's Buda end in a dip.
- To check tile data independently of the viewer, decode a tile in Python (counts / ground / runs as in
  `engine/mesher.worker.ts`: offsets are the cumulative counts, runs are (z0, length, palette) in cells of s voxels).
- **Aerial references**: Esri's World Imagery tiles (`server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/
  MapServer/tile/{z}/{y}/{x}`) answer from the container; resampled onto the grid (x right, y down) they line up with a
  bench window's top view (colour of each column's top voxel). For reference only: nothing derived from them goes
  into the data, except hand decisions (which Parliament parts are copper, where the Gellért's terraces are). Tall
  things lean in them: about (-0.063, -0.35) grid metres per metre of height round the centre (from the Parliament's
  dome), so a roof's outline must be shifted by its height before its colour is read.
- Reference photos: Wikimedia (commons API, upload.wikimedia.org) answers 429 from shared IPs. The Openverse API
  (`api.openverse.org/v1/images/?q=...`) with Flickr image URLs worked. Credits are in `docs/landmarks.md`.
- Hungarian Wikipedia pages fail through WebFetch; the Chain Bridge page worked, the others didn't.
- Wikimedia and Flickr image downloads can both answer 429. Mapillary's graph API (`graph.mapillary.com/images?bbox=`,
  then `/{id}?fields=thumb_2048_url,computed_compass_angle`) gives street-level photos with the token; panoramas are
  equirectangular with the compass angle at the centre column, so crop round the bearing to the subject.
- Sentinel-2 cloudless: EOX's tiles are JPEG at zoom 15 (~3 m pixels, 10 m real). A real orthophoto would plug into
  the same `s2` slot in prep.py (any RGB raster with a CRS).
- **After changing `aoi.py`, run `fetch_all.sh` again before voxelizing.** Downloads are cached, but the per-AOI
  filters (Átló heights, the OSM cut, Wikidata) must rerun. A stale `atlo_heights.json` once left the new areas'
  buildings at default heights.
- Builds are memory-bound: the 1 m rasters plus 0.5 m road colours fit in 7 GB. Don't make more global 0.5 m arrays;
  do 0.5 m work per window in `build()`.

## State and next steps

Done:
- 0.5 m pipeline and viewer.
- Thirty-nine landmarks: Parliament (with Kossuth tér's monuments and flag in landmarks_kossuth.py), Chain / Liberty / Elisabeth / Margaret / Petőfi bridges, Fisherman's Bastion,
  Matthias Church, Basilica (with its west front), Buda Castle dome, Liberty Statue, Heroes' Square, Great Market
  Hall, Dohány Street Synagogue, Puskás Aréna; in landmarks_city.py the Opera, Keleti and Nyugati stations, the
  Széchenyi Baths, the Museum of Ethnography, the Zoo (Great Rock, Elephant House, gate), the Bálna, the Ferencváros
  church, the Budapest Eye and the Soviet War Memorial; in landmarks_more.py the Gellért Hotel and Baths, BME
  Building K, the National Museum, the Kálvin tér skybridge and the Danube boats. Each in its own module (Nov 2026): Matthias Church
  (rebuilt whole), the Hilton, the Citadella with its flag (and the Liberty Statue turned to face down the east cut),
  the Erkel Theatre, the Rákóczi tér market hall, the Corvin Palace and the Europeum on Blaha Lujza tér, the WestEnd
  City Center, and SideQuest Bar inside and out.
- Ported from warsaw-vibe-voxel (Nov 2026): no lane lines in junctions, granite for paving-stone carriageways
  (`road_paving`), service roads taking their square's surface, `area:highway` carriageway values, the centreline check
  (`carriageway_cut` in report.json); pedestrian underpasses (`underpasses`, `carve_underpasses` in voxelize.py:
  footways at layer -1 outside buildings, floor 4 m under the smoothed street, stairs `level=-1;0` as open stairwells
  with a parapet); church windows and statues (landmarks_statues.py).
- City pass against street photos (Nov 2026, Mapillary poses in the scratchpad's `refs/street/poses.jsonl` style:
  x, y, yaw on the grid, shot with walk mode at the same spot): lighter facade palette (`WALLS`), lighter grey posts,
  street trees from Sentinel-2 ("street trees from Sentinel-2" in the log), Anker-ház's ochre and domed towers and
  Vörösmarty n°1's pale glass (overrides.json). Monuments clear the trees round them (`Scene.clear`).
- Bridge ends on two levels: bridges left out of the ground model, lower quays kept low under the bridgeheads, roads
  under hand-built decks dug for headroom, tunnels and covered ways near the river carved (docs/landmarks.md).
- Pink: violet and magenta building colours become a dusty rose (`style.tame`), satellite roof colours that drift
  pink become terracotta; flowerbeds are mostly foliage with two hashed bloom colours.
- Map extended to Széll Kálmán tér, the whole Városliget and the Puskás Aréna; FABDEM ground (Castle Hill fixed);
  street widths from lanes/parking within the street canyon; Sentinel-2 roof colours and green courtyards; Mapillary
  street furniture.
- Views: overview, parliament, kossuth, castle, chainbridge, chainarch, basilica, gellert, heroes, fishermans, matthias,
  liberty, elisabeth, market, rakoczi, synagogue, statue, citadella, varosliget, szechenyi, puskas, szell, margaret,
  petofi, opera, erkel, keleti, nyugati, westend, ethnography, balna, zoo, eye, gellerthotel, bme, museum, a38, hilton,
  blaha, sidequest, sidequest_inside (each with `label_hu`; `walk: true` starts walk mode where the view stands).
- The viewer rewritten as this project's own code (2026-11): map / walk / drive, time of day with the real sun, snow,
  EN/HU. Minecraft `/bar` teleports to the bar's door (`bar` landmark from `meta.sidequest.door`).
- Seasons (Nov 2026, after warsaw-vibe-voxel): a date slider in the time card (live: Budapest's date), the sun on
  that date, the trees through the year per class (phenology.py: Warsaw's DWD/iNaturalist table moved to Budapest by
  thermal time; plane trees added), fallen leaves, lawns by month, snow only around dates it can fall (climate.py).
  The trees' classes come from the tree build's `foliage.bin` (FOLIAGE-CONTRACT); tested on a provisional one made
  from the tiles' leaf columns.
- Desktop app (Nov 2026): the viewer as a Linux AppImage (`./bv desktop`), first in Tauri, then in Electron for
  WebGPU; full screen, with a menu (Esc, the pad's Menu button) to leave full screen, go to the bar or quit, and kiosk
  arguments. Electron tested in a nested KWin (WebGPU adapters, menu, kiosk, links, the AppImage); its controller
  path and native Wayland on the real desktop not yet (see Desktop app).
- Minecraft server (mc.side-quest.bar): converter, protected Paper server with landmark teleports and flight, Java and
  Bedrock, published on its own (`./bv publish-minecraft`), separately from the viewer (`./bv publish-web`); the
  viewer's SideQuest Bar card and the Minecraft card (feature flag, off by default). Tested locally end to end (start.sh, plugin, map swap on update, sync to a local target);
  not yet run on the real server.

Known weak spots, roughly by how much they show:

1. **Ground** away from OSM's survey points can be a few metres off (FABDEM is 30 m). Better DEM data (Lechner DFM,
   or the city's 2016 survey) would fix it.
2. **Parliament.** The courts' facades and the interior halls aren't drawn; the statues are simple figures.
3. **Synagogue**: its facade details and rose window are missing.
4. **Street level**: posts (lamps, signs) are a 0.5 m voxel thick, so they look chunky up close.
5. **Approximations**: the Bastion's towers are approximate, the Matthias roofs' Zsolnay patterns are coarser than
   the tiles (V rows, diamonds and rosettes at 0.5 m), and the bridges' sculptures are simple figures.
6. **Downsampling**: for levels ≥ 4, window glass gives way to wall (`low_ids` in `tiles.downsample`), so distant
   landmarks lose their painted windows (the shader's procedural windows on plain walls don't depend on the level).
7. **Walk/drive** collide only with the finest tiles' columns; a tile still loading stops you rather than letting you
   fall.

Workflow for a landmark:
1. Edit its builder.
2. `BENCH=<spot>`, then `preview.py`.
3. Run the full build (~28 min).
4. Look at it with `./bv web`, `?view=...`.
5. Compare with the photos linked in `docs/landmarks.md`.
