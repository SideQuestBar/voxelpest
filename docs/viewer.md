# The viewer (`web/`)

The web viewer in detail: controls, phones and controllers, the vehicles, time, seasons and weather, URL parameters
and how the code is laid out. Setup is in the [README](../README.md); publishing in [publishing.md](publishing.md).

## Modes and controls

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


## Vehicles

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

## Time, seasons and weather

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

## URL parameters

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

## SideQuest Bar and the Minecraft card

The viewer shows a card for **SideQuest Bar**, who made the map, with a pin over the bar on Klauzál utca. The bar is
built inside and out, from its owner's photos and its evacuation plan: its door is open, so you can walk in, look
round the room, climb the steel stair to the mezzanine and its foosball table, and find the toilets
(`view=sidequest_inside` starts inside, on the map or with `mode=walk` on foot; `/lm sidequest_inside` in Minecraft). The **Play
in Minecraft** card (the number of players online, and how to join) is behind a feature flag, off by default:
`MINECRAFT=true` in web.env turns it on for the published site (`VITE_MINECRAFT` at build time), and `?minecraft=1`
or `?minecraft=0` in the URL overrides it. Its count comes from `MC_STATUS_URL` if you publish the plugin's status
endpoint, else from api.mcstatus.io.

## How it works

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
