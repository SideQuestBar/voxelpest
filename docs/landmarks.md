# Landmarks built by hand

`scripts/landmarks.py` and the `scripts/landmarks_*.py` modules draw thirty-nine landmarks at 0.5 m from measured dimensions and reference photos, on
the positions, outlines and heights OSM gives. This page lists what each one is made of, the numbers it uses, and where
they come from. The photos are linked, not copied: their licences vary.

Every landmark is a list of solids evaluated voxel by voxel:

- **Boxes**, tapered boxes and pitched roofs.
- **Lathes**: a profile turned about an axis, round or as a regular n-gon. These make drums, domes, spires, onion
  domes and columns.
- **Arches**, round or pointed. They are carved through walls or painted on them as windows.
- **Capsules**: limbs, struts and short bars.
- **Slabs** that follow a road's rise, for decks, girders and railings.
- **OSM polygons**, extruded.
- **Fields**: shapes that follow an outline rather than a frame (a stadium bowl, a facade that leans along a curve),
  drawn from distances to OSM rings precomputed on the 0.5 m grid.

Each solid fills, carves, paints only voxels of given colours (windows on a wall), or fills only empty voxels
(pilasters that must not cut into a neighbour). Chains, cables, hangers and truss members are lines of voxels.

## Parliament (Országház)

**Dimensions**: 268 × 123 m, 96 m to the top of the spire ([Wikipedia][parl-wiki]).

**OSM** maps it in 132 parts with heights. These are kept as they are:

- the wings, at their mapped heights;
- the two chamber halls, 48.5 m with mansard roofs.

**Roofs**, from aerial photos (Esri World Imagery, looked at for reference): OSM gives every part `#bb7063`. Each
part's outline was laid on the aerial, shifted by the image's lean at its roof height (tall roofs stand up to 25 m
off their footprint in it), and its colour read: 40 parts are green copper (the chambers' great roofs, the four end
pavilions, the strips along the courts), the rest red-brown tile. The ids are `PARL_COPPER` in landmarks.py.

**Replaced**:

- **The dome group.** The 16-sided drum (inradius 12.6 m, as OSM's 25.8 m dome outline) carries two tiers of
  windows, a gallery and 16 pinnacles. Against it lean 16 stepped buttresses (OSM maps them as 8.4 × 1.9 m boxes),
  each with a pinnacle. The pointed dome rises from 55 to 75.5 m in red panels between pale ribs, with a ring of
  dormers. On it sit the lantern (75-80 m) and an octagonal spire to 95.4 m with a gilded finial.
- **The two needle towers** on the river front either side of the dome: stone, not roofed. A square shaft to 52 m
  with tall belfry lancets and corner pinnacles, an octagonal lantern, and a crocketed needle to 72 m (OSM says 66 m;
  in a level photo from across the river their tips stand at 0.8 of the dome's height, about 71 m once the dome's
  distance behind them is allowed for).
- **The turrets.** Eighteen other parts with pyramidal roofs are rebuilt as Gothic turrets, each with a shaft,
  pointed belfry windows, four corner pinnacles and an octagonal spire, copper or tile as the aerial shows.

**Added to every other part**:

- a buttress strip every 4.2 m, with a pinnacle above the eaves;
- windows storey by storey, not a uniform grid: round-headed on the ground floor, tall pointed ones on the main
  floor, shorter pointed ones above, small square ones in the attic;
- on the river front, the ground floor's arcade: pointed arches 2.4 m deep between the buttresses;
- a small gable on the eaves every other bay.

**The main entrance** on Kossuth tér (in `landmarks_kossuth.py`): steps the width of the porch, three pointed arches
3.4 m wide carved 3 m into it, and two bronze lions on stone pedestals at the foot of the steps, 20 m apart (as the
aerial shows their pedestals).

**Photos**: [river front, night][p1], [centre][p2], [silhouette][p3], [river front, day][p4], [dome][p5],
[dusk][p6]; Flickr: laszlo-photo (CC BY) [from the Castle][p7], archer10 (CC BY-SA) [the river arcade and a needle
tower][p8], teofilo (CC BY) [a Kossuth tér facade][p9]; Mapillary (CC BY-SA 4.0) [the main entrance and its
lions][p10], [the facade from the square][p11].

## Kossuth tér

The square in front of the Parliament (`landmarks_kossuth.py`), on OSM's nodes for each monument; sizes estimated
from photos.

- **The national flag**: OSM's `man_made=flagpole`, 33 m. A tapering steel mast on a stone foot and a gilt ball;
  the flag 9 × 4.5 m in three bands, waving towards the south-east (Budapest's wind is mostly from the north-west).
- **The granite square** on the dome's axis between the lawns, from the steps out to the water basin: dark grey, as
  the aerial shows it against the pale paving round it.
- **Ferenc Rákóczi II** (János Pásztor, 1937), in the southern lawn: green bronze horseman on a red granite pedestal.
- **Gyula Andrássy** (György Zala, 1906, recast 2016), south of the Parliament by the river: dark bronze on a white
  marble pedestal with bronze groups round its foot.
- **István Tisza** (Zala, 1934, rebuilt 2014), north of the Parliament: a white pylon of two fluted piers with a
  sculpture group on top, the bronze figure before it between two bronze groups, on a broad plinth.
- **Lajos Kossuth** (János Horvay, 1927, rebuilt 2014): a long white wall, the figure groups of 1848 and 1849 before
  it, Kossuth on a tall pedestal in the middle.
- **Attila József** sitting on the embankment steps, looking at the Danube.
- No random trees in the formal flowerbeds: parks tagged `landuse=flowerbed` get none (voxelize.py); the trees OSM
  maps one by one stay.

**Photos**: Flickr: Old Fogey 1942 (CC BY-SA) [Rákóczi][ks1]; leonyaakov (CC BY-NC-SA) [Andrássy][ks2];
wallyg (CC BY-NC-ND) [the Kossuth memorial][ks3]; corno.fulgur75 (CC BY) [the Tisza memorial][ks4]; Mapillary
(CC BY-SA 4.0) [the flag][ks5], [Tisza][ks6], [Kossuth][ks7].

## Chain Bridge (Széchenyi lánchíd)

**Dimensions** ([hu.wikipedia][chain-wiki]):

- 380 m long; spans 88.7 + 202.6 + 88.7 m
- 14.8 m wide: a 6.4 m road and two 2.2 m footways
- OSM's pylon footprints are 202.6 m apart, which matches the main span

**Pylons**: on piers with pointed cutwaters, 10.9 × 31.9 m (OSM). Each tower is rusticated, with pilasters, a cornice
and a crown. The arch is 6.8 m wide, round-headed, with an archivolt, and the Hungarian coat of arms sits above it.
The towers end 30 m above the deck.

**Chains**: two a side, over the saddles and down into the anchorages 88.7 m beyond the pylons. A line of bulbs runs
along the top chain, lit at night as it is in reality. Hangers stand every 3.55 m.

**Deck**: lattice stiffening girders, cast-iron railings, and the footways passing round the pylons.

**Lions**: four reclining lions (Marschalkó, 1852) on pedestals at the abutments.

**Photos**: [pylon][c1], [from below][c2], [from the air at night][c3], [Pest pylon at night][c4].

## Liberty Bridge (Szabadság híd)

**Structure**: a cantilever truss, 333.6 m in spans of 79 + 175.6 + 79 m. OSM's pylons stand 175.6 m apart.

**Trusses**: the top chord rises to 15.5 m over the pylons, sags to 1.9 m at mid-span and runs down to the
abutments, with verticals every 5.5 m, diagonals, and bracing overhead where it is high enough.

**Portals**: an arched portal over each pier, carrying the coat of arms.

**Masts**: four slender masts, each topped by a bronze Turul with raised wings.

**Deck**: tram tracks down the middle, footways outside the trusses.

**Photos**: [from Gellért Hill side][l1], [portal and Turul][l2].

## Elisabeth Bridge (Erzsébet híd)

**Structure**: a white suspension bridge with a single 290 m span. The pylons are placed where the Danube meets each
bank under OSM's bridge outline. Each has two white legs 28 m above the deck.

**Cables**: the main cables run between the pylons with hangers every 6 m, and back-stays run down into the
bridgeheads.

**Deck**: 27.6 m wide, on the road's axis (a line fitted to OSM's bridge ways; the outline's rectangle takes in the
pylon platforms unevenly and ran 7 m off the road at the Buda end). Three lanes each way, the outer one a bus lane
behind a solid line, a double line in the middle, dashes between the others.

**Photos**: [pylon and cables][e1].

## Fisherman's Bastion (Halászbástya)

**Shape**: OSM's outline is the terrace. Along its outer edges is an arcaded wall: round arches every 3.2 m, a
crenellated top, and a walk at the level of the square by Matthias Church.

**Towers**: seven conical towers. Their positions were read off the outline's round bastions; the photos give their
proportions. The main one, by St Stephen's statue, has a 5 m radius, eight arched openings, four corner turrets and
dormers on its cone.

**Photos**: [stairs and main tower][f1], [from the river][f2], [a tower][f3].

## Matthias Church (Mátyás-templom)

**Sources**: the Budavári Nagyboldogasszony-templom as Frigyes Schulek rebuilt it in 1874–96. Hungarian Wikipedia
[hu-wiki][mt1] gives the Matthias tower 78.16 m from the church floor, 76.57 m from the pavement, and its balcony
(koszorúerkély) at 46.73 m, and lists Schulek's additions: the porch before the Mary portal, the St Stephen chapel
where the Garai chapel stood, the neo-Gothic chapels on the north aisle, the stone spire and balcony wreath of the
south tower, the Béla tower's helm with corner spirelets, the openwork gable between the towers, two sacristies, and
the wooden ridge turret (huszártorony). Péter Szablyár's *Sky-high* ([Our Budapest, 2007][mt2]): about 60 m long,
24.15 m wide inside, nave 11.4 m and aisles 6.6 m wide, vaults 16.8 m and 15.7 m high; the Béla tower ends at 36 m;
the Matthias tower has two square storeys and three octagonal ones, the fourth with King Matthias's arms of 1470.
Lilla Farbaky Deklava on Schulek's plaster model ([Periodica Polytechnica, 2014][mt3]) for the plan (polygonal main
apse, side sanctuaries, sacristies, the north chapel row). Infostart ([2008][mt4]): about 150 000 Zsolnay
pyrogranite tiles, two thirds glazed in colour.

**Drawn** whole in `landmarks_matthias.py` in place of OSM's 36 parts (all dropped; the outline stays in the
pipeline only for its base, which the Bastion's terrace uses, and is cleared above it). Everything is laid out on the
nave's axis (OSM's main part), u from the west front (−30.2) to the apse (30.6), v towards the square:

- **Hall**: 33.5 m of four bays (8.4 m) between walls at −13.3 and 13.0 (OSM), eaves 16.3 m, a corbel table, cornice
  and green copper gutter; the north side in the older, warmer stone, the south in Schulek's white limestone, on a
  grey plinth. Stepped buttresses with pinnacles between the bays; a three-light traceried window in each south bay
  (5–14.7 m). The fourth south bay has a gable with two lancets and a roundel, the south door under it, and the
  octagonal stair turret at its east corner, 3.5 m across: a stage of lancets above the eaves, gablets and pinnacles,
  a stone spire to 28 m and Matthias's raven (proportions from [the south side][mt8] and [from the south-east][mt23]).
- **Choir and apse**: 12.7 m wide, the apse half an octagon (inradius 6.3 m) with stepped buttresses at its corners
  that stop under the cornice (no pinnacles over the apse's eaves, [from the Bastion][mt24]), two tiers of windows,
  an iron cross at the end of the ridge.
- **Roofs** (eaves 16.3 m, from Mapillary photogrammetry of the south wall): the main roof over the nave and choir
  to a ridge at 25.5 m, hipped round the apse in eight facets; over each aisle bay a cross roof to 23 m, hipped at
  the wall (gabled in the fourth bays), its finial in iron. The north gable over the fourth bay rises from its own
  block. Zsolnay tiles: rows of V's in orange and yellow lined in turquoise, white and brown on the nave and the cross
  roofs, with rosette bands along the eaves and under the ridge, an orange crest and small dormer vents; on each apse
  facet a big diamond outlined in turquoise and yellow, the Árpád stripes (red and white) in the east one; small
  rosettes in white, turquoise, green and blue on brown on the side chapels' and the annexes' roofs.
- **Ridge turret**: dark slate, octagonal, a gilt ring at 28 m and a belfry stage with gilt pinnacles, its spire to
  40 m and a gilt cross to 42 m (photogrammetry), over the start of the choir.
- **Matthias tower** (76.6 m above the pavement): two square storeys (to 7.5 and 17.5 m) with diagonal buttresses
  that rise into pinnacle clusters at 25.5 m; three octagonal storeys (to 27.5, 37.5, 46.7 m), each with two-light
  lancets in blind arches under gablets and corner shafts; the balcony at 46.7 m on corbels with a pierced
  balustrade; the closed storey with four corner bays and gargoyles to 54.5 m; the open lantern of eight pointed
  arches under gablets with a ring of pinnacles to 61.3 m; the crocketed stone spire to 75 m, its knob and cross.
  The spire is stone, not tiled (photos). Storey heights measured on photos scaled by the balcony's 46.73 m.
- **West front**: the portal porch (to 9.2 m, copper coping) with a pointed doorway in two orders, the door and the
  tympanum; the rose window, 5 m across, its centre at 13.3 m; the cornice at 17.5 m; the openwork gable to 30.5 m
  with an arcade and five lancets, crockets and a cross, pinnacles at its feet.
- **Béla tower** (north-west): to 21 m, the older stone below 16.6 m, corner lesenes, two arched friezes, a
  four-light window and two single ones in its top storey, a roundel and a window below; its helm an octagonal tiled
  spire to 35.2 m (white crosses in green-outlined diamonds on red and orange) with a dormer on each face, four square
  corner spirelets 2.6 m wide to 27.6 m, flush with the tower's faces and tiled like the helm ([the helm][mt11]),
  iron crosses. A stair turret with a stone cone on its north side.
- **Annexes** on OSM's part outlines: Schulek's porch before the Mary portal (pointed opening, hood, buttresses,
  balustrade, tiled hip roof); the south chapel by the choir (a flat roof behind its balustrade, as the photos and
  the aerial show); on the north the chapel row (lancets, roundels, pinnacles, a lean-to roof), the north gable
  block (a big traceried window and two roundels), the sacristy and north door under a balustrade and a dark low
  roof, and the St Stephen chapel with its windows, corner pinnacles, balustrade and tiled hip, and a stair turret
  with a spire. Balustrades and windows only on outside walls.
- Crosses and finials are 0.6 m thick: a 0.3 m post at the frame's angle to the grid falls between the voxel centres
  about two times in three.

**References**: the west front [from the square][mt5], [from the south-west][mt6], [with the Holy Trinity
column][mt7] (archer10, CC BY-SA); the south side [with St Stephen][mt8] (Nataraj Metz, CC BY-NC-SA), [the cross
roofs][mt9], [the side chapel's rosettes][mt10], [the Béla tower's helm][mt11], [the tower's top][mt12],
[the tower][mt13] (ahisgett, CC BY); [the apse roof][mt14] (MrUllmi, CC BY-NC-SA); [the cross roofs from the
south-west][mt15] (sfoskett, CC BY-NC-SA); [the apse and the north side][mt16] (jbdodane, CC BY-NC); [roofs and
turret][m3] (Alex E. Proimos, CC BY-NC); [from the river][mt17], [the roof][mt18] (VillageHero, CC BY-SA); [the
south side from the south-east][mt23] (ctj71081, CC BY-NC); [the apse from the Bastion][mt24] (Michael & Sherry
Martin, CC BY-NC-ND). Street photos on Mapillary (CC BY-SA 4.0): [the south side from St Stephen's statue][mt19] (its
computed pose gave the eaves and the turret's heights), [the north-east][mt20], [the north side][mt21], [the
portal][mt22]. Aerial: Esri World Imagery and Bing (reference only, for the roofs' layout).

## St Stephen's Basilica (Szent István-bazilika)

**Kept**: OSM's parts, which give the plan, the heights and the dome's 15.8 m radius.

**Dome**, replaced:

- a drum ringed by 32 columns, with an entablature, a balustrade and windows
- a green copper dome with 16 ribs and eight dormers
- a lantern of eight columns
- a small dome, ball and cross at 96 m

**Bell towers**: an octagonal open belfry each, a bell-shaped green cupola, a lantern and a cross at 80 m, and the
clock faces. On their west faces, a statue in a niche and paired windows under small pediments.

**West front**, between the towers (heights read off [the west front photo][b3], allowing for its upward
perspective):

- eight granite steps up from Szent István tér to the portico, 3 m;
- six engaged Corinthian columns, in pairs round the entrance and at the towers, to ~30 m;
- the deep arched entrance, 8.8 m wide, with the door and the gold mosaic in its head;
- the entablature with the inscription "EGO SUM VIA VERITAS ET VITA" in gold, 30–34 m;
- the pediment, 34–41 m, which is the nave's gable, with five figures in its recessed tympanum.

**Photos**: [dome][b1], [apse colonnade][b2], [west front][b3].

## Buda Castle dome and the palace

The National Gallery's dome over the palace's central wing:

- a drum with 16 pairs of columns and windows
- a green copper dome with ribs and four lucarnes
- a lantern, a small dome and a finial at about 67 m above the palace's foot (the aerial's lean puts the lantern
  about 66 m above the ground round it)

**The palace** (OSM: one outline round its courts, 3 levels, no height) is given its height in `overrides.json`:
33 m from its foot with hipped copper roofs over every wing, about 22 m to the eaves over the Lions' Court, as the
aerial shows; rows of tall windows on every wall, the courts' included (CLASSIC stone gets no procedural ones).

**The Lions' Court**: shut in by the wings, the 30 m ground models see their roofs in it and had lifted it to the
eaves. voxelize.py sets it level with the Hunyadi court, through the Lions' Gate (155.7 m).

**Photos**: [from Pest][k1], [at night][k2], [the river front][k3].

## Liberty Statue (Szabadság-szobor)

By Kisfaludi Strobl, 1947, on Gellért Hill:

- **Pedestal**: a stepped base, sheer at the back 3.5 m behind the centre and 15 m wide (OSM's retaining wall round
  it), stepping down to the front, and a 26 m tapering limestone pedestal.
- **Figure**: a 14 m bronze woman, her robe blowing back, arms raised in a Y, holding over her head a palm leaf about
  8 m across, its leaflets along both edges.
- **Side figures**: two bronze figures on their own plinths at the foot of the front steps, at OSM's nodes (about 9 m
  in front of the pedestal and 9 m to either side).
- **Since 2025**: the block in front of the shaft that held the Soviet soldier (now the 1990 inscription) and on the
  shaft above it a white cross ([Telex 2025][lc1]: placed where the soldier stood; [444][lc2]: taller than the 4 m
  soldier), drawn 12 m tall with a 4 m crossbar from We Love Budapest's 2026 photo ([ct5]); the shaft's broad foot
  up to the block's shoulders.

**Orientation**: it faces about 113° (east-south-east, towards Pest), down the Citadella's east cut: the line through
its two side figures in OSM, and the 2026 photos (the cut's white walls frame the pedestal's back, the leaf spreads
across the view from the park). It was drawn facing 35° before.

**Photos**: [silhouette][s1], [from the hill][s2], the 2026 front with the cross ([We Love Budapest][ct5]), the back
from the cut's foot on Mapillary ([1][ct15], [2][lc3]).

## Citadella (Gellért Hill)

**Sources**: the Habsburg fortress of 1850–54 (Emanuel Zitta to Ignaz Weiss's plans), about 220 × 60 m on the summit
([Wikipedia][ct1]); closed in 2020 for the Citadella-program and reopened on 5 April 2026, to the designs of Dániel
Taraczky (art1st design studio), built by ZÁÉV and Market. What the renovation made of it: three cuts through the
walls, the Rondella's north and south mouths and the east bastion behind the Liberty Statue, lined with white
monolithic concrete against the yellowish stone; the western Rondella a two-storey museum (A Szabadság Bástyája,
1 700 m²) with a semicircular roof terrace, a glass foyer (eight glued glass beams 14 m long, glass walls 11.2 × 2.4 m
and 14.2 × 2.4 m) and a glass bridge, a water mirror in its court; a 6 000 m² public park inside the walls with walks
along them; walls of Süttő limestone (13 800 m² cleaned), their coping red Tardos limestone ([Telex][ct2],
[Building Connections][ct3], [We Love Budapest 2025][ct4], [2026][ct5], [turizmus.com][ct6], [Magyar Nemzet][ct7]).
**The flag**: Hungary's largest national flag, 72 m², 6 × 12 m ([Infostart 2022][ct18]), on a steel mast 36.3 m tall
and 7.5 t ([Building Connections][ct3]; 36 m in [Telex 2022][ct8]), set in 2022 in a concrete block on the dolomite
where the old observatory stood, in the middle of the park on a long grassy mound ringed by a bed ([Telex][ct2]). OSM maps the outline
(`historic=fort`), the Rondella (relation 20421437, its court as a pond), the two casemate ranges, the park, the walls,
the cut's two walls, the flagpole (node 11331034119, `height=36`) and every flight of steps with its step count.

**Levels** (the 30 m models can't give them: FABDEM took the fortress for a building and reads 212 m inside it, and
OSM's summit node, 235 m just west of the Rondella, raised the plaza there over the Rondella's roof): the park at
229 m, from the GPS heights of the 2026 panoramas less the geoid and the surface model over the open courtyard. The
rest from the steps OSM counts (~15 cm each): the reception square 3.3 m under the park (22 steps), the promenades
6.9 m under it at the north mouth (24 more) and 5 m at the south mouth (11), the Liberty Statue's terrace 8.3 m under
it (52 steps down the east cut; a phone's heights on the 2026 photos going down it say 9 m); the walks 2.5 m over the
park (14–22 steps), the Rondella's terrace 5 m, the ranges' roofs 4.4 m (one storey on the park, three outside).
`landmarks_citadella.ground()` sets voxelize.py's ground to these inside the walls and to the promenades' levels
round them (the 2016 and 2026 photos along the Citadella sétány; the south wall stands about 7 m over it), blending
into the hill over ~25 m, ~50 m where the ground comes down (the summit's hump west of the Rondella). The Liberty
Statue's terrace is level from the cut's foot to the five steps down in front of it (27 × 25 m in the statue's frame,
out to OSM's retaining walls and steps): the blend had left it falling 3 m towards its front steps.

**Drawn** (`landmarks_citadella.py`, OSM's outlines):

- **Walls**: a Field from the distance to the outline. The outer face from the promenade up, battered towards its
  foot (up to 1.4 m out) with a darker plinth, courses of two creams, a row of slit loopholes; the parapet 1.1 m over
  the walk with its red coping; the walk 4.5 m wide behind it, paved, with a black railing where it stands over the
  park; the bastions' tops (the north-east bastion, the east bastion's two lobes) whole terraces at the walk's level.
- **Rondella**: the drum from OSM's outline, battered at the foot, two rows of embrasures, the parapet and coping;
  the terrace planted over brown mulch along the parapet and paved round the court (as the aerial shows it); the
  court carved to its paving with the water mirror flush in it; between the arms the glass foyer on the square, 8 m
  tall with mullions every 2.4 m, the arms' ends clad in white concrete, the glass bridge across at the terrace.
- **Reception square** (what the walls enclose between the Rondella, the ranges and the park) and its 9 m flight up
  to the park; the **north and south mouths**: stairs from the promenades up to the square between white concrete
  walls rising towards the square.
- **Casemate ranges**: OSM's two outlines from the ground below up to a flat roof planted over brown mulch behind a
  parapet with coping; arched doors and windows in stone surrounds, one storey on the park, up to three outside.
- **East cut**: carved through the east bastion along OSM's two walls, steps as wide as the cut from the park down to
  the statue's terrace, the walls white concrete, rising to points at their outer ends.
- **The statue's terrace**: pale limestone round its tulip bed (OSM's grass), stone retaining walls on three sides
  where the hill falls away, no trees on it.
- **Round the walls**: Sentinel-2 saw the building site there, which the pipeline paves by default (a band 25 m wide
  along the north side): grass at the walls' foot and along the promenades (OSM's ways keep their paving), young
  trees on the slope towards the Danube beyond them, as on the 2026 photos and the aerial's wooded slope.
- **Park**: lawn and beds of mulch, broad pale limestone paths along OSM's ways (4.8 m), young trees in the beds; the
  generated trees are cleared.
- **The flag**: the mound (13.5 × 7 m of lawn rising 1.6 m, a bed round it to 17 × 9.5 m) along the fortress, pale
  stones at the mast's foot, the mast tapering from 1 m and drawn as a voxel line all the way up (a thin lathe draws
  nothing where its radius drops under half a voxel), a cap on top; the flag (`landmarks_kossuth.flag`) 12 × 6 m,
  its top 0.5 m under the mast's, flying towards the south-east like the one on Kossuth tér; the hoist is a voxel line
  per half metre from the mast's own column into the cloth, so the flag never stands off the mast.
- The **Liberty Statue** is `liberty_statue` in landmarks.py; it stands on the ground at its node, now the terrace's
  level, and faces down the cut (its section above has the 2025 cross and the turn).

**Photos**: the 2026 panoramas walking through the park and along the walls on Mapillary (CC BY-SA 4.0): [the flag
from the north walk][ct9], [the Rondella from the north][ct10], [the glass foyer][ct11], [the park from the
casemates][ct12], [the east bastion and the statue][ct13]; from the statue's terrace [up the east cut][ct14] and [the
bastion and its cut][ct15]; the south promenade in 2016 [along the south wall][ct16]; the [drone view east over the
park][ct17] (Daily News Hungary, from the Citadella's Facebook); We Love Budapest's photos of the walls, the foyer and
the cut ([2026][ct5]). The footprint was checked against Esri World Imagery (taken during the works).

## Heroes' Square (Hősök tere)

**Colonnades**: OSM's three outlines of the Millennium Monument become the two quadrant colonnades and the
chieftains' plinth. Each colonnade has:

- a plinth, and columns every 3 m along both faces
- an entablature
- bronze statues between the columns
- end pavilions with bronze groups on top

**The column**: Gabriel's column is 36 m: a stepped base, the column, a capital, a gilded globe, and the archangel,
whose top is at OSM's 40.8 m. The seven chieftains are bronze horsemen round its base.

**Photos**: [square][h1], [colonnade at night][h2].

## Great Market Hall (Központi Vásárcsarnok)

**Walls**: OSM's outline, 184 × 58 m, in yellow brick with red bands and tall arched windows.

**Roof**: the long roof has Zsolnay tiles in zigzag bands and a glazed ridge.

**Front**: on the side facing the lower ground (Fővám tér) stand a brick gable with a great arched window and two
corner towers with tiled pyramid roofs.

**Photos**: [front][mh1], [inside][mh2].

## Dohány Street Synagogue

**Towers**: the two 43 m towers (OSM) are octagonal shafts in red and yellow brick stripes, each with an open
gallery, a gilded onion dome and a finial.

**Walls**: the walls are repainted in the stripes.

**Photos**: [interior][d1], [ark][d2] (exterior from general knowledge of the building).

## Margaret Bridge (Margit híd)

**Dimensions**: 607.6 m long, 25 m wide; six spans of two-hinged steel deck arches, the longest 87.9 m with a 7.3 m
rise, on masonry piers ([Wikipedia][mb1], [Structurae][mb2]). The two halves meet at the island pier: OSM's piers put
the bend at 150.6° (the line breaks by "roughly 30 degrees", [Budappest][mb3]). Allegorical figures by Adolphe Thabard
on the piers ([Budappest][mb3]); galley prows on the pillars and, on the island pier, the Hungarian crown between two
obelisks ([A View on Cities][mb4]). Yellow since 1979 ([Budappest][mb3]); in the photos a muted ochre.

**OSM**: the outline (two polygons: the bridge, and the branch to the island), four river piers (36.8 × 9.2 m) and the
island pier (38 × 26 m). The halves' axes run through each side's two piers; they meet within 3 m of the island
pier's centre.

**Drawn** (`margaret_bridge`):

- **Deck**: 25.2 m, the tram in the middle, two lanes each way, pavements; an ochre balustrade, lamp posts every 21 m.
  Nearly level over the river (11 m above the water at the bend, rising 2.2 m to the Pest bank), then down the
  approaches on stone columns.
- **Arches**: three per half, from the island pier's face to the piers and on to the bank abutment, each with six
  segmental ribs across the deck, a 7.3 m rise (less where the deck is lower), verticals every 3.6 m and lattice
  crosses in the outer spandrels.
- **Piers**: limestone cutwaters, rising at both ends above the deck as pedestals, each with a prow below and a
  winged figure on top.
- **Island pier**: level with the deck; two 12 m obelisks round the gilded crown on the downstream side.
- **Branch**: dips from the island pier to Margaret Island, with its own balustrade and girders, along its mapped road
  (it once pointed at the outline's far corner, 10° off), a dashed centre line.
- **Abutments**: stone, with an arch for the quay road.
- **Bank piers**: high enough for the approach to clear the ground behind the bank. Jászai Mari tér stands 2.5 m
  above the river spans, so the Pest half rises gently towards its bank and runs on straight and level with the
  square onto Szent István körút, the lower quay passing under the bank pier (it used to run buried under the square,
  painted onto the ground, with the roads across it dug down to it). The Buda half dips to its bank pier as before.
- **Lane markings** on every hand-built deck: edge lines, dashed lane lines, the line along the tram.

**Photos**: Mapillary (CC BY-SA 4.0) from the Buda bank: [the spans and piers][mb5], [the whole bridge][mb6],
[the deck and lamps][mb7].

## Petőfi Bridge (Petőfi híd)

**Dimensions**: 378 m over the river in three spans, 112 + 154 + 112 m (514 m with the approaches), 25.6 m wide;
four steel lattice girders acting as a grid, deeper over the piers (depth 1/24 of the outer spans and 1/32 of the
centre span); 20.4 m of carriageway with the tram in the middle and 2.6 m pavements; grey since 1952 ([Wikipedia][pb1],
[Structurae][pb2], [Hungarian Wikipedia][pb3]).

**OSM**: the outline and the two river piers, 154 m apart, which give the axis; the outer spans are scaled from there.

**Drawn** (`petofi_bridge`):

- **Deck**: 13.5 m above the water mid-river, falling to 10.5 m at the abutments; tram, lanes, pavements, a grey
  railing, lamp posts every 26 m.
- **Girders**: four, 7.2 m apart, 8 m deep over the piers, 4.8 m mid-river and 3.5 m at the abutments, so the
  underside sweeps in curves as in the photo. Verticals every ~6 m, Warren diagonals on the outer two, cross girders
  every 12 m.
- **Piers**: stone cutwaters with a cap under the girders; stone abutments with an arch for the quay road; columns
  under the approaches.

**Photos**: Mapillary (CC BY-SA 4.0) [from the Buda bank][pb4].

## Puskás Aréna

**Dimensions**: 316 × 259 m (OSM's outline; 316.5 m long and 52.26 m high per [Metalocus][pa1], 51 m per
[StadiumDB][pa2]). Three tiers of 28, 22 and 25 rows with boxes behind the middle tier ([StadiumDB][pa2]); red seats
([NSS Sports][pa3]); 38 pylons, about 30 visible through 19 500 m² of stainless-steel mesh ([Metalocus][pa1]).

**OSM**: relation 8766354 is the grandstand ring (outer = roof edge, hole = the lower tier's back), relation 10981440
the lower tier round the pitch. Both are replaced; the 1953 tower ("Torony") stays as OSM maps it.

**Drawn** (`puskas_arena`, from distances to those rings):

- **Facade**: grey steel mesh 7–41 m up, leaning out as it rises (6.4 m in from the roof edge at the bottom, 3 m at
  the top), with darker floor lines every 4.5 m.
- **Pylons**: 30 white lattice pylons, 7 m wide and 40 m high, evenly round the oval, standing proud of the mesh.
- **Ground floor**: glazed and set back 8 m under the mesh.
- **Roof**: an open gap above the mesh with white brackets every 8 m, then the white roof edge. The roof slopes from
  51 m at the edge to 47 m inside, with radial trusses and a lighter translucent band at the inner edge. It reaches
  6 m out over the lower tier, which is open to the sky, as Sentinel-2 shows (its red seats read reddish-brown there).
- **Stands**: the lower tier rises from the pitch to 12 m. A glazed box front leads to the middle tier (16–26 m),
  more boxes to the upper tier (30–44 m), and concourses fill the space behind. The seats are red in alternating
  shades row by row, with grey aisles every 15 m.
- **Pitch**: levelled, mown in 5.5 m stripes.

**Photos**: Mapillary street-level panoramas (CC BY-SA 4.0) from the west, south-west and south: images
[1026724767077221][pa4], [1669108093966349][pa5], [1377568334002507][pa6], [1139099811739948][pa7].

## Bridge ends

The river bridges meet a two-level embankment. Along the lower quays (the ones Budapest named after rescuers in
2023) the ground steps down to 3.5 m above the mean water, with retaining walls behind; the streets stay above.
At a hand-built bridge the bridgehead stays at the street's level and only the quay's own road (and tram) stay low
under it. voxelize.py then:

- leaves the decks over land out of the surface model (FABDEM keeps bridges): the ground under them is filled from
  around, so the street under a bridgehead is no longer lifted to the deck;
- digs every road or tram that crosses under a hand-built deck down to 4.8 m of headroom (3.8 m on a lower quay, 3 m
  for paths), on ramps of at most 7 %, except across a bridgehead that lies level with its square (Margaret Bridge's
  Pest end): there they meet the deck at grade (in reality Jászai Mari tér's road passes under it, but the model's
  square is too high for that);
- carves the mapped tunnels and covered ways near the river (`tunnel=yes`, `covered=yes`): a passage from a lower
  quay through a bridgehead, like the cycle path through the Chain Bridge's Buda abutment, runs on the quay's level,
  its mouths cut down to it.

landmarks.py's `approach` fills under a deck wherever less than 2.5 m of headroom would be left (a stone embankment,
which reads as an abutment wall where it faces an opening) and stands the deck on columns over the dug roads. The
Chain Bridge's bridgeheads use it too, so they open over the quay roads. Margaret Bridge's deck climbs to the street
at its Buda end and reaches Jászai Mari tér's level at its Pest bank pier; its branch runs on along the mapped bridge
road down to the island's road.

The bridgeheads' squares are held at the street's level: Fővám tér (108.6 m) and Szent Gellért tér (108.3 m) carry
virtual survey points, Pest's riverside is raised to the level of the streets behind it (the 30 m models dip towards
the river, seeing the quay below), and only Pest's trams count as running on a lower quay (Buda's run on the upper
one, so Szent Gellért tér is no longer sunk to the quay). Liberty Bridge's Buda end now meets the square at its own
level; Elisabeth Bridge's ends run on into Március 15. tér and the Döbrentei tér junction without a step. Petőfi
Bridge's deck stands 17 m above the water mid-river and 15.5 m at its abutments, so Boráros tér's roads pass under its
Pest end on gentle ramps instead of trenches.

**Flyovers**: OSM maps the Nyugati tér flyover as three ways; each used to rise and fall on its own, so the deck
waved. voxelize.py now chains the ways of one flyover (same name and layer, meeting end to end) and lays them as one:
the deck rises from each end at most 6.5 % to 6.2 m over the ground of its middle, and stands on columns every 26 m
where it is more than 3.5 m up.

**Photos**: the Pest bridgehead of Margaret Bridge, the girder span over the quay road between stone abutments:
Mapillary (CC BY-SA 4.0) [image 1095412846801805][be1].

## Budapest Eye (Óriáskerék)

**Dimensions**: 65 m high (OSM `height`), on Erzsébet tér; OSM maps its base, 46 × 20 m.

**Drawn** (`big_wheel` in landmarks_city.py): a white rim of 29.5 m radius on a hub 34.6 m up, two rings 3.2 m apart
laced with diagonals and an inner chord ring, 42 spokes a side; 42 closed gondolas (white, glazed, a light roof)
hanging between the rings; two pairs of legs splayed in the wheel's plane up to the axle, braced; a boarding deck
with its hut; 320 lamps round the rim.

## Soviet War Memorial (Szabadság tér)

**Dimensions**: 15 m (OSM `height`); by Károly Antal, 1946 (OSM `artist_name`, `start_date`).

**Drawn** (`soviet_memorial`): a white limestone obelisk on a pedestal with a bronze relief and a wreath on each long
face, the Soviet arms in gilt bronze on the obelisk, gilt lines of inscription, a gilded star on the pyramidion; two
low wings of bronze reliefs on a stepped platform.

**Photos**: Mapillary (CC BY-SA 4.0) from the square's south side.

## Ferencváros parish church (Assisi Szent Ferenc-templom, Bakáts tér)

**Dimensions**: Miklós Ybl, 1867–1879, neo-Romanesque; brick-clad, the tower 66.7 m high, the tower and the stair
turrets roofed in scaled copper ([We Love Budapest][fc1]); 66 × 28 m (OSM).

**Drawn** (`ferencvaros_church`): facing Bakáts tér (the end nearer the mapped square); yellow brick in red bands with
stone dressings; aisles under lean-to roofs, a 19.5 m nave under a slate roof, an apse with five windows;
round-arched windows in the aisles and the clerestory; the tower over the portal: an 8.6 m shaft with corner
buttresses, a rose window, a clock on each face at 29 m, a belfry of twin arches on each side, four small gables and
four pinnacles, and an octagonal copper spire to 66 m with a gilt cross; two octagonal stair turrets with copper caps.

The tower stands on the front with the main entrance (the `entrance=main` node on the outline), facing Bakáts tér's
west end; it once stood at the apse end.

## Bálna

**Dimensions**: Kas Oosterhuis's glass and steel shell (2013) between two of the 1881 Közraktárak warehouses; OSM
maps the whole (149.6 × 48 m), the glass part and one warehouse.

**Drawn** (`balna`): the two warehouses, red brick in yellow bands, four storeys of arched windows to a 15.5 m eave,
gabled slate roofs. The whale is a height field over the glass part: from the warehouses' eaves (or the ground, away
from them) up a quarter ellipse of 15 m radius to a crest of 22.5–26.5 m, highest towards the head, which follows
OSM's rounded outline down to the promenade. Its skin is a diamond lattice of white steel with frosted and clear
triangles, over a band of dark green glass at the bottom; inside, it is hollow.

**Photos**: Mapillary (CC BY-SA 4.0) from Közraktár utca: the shell's side over the green glass base, the warehouse
beside it.

## Hungarian State Opera (Magyar Állami Operaház)

**Dimensions**: Miklós Ybl, 1875–1884, neo-Renaissance; 50.7 m high (OSM, from Wikipedia); the outline 108 × 53 m
with the projecting centre (31 m wide) and the carriage porch mapped as parts.

**Drawn** (`opera`), from the outline's shape (the centre's width and depth, the pavilions' line, the porch):

- **Porch**: three arches to Andrássy út and one each side, a terrace with a balustrade on top; the doors behind.
- **Centre**: a rusticated ground floor; a loggia of five tall arches between paired columns, set 2.6 m deep with
  glazing behind, archivolts and a balcony; oculi in the frieze; the main cornice at 22.6 m; an attic with five
  windows; a balustrade with eight statues (the composers); behind it a slate mansard with dormers and a metal crest.
- **Corner pavilions**: an arched niche with a Muse on the first floor, a door under a pediment, an attic, and a
  square slate dome over each, steep at the foot and rounding over, with zinc ribs on its corners, a lantern and a
  gilt finial; corner finials and two statues.
- **Liszt and Erkel**, seated in bronze in niches either side of the porch; two sphinxes on the ramp walls.
- **Front range**: a steep slate mansard and over it a hipped roof with an iron crest and finials, dormers in front.
- **Auditorium and stage**, as aerial photos show them: one long hipped roof of pale zinc, as wide as the centre
  (31 m) and 74 m long, eaves at 26 m and ridge at 36 m, two round lanterns on the ridge (over the chandelier and
  over the stage); low roofs either side with rows of skylights framed in zinc every 8.4 m; a pale hipped roof
  across the back. (A round auditorium dome and a separate stage house stood here before: the aerial shows
  neither.)
- **Carriage drives**: arcades along both sides with a terrace above (the royal entrance on Hajós utca).
- Windows on the side and back walls, candelabra on the pavement.

**Photos**: Mapillary (CC BY-SA 4.0) [the front from Andrássy út][op1]; the side facades from Hajós utca; the roofs
from aerial photos (Google's and Esri's, looked at for reference).

## Erkel Theatre (Erkel Színház)

**Sources**: Marcell Komor, Dezső Jakab and Géza Márkus, 1911, as the Népopera; the Opera's second house from 1951,
named after Ferenc Erkel in 1953, its front rebuilt in the 1950s, renovated 2007-2013; 1,819 seats
([Wikipedia][ek-wiki]). OSM maps one outline, without parts or a height, whose front corners lie on a circle of 74.2 m
radius: `front_arc` fits that circle, and the building stands on it, +v out through the middle of the front. The
outline stays among OSM's buildings (dropped, it let the ground model read the theatre's roofs in the 30 m surface model
as ground and lift the square round it by up to 1 m); the builder clears the generic building drawn from it first.

**Drawn** (`erkel`, in `scripts/landmarks_erkel.py`):

- **Front range**: the circle's 49 m arc, 12.5 m deep, pale travertine to a plain parapet at 20.5 m. Seven bays 5.7 m
  apart (the end walls are 1.14 bays wide in the photos). On the ground floor, glass doors set back between piers up
  to a white canopy 4 m deep (5.0-6.4 m) that runs 3 m on past the front's ends, and a single door in each end wall;
  above it tall glazed bays (2.2 m wide, 6.4-14.5 m, four panes high) with blue mullions and transoms, and the opera's
  banners on the piers between them (7.0-14.4 m); E R K E L in blue over the five middle bays (15.0-17.5 m); seven
  recessed window strips (18.0-19.5 m) under the parapet. The letters are 2.5 m tall in a 4 x 5 pixel font (the real
  ones are about 1.9 m: a 4-row font was tried and read badly).
- **End blocks**: OSM's stepped outline at both ends, travertine to 14.6 m for about 20 m behind the front, white
  render to 11 m behind that.
- **Auditorium**: as the aerial shows its pale roof, 43 m wide 5 m behind the front range (a flat roof at 17.5 m
  between the two), narrowing to 32 m and rounded off over its last 14.5 m, to 1 m short of the stage house; white
  walls to the eaves at 17 m under a pale grey metal vault to 23 m with a darker ridge. A one-storey ring of rooms
  (5.5 m) round its narrow end, two three-storey blocks (9 m) beside the stage.
- **Stage house**: the full width of the back block (38 m), 23 m deep, white render to 26.5 m with rounded corners;
  five rows of windows, a glazed top storey, the half-round stair tower on the west side, a box on its gravel roof.
- **Service wing** behind it: four storeys, 13 m.

The front's heights come from the two square-on photos (the user's and wongwt's), scaled by the bays' 5.7 m spacing
and placed by the forecourt (17.5 m from the front to the kerb, which puts both cameras 25-27 m out): canopy 4.9-6.4
m, bay tops 14.6 m, letters 15.4-17.3 m, window strips 17.8-19.4 m, parapet 20.4-20.6 m. The end blocks from the
photo of the east end. The parts behind the front from Esri's aerial, set beside a top view of the bench leaned the
same way (shifted by (-0.063, -0.35) grid m per m of height). Átló gives 24 m for the whole outline; GBA's heights
here are smoothed to 16 m.

**Photos**: the front from the square (Google Maps, February 2021, sent by the user); Flickr: wongwt (CC BY-SA)
[the front][ek1]; Wikimedia: Globetrotter19 (CC BY-SA) [the west side and the stage house][ek2]; Mapillary
(CC BY-SA 4.0) [the east end][ek3], [the front from the west][ek4], [the east side][ek5], [the stage house from the
south-west][ek6], [the ring round the auditorium][ek7]; the roofs from Esri's World Imagery (looked at for reference).

## Gellért Hotel and Baths (Gellért Szálló és Gyógyfürdő)

**Sources**: Ármin Hegedűs, Artúr Sebestyén and Izidor Sterk, 1912–1918, Art Nouveau. OSM maps the whole complex as
one outline (8 275 m², 5 levels + a roof storey); the outdoor wave pool (Hullámmedence) and the warm adventure pool
(Élménymedence, 36 °C) as `leisure=swimming_pool`.

**Drawn** (`gellert`), on a frame whose +v faces the Danube:

- **Ranges**: a Field from the distance to the outline: every range 15 m deep, walls to 22.5 m (the range against the
  hill 20.5 m), pale stone with a rusticated ground floor, lighter bay strips every 7.6 m and a cornice; brown-red tiled
  roofs rising 0.88 m per metre from both sides of each range. Windows: arched on the ground floor and the top floor,
  square between.
- **Middle tower** (where the outline's front projects): an attic storey to 31 m with a great arched window and the
  name in gilt letters, a steep red hipped roof rising 12.5 m, an octagonal copper lantern with windows, a dome and a
  gilt spire, to about 55 m.
- **Corner pavilions** at both ends of the hotel front, symmetric about the tower: a square attic and an octagonal
  green copper dome with ribs, a lantern and a finial.
- **The baths' rotunda** on the corner of Kelenhegyi út (where the outline steps back beyond the hotel front): a round
  drum, 15 m across, with two tiers of tall arched windows, under a dark ribbed dome with a lantern.
- **Inside**: the halls behind the ranges under low zinc roofs with rows of skylights; over the swimming hall a glass
  barrel vault on iron ribs, and a glass dome over the thermal hall.
- **Pools**: the outdoor pools as basins 1.4 m deep with the water 0.3 m under a white stone rim.
- **The open-air baths** up the hill behind (placed from aerial photos, `gellert_garden`): the sun terrace, a
  one-storey white arcade bent round the half-moon garden in an arc from 18.5 to 27 m out, open towards the baths,
  its roof in terracotta tiles behind a white balustrade, arched bays on both faces; a terracotta promenade inside
  the arc and clipped shrubs in the garden; the wave pool's terracotta deck with a balustrade, the stepped curve at
  its far end, the round children's pool beside it.
- **Ground**: the 30 m models carry Gellért Hill's slope down to Szent Gellért tér, which stood the hotel 10 m above
  its own entrance. voxelize.py lowers its front garden to the square's level (107.6 m), fading over 14 m, and the
  hotel stands on the ground in front of it, cut into the hill behind.

**Photos**: Flickr, G Travels (CC BY-NC) [front][g1], [tower and domes][g2], [the baths' rotunda][g3]; street photos
round the building on Mapillary (CC BY-SA 4.0) [map][gm]; the open-air baths: kakov (CC BY-NC-SA) [the wave pool and
the arcade][g4], [its side][g5].

## BME Building K (Budapesti Műszaki Egyetem, K épület)

**Sources**: Alajos Hauszmann, Győző Czigler and Samu Pecz, 1909. OSM: the outline (200 × 113 m, 6 levels), the
5-level ranges as a part with the light courts as holes, the courts' low halls as parts, the aula's glass roof as a
part (`building:part=roof`).

**Drawn** (`bme_k`):

- **Ranges**: a Field from the distance to the ranges' part: walls to 22 m, a rusticated stone ground floor to
  5.6 m, red-brown brick above with stone bands and pilaster strips every 7.2 m; slate roofs rising 1.15 m per metre
  (about 49°) to a ridge, in a diamond pattern of three slates. Windows in four rows, arched on the ground and second
  floors.
- **Entrance pavilion** (the middle projection of the river front, found from the outline): grey-brown sandstone to
  25.5 m, three arched doors, six giant columns on the first and second floors with tall windows between, paired
  windows in the corner bays, an entablature and a balustrade; a hipped slate roof rising 12 m with an iron crest and
  dormers; an octagonal turret with a slate spire on each corner.
- **End pavilions** (where the cross wings come forward to the river): brick to 23.5 m with stone quoins, a pyramid
  roof rising 13.5 m and a spirelet.
- **Aula**: a glass hipped roof on iron ribs over the central court.

**Photos**: Flickr: francisco.j.gonzalez (CC BY) [the main entrance][bk1], [a side pavilion][bk2]; hanspoldoja (CC BY)
[the river front at night][bk3]; Mapillary (CC BY-SA 4.0) [map][bkm].

## Hungarian National Museum (Magyar Nemzeti Múzeum)

**Sources**: Mihály Pollack, 1837–1847, Classicist. OSM: a 110 × 87 m outline with two courts as holes, the portico
and its stair as a 36 × 15 m projection towards Múzeum körút.

**Drawn** (`national_museum`):

- **Block**: walls to 20.6 m, cream above a grey rusticated ground floor, a string course, a frieze, a dentilled
  cornice with an overhang and a low attic; low zinc roofs over the ranges. Windows: plain on the ground floor,
  pedimented with sills on the main floor, smaller above. Giant pilasters with capitals at the ends of every long
  wall.
- **Portico**: a podium 4.4 m high reached by a twelve-step stair between side walls; eight Corinthian columns
  (bases, tapering shafts, flared capitals) to the entablature; three doors with pediments and windows over them in
  the porch; a pediment rising 5.3 m with nine figures in the tympanum and an acroterion.
- **Dome**: a 16-sided drum with small windows and a low zinc dome with a lantern, over the Dome Hall between the two
  courts.

**Photos**: Flickr: HatM (CC BY-NC-SA) [front][nm1], [portico][nm2]; TopBudapestOrg (CC BY) [the museum][nm3];
Mapillary (CC BY-SA 4.0) [map][nmm].

## Hilton Budapest (Hess András tér 1-3)

**Sources**: Béla Pintér, 1976 (opened 1 January 1977), round the remains of the Dominican church and friary of St
Nicholas (13th century; the tower 15th-16th century, its ruin restored 1924-26) and behind the restored late Baroque
front of the Jesuit college. OSM: the outline as relation 5647453 (5 055 m², a courtyard as its hole), the tower as
part 379070846 (8.6 × 9.1 m), the church's ruins as 439377979 (`historic=ruins`, the nave and the polygonal apse). The
octagonal top of the tower is the 1970s' own: a cone of glass blocks and concrete panels (reflecting glass since 1990)
round a steel fire-water tank (*Víztornyok Magyarországon*, MAVÍZ 2007, [p. 72][hl6]). Everything is placed on a frame
along the Baroque front (u north, v east into the building).

Heights were measured, not taken from tags (OSM has `building:levels=4` only): rays from Mapillary photos with their
computed poses ([1][hl7], [2][hl8], [3][hl9]) give the Baroque eaves at 15-16.5 m above the street, and the Street
View view of the front, scaled by the people at the door, 15.1 m. The rest comes from proportions in the photos: the
fins' eaves about 2 m over the Baroque cornice, the tower's square shaft 18.7 m, the octagon to 27.5 m (about as tall
as it is wide, in the front views), the spire's tip at 32.5 m (where the owner's view puts it).

**Drawn** (`landmarks_hilton.hilton`):

- **The Baroque front** on Hess András tér, 74 m from Szentháromság tér to the tower and 12 m deep (the outline is
  that deep beside the tower): white walls to the cornice at 15.3 m; fifteen bays of 4.75 m, the entrance in the sixth
  from the tower (counted in the photos: five bays north of the doors, nine south; cross-ratios of the window columns
  put the tower 5.5 bays north of the doors and the corner 10.3 bays south, so 74.6 m / 15.7; OSM's `entrance=main`
  node sits 2.5 m north of the middle door), each with a giant pilaster from the plinth to capitals with volutes at
  11.2-12.2 m; windows on four floors: the ground floor's tall ones (1.1-3.4 m), the first floor's under triangular
  pediments (6.0-7.6 m), the second floor's with a carved garland over them, the attic's (12.9-14.1 m) above an
  entablature, blank panels over the pilasters; a pilaster also between the southmost bay and the corner's; a two-step
  cornice. The end on Szentháromság tér has two bays. A brown tiled roof rising 8.2 m (about 52°), hipped over the
  square; by the tower a raised attic with garlands and three statues.
- **Entrance**: three doors, one in each of the three middle bays, under a flat dark canopy 13 m wide and 5.6 m deep
  with the name in letters on its edge (as street photos show it in 2025; older ones, the owner's Street View view
  among them, show a gabled canopy).
- **St Nicholas tower**: rough coursed stone to 18.7 m with pointed windows on two levels, the King Matthias memorial
  (a copy of the relief in Bautzen, put up in 1930) in a white aedicule on the west face; a tiled skirt, then the
  white octagon to 27.5 m with a tall slit of dark glass in every face, white pinnacles on three corners and a turret
  with a cone on the south-east one, an octagonal tiled spire to 32.5 m with a finial.
- **The 1970s wings** (a Field from the distance to the outline): deep cream fins every 2.6 m, 1.4 m wide with a flat
  front and raking cheeks, 0.6 m proud of strips of bronze reflecting glass (a gold spandrel and a window per storey);
  a slate hood hanging over the top of each strip; a steep slate mansard (about 70°) with a roof window over each
  strip, to a flat roof; on the street the ground floor set back under a dark soffit, with shops behind columns under
  the fins. The south block (round the courtyard): four storeys of fins over a 4.2 m ground floor, eaves at 17.4 m,
  the flat roof at 22.2 m with two plant rooms and a glass roof light along the courtyard; the lower north block:
  three storeys, eaves at 13 m and its flat roof at 18.2 m. Below the street's level, where Castle Hill falls to the
  east, the walls stand on the old rubble masonry. Beside the tower a low wing with a hipped roof and four flags in
  front of it.
- **The Dominican church**: its nave is the open court between the two blocks; the ruined north wall, up to 6.8 m with
  three pointed openings, and low walls round the apse that comes out towards the Bastion. In the notch of the north
  block OSM's parking (314893767) stays an open court, as Bing's aerial shows it with cars in it.

**Ground and view**: the outline stays in the ground model as a 12 m building (`Plan.ground_keep`): left out, the
surface model's blur of the hotel's roofs read as open ground and lifted Hess András tér 6 m; with it the street stays
at 172 m, as before the hotel was hand-built. The `hilton` view looks at the Baroque front from over the roofs across
Hess András tér, the tower on the left.

**Photos**: the front on Hess András tér (Google Street View, from the user) and Dezidor, Wikimedia Commons (CC BY
3.0) [the western facade][hl1]; ctj71081, Flickr (CC BY-NC) [the fin facades from Szentháromság tér][hl2]; Takáts
Ákos, Flickr (CC BY-NC-SA) [the Danube front from Pest][hl3]; Nigel Swales, Flickr (CC BY-SA) [fins, glass and
hoods][hl4]; the north wing over the ruins, the tower and the corners on [manchesterhistory.net][hl5]; Mapillary (CC
BY-SA 4.0) [map][hlm]. Roofs and the courtyard from Esri's and Bing's aerial photos, looked at for reference.

## Kálvin tér skybridge (the Mercure Korona's gallery)

**Sources**: OSM part 129917689 (`building:part=bridge`, levels 3-4) over Kecskeméti utca between the hotel's wings;
street photos on Mapillary.

**Drawn** (`kalvin_bridge`): a flat beige arch springing at 6.4 m and reaching 9.6 m at its crown, the gallery's floor
at 10.6 m, a glazed storey to 14 m with mullions every 1.8 m, a roof slab with planters along its edges and a railing.
The street under it stays open (the generic code once drew it down to the ground, as a building across the road).

**Photos**: Mapillary (CC BY-SA 4.0) [map][kvm].

## Blaha Lujza tér: the Corvin Palace and the Europeum

**Sources**: OSM outlines 261801166 (the Corvin Palace: a 61.1 m front to the square, 75 m along Somogyi Béla utca, 88 m
along Márkus Emília utca, 41.5 m on Stáhly utca) and 308551954 (the Europeum: 63.1 m to the square, 38.8 m to József
körút, 48.5 m to Somogyi Béla utca, its south side against its neighbours); no building parts. The Corvin was clad in
aluminium from 1967 to 2018 and under scaffolding until 2023, so only photos from 2025-2026 show its front: Time Out
Market Budapest's photo (October 2026) and Mapillary panoramas. Bays are measured from the angles in a panorama taken square
to the front (fitted to the outline's corners), heights from elevation angles in panoramas whose distance is known
(about ±1.5 m), cross-checked against the storeys. [Telex][bl1] (2023) on the restoration: the front looks one storey
high over four storeys inside, and its four corner candelabra were rebuilt from old photographs. Roofs, the courts and
the Europeum's lift tower from Esri's aerial imagery (taken while the Corvin's roof was still being rebuilt).

**Drawn** (`landmarks_blaha.py`, `corvin`):

- **The stone front** along the square and 15 m into each side street, pale beige: corner piers 2.5 m; four arches a
  side 4.1 m wide springing at 5.7 m, between piers 1.7 m wide with round medallions, the shop fronts in them under
  balustrades and glazed arch heads; in the middle the square portal 6.1 × 7.1 m between piers 3.5 m wide, the CORVIN-PALACE board over it.
  A rusticated ground storey to 8.8 m, a string course and the key band to 9.9 m; giant fluted pilasters (paired at
  the corners, by the portal and at the returns' ends) to capitals at 17.3 m, tall windows 3 × 4.6 m between them in
  dark brown frames with the wooden band of the floor behind them and a carved panel above, over the portal a triple
  window (2.5 m between two of 0.9 m, pilaster strips between them) and Time Out Market's dark banners hung between
  the paired pilasters either side; frieze windows 1.4 × 0.9 m between consoles; a dentilled cornice overhanging
  1.3 m, its top at 19.8 m; a balustrade to 21.05 m with a pedestal over every pilaster; four candelabra (pedestals
  and stone obelisks to 24.8 m) on the front's corners and the returns' ends; a relief figure on each corner over the
  arcade.
- **The back ranges** along the side streets and Stáhly utca: 19 m to the cornice, greige render, a banded ground floor
  with a shop window in every 5.4 m bay, four storeys of windows in pairs between pilaster strips, the two corners on
  Stáhly utca rounded (5 m). Behind the front range a court down to 10.5 m with the hall's glass roof in its middle;
  two skylights and a stair house on the front range's roof.

**Drawn** (`europeum`):

- **Base**: square stone piers every 5.25 m, the shop windows 1.2 m behind them to 5 m, a fascia, big panes on the
  first floor to 9.6 m; a double-height entrance on the square.
- **Hotel**: three storeys of 3.2 m to 19.6 m, in every bay a narrow window beside a wide one; the parapet at 20.2 m.
- **Top**: over the western half of the square front a glazed storey set back 1.6 m; over the eastern half and József
  körút the front rises as an open stone frame to 23.6 m with a loggia and a glass wall behind it.
- **The corner** to the square and the körút cut away 6.3 m along each front and 4.6 m deep, the full height, behind an
  open stone frame: a 2 m corner pier with the shops' signs stacked up both its faces, beams over the shops (5 m) and
  over the first floor (9.6 m) with a pier between them in the middle of each opening, the roof slab across the top;
  glass walls behind, so the sky shows through the frame from along either front. On the roof above it the red
  europeum letters, 18 m long in a five-row pixel font (0.55 m pixels), read from the square.
- A court over the mall's glass roof at 10 m, hotel windows round it; the lift tower over the roof.

**Photos**: Mapillary (CC BY-SA 4.0): [the Corvin's front, square on][bl2], [both from the square][bl3], [Somogyi Béla
utca][bl4], [the north corner from Rákóczi út][bl5], [Stáhly utca][bl6], [Márkus Emília utca][bl7], [the Europeum's
front][bl8], [its corner from József körút][bl9]; [map][blm]. With the request came Time Out Market Budapest's photo
(Google Maps, October 2026) and a Google Street View of the Europeum (March 2021).

**View** `blaha`: from 118 m north of the two fronts (a little east of north), 24 m up, both buildings side
by side across the square.

## Boats on the Danube

**Sources**: OSM `building=ship` / `houseboat` outlines (Spoon, Boatanic, the Kossuth museum ship, A38, Kassa, Fortuna,
Grand Jules, Vogue, Kláris) and two `building=yes` on the water (A38's exhibition barge, the Zsófia event ship). They
used to be extruded like buildings.

**Drawn** (`danube_boats`), each on its outline's rectangle:

- **Hull**: full beam amidships, a pointed bow (the narrower end of the outline, or upstream: boats moor facing the
  current), a rounded stern, sides tucking in below the waterline, a deck that rises towards the bow; a dark band at
  the waterline and on the gunwale, white topsides, a wooden deck.
- **Passenger ships**: one to three decks (by length; hotel ships three) with window bands and rounded fronts, a
  railing round the sun deck, a wheelhouse, a flagstaff with the Hungarian flag, awnings over the restaurant and bar
  boats' sun decks.
- **A38**: a dark grey stone carrier with a red bottom, a bulwark round the hold, its wheelhouse block aft (three
  decks and a red funnel), a glass pavilion on the deck and a mast; the exhibition barge alongside with a long
  pavilion.
- **Kossuth** (1913 paddle steamer): paddle boxes amidships and a yellow funnel with a black top.

**Photos**: Flickr: jd (CC BY-NC-ND) [A38][a1]; Cynewulf (CC BY-NC-SA) [boats on the Pest quay at night][bt1];
Mapillary (CC BY-SA 4.0) [A38][a38m], [Spoon and the Kossuth][btm].

## Budapest Zoo: the Great Rock and the Elephant House

**Sources**: the 1912 rebuild (Kornél Neuschloss, Károly Kós); the Elephant House an Eastern-inspired pavilion clad in
Zsolnay tiles with a minaret; the main gate with elephant and polar bear sculptures, Zsolnay ceramics and Miksa Róth's
mosaics; the Great Rock (Nagyszikla) an artificial mountain by Gyula Végh ([Hungary Unlocked][zoo1]).

**Drawn** (`zoo`):

- **Great Rock**: a height field over OSM's outline, 33 m at most, broken by a few octaves of waves into crags and
  gullies and stepped into 1.2 m ledges; grey concrete rock in blocks of five shades, green on the gentle ledges.
  The Little Rock the same at 13 m.
- **Elephant House**: walls in cream and ochre bands under a red cornice, a sixteen-sided drum with arched windows
  and a Zsolnay dome (cream, teal, green, gold, blue) with a gilt finial and crescent; half domes over both ends;
  horseshoe-arched windows and portals; an octagonal minaret with a balcony and a tiled cap, 27.8 m.
- **Main gate**: a low range with a mosaic frieze, a gateway arch between two pylons, a stone elephant on each, and a
  polar bear over the gate.

## Széchenyi Baths (Széchenyi Gyógyfürdő)

**Sources**: Győző Czigler and Ede Dvorák, 1913; the pool wings by Imre Francsek, 1927. Mapillary (CC BY-SA 4.0)
photos show the 1913 front in grey-white stone with three domes and the yellow wings round the pools.

**Drawn** (`szechenyi`, on OSM's outline with its courts): walls to 14.5 m, the 1913 range (the side away from the
pool court) in stone, rusticated below, the rest yellow with white bands; arched windows on every wall; hipped roofs
from the distance to the walls, with balustrades; a ribbed dome with a lantern over the entrance hall (8.5 m radius)
and one over each front corner, two small copper domes over the court's corners; a portico with a pediment. In the
court: a 50 m swimming pool between two warm pools with rounded ends, in white stone rims.

## Museum of Ethnography (Néprajzi Múzeum)

**Sources**: Marcel Ferencz (Napur Architect), opened 2022: two wings that dip to the path between them, where the
park opens onto 56-osok tere, and rise outwards like ramps; a roof garden on top, edges clad in a metal grille whose
pixels draw folk motifs.

**Drawn** (`neprajzi`): each wing of OSM's two polygons rises from 1 m at the end by the gap to 22.5 m at its outer
end, on a concave curve (21.5 t^2.6); a lawn with gravel paths on top and a white parapet; the sides in pixel panels
of four greys; glass under the raised ends. (They first rose towards each other: turned round on a local's note.)

## Keleti Station (Keleti pályaudvar)

**Sources**: Gyula Rochlitz and János Feketeházy, 1884; OSM maps the shed (31 m, a round roof 13 m high), the Lotz
hall, the side wings and the corner pavilions as parts.

**Drawn** (`keleti`): the shed's walls to 18 m and a barrel vault 13 m high, its ribs every 6.5 m and a glazed band
along the top. The head on Baross tér (the end without tracks): an arched gable with a great window of iron mullions
in a raised frame, three portals, pilasters with statues, an attic with a clock and three statues. The far end glazed
over the tracks. The corner pavilions with mansards and lanterns, James Watt and George Stephenson in niches facing the
square. The side wings stay OSM's.

## Nyugati Station (Nyugati pályaudvar)

**Sources**: August de Serres for the Eiffel company, 1877; OSM maps the shed (gabled), the front pavilions with
their corner turrets and the side wings.

**Drawn** (`nyugati`): the shed's walls to 16 m under a gabled roof of slate with a glazed ridge, iron ribs every
7.5 m; the gable on Teréz körút glazed in a blue-grey iron grid, with three doors and a clock; two stone towers with
domed caps and statues either side. The far end glazed over the tracks; the pavilions and wings stay OSM's.

## Rákóczi tér market hall (Rákóczi téri vásárcsarnok)

**Sources**: Market Hall II (the sign over the entrance reads "II. VÁSÁRCSARNOK"), built 1894–1897; OSM's `architect`
and the English Wikipedia name Pál Klunzinger and István Rozinay. Burnt out on 6 May 1988, reopened on 25 July 1991
after a rebuilding by György Tokár and György Hidasi. OSM: the 75.7 × 71.2 m outline (relation 4514296), stepping
out 1.2–1.8 m at the corners on the sides and the back where the pavilions stand; no parts inside. The plan and the
roofs are read off Bing's and Esri's aerials (reference only); heights off a frontal street photo taken 112 m away,
scaled by the gable's width (14.4 m, the nave's width on the aerials). The main gable's were checked again against
the user's photo of the front, solved for its camera (19.5 m out, at eye height, about 70° wide, tilted up 19°): the
wings' balustrade (11.9 m) and obelisks (14.7 m) come out as drawn, the entablature 14.9–16 m at its ends and 17.7 m
in the middle, the arms' top 20.5 m, the window and the entrance both about 7 m wide; [a Mapillary panorama from the
square][rk8] agrees (16 m, 18 m, 20 m by the gable's width).

**Drawn** (`rakoczi_hall`, `scripts/landmarks_rakoczi.py`):

- **Plan**: two naves 14.4 m wide crossing in the middle, each with aisles to 26 m; one-storey links in the four
  angles; pavilions of about 17.8 × 15 m on the corners, placed by the outline's steps.
- **Naves**: walls to 15 m with clerestories over the aisles, gabled roofs of grey-green sheet to 17.8 m with vents
  along the ridges; where they cross, their valleys make the X seen from above. Aisles: walls to 10.8 m, lean-to roofs
  rising to 12.2 m against the naves.
- **Main gable** (Rákóczi tér): a segmental arched window 7 m wide from 6.3 m to 14 m, in blue iron with two posts
  and transoms over small panes, set back half a metre in a ring of brick voussoirs and a red and white chequered
  band, with a keystone. Under it the entrance, as wide as the window and 4.6 m high, two iron posts and the folded
  doors, a frieze of iron rings, the sign and the clock. Piers with stone bases to 2.2 m, quoins, string courses,
  relief panels and lamps. The entablature runs from 14.2 m to 16.1 m over its stepped ends and rises 1.6 m to the
  middle: a frieze, dentils, a corona projecting 0.9 m. On a pedestal at the top the city's arms, a crowned shield
  held by a lion and a griffin, to 20.4 m.
- **Wings** (the aisles' ends, 5.8 m wide): triple windows on two floors (blue grilles on the lower ones), a string
  course at 6 m, relieving arches, a red brick frieze and a cornice to 10.8 m, a balustrade to 11.8 m, a stone obelisk
  on a pedestal at each outer end to 14.9 m, a scroll down to the link, a lantern on the corner.
- **Links**: one storey to 7.8 m, three tall grilled windows, a red band, a cornice and a parapet; on the front a
  small gable with scrolls over the middle, on the other sides a loading door under an iron and glass canopy. Their
  roofs are lean-tos glazed against the aisle walls, which have high windows above them.
- **Pavilions**: two storeys to 10.8 m: a stone plinth, shop windows, a zigzag brick band between the floors, windows
  above, a red frieze and a cornice, quoins; hipped roofs of brown tiles rising 3.6 m, with chimneys.
- **Side and back gables** (Vásár utca, Déri Miksa utca, Víg utca): the same window and entablature without the arms
  and the clock, behind closed blue doors; their wings end in plain parapets.
- **Colours**: yellow brick with a red band every 2 m, white limestone, blue iron, the grey-green of the aerials on
  the hall's roofs.
- **Its outline** stays a building to voxelize.py before the landmarks are drawn (`KEEP_GROUND` → `Plan.ground_cover`):
  dropped, its grey-green roof read as a green courtyard and got trees, the square's trees moved (one more random
  draw), and the ground model took the footprint as open ground. With it, the square round the hall matches the build
  without the landmark (995 of 123 000 columns differ in the bench window, all by one voxel).

**Photos**: the user's photo of the main front (Google Maps, May 2026); Wikimedia Commons: Sir Morosus (CC BY-SA)
[the crossing inside][rk1], Globetrotter19 (CC BY-SA) [the Víg utca front][rk2], Fortepan 88992 (CC BY-SA)
[the main entrance in the 1970s][rk3]; Mapillary (CC BY-SA 4.0) [the front from 112 m][rk4], [the south half of the
front][rk5], [the Vásár utca gable][rk6], [the corner pavilion on Vásár utca][rk7], [a panorama on the square][rk8],
[map][rkm].
## WestEnd City Center

**Sources**: József Finta and Partners (lead architects József Finta, Antal Fekete, Alfréd Peschka), designed in 1997,
opened on 12 November 1999 for TriGránit; about 186,000–194,500 m² gross: the mall (49,700 m², 400 shops, the cinema),
the hotel (the Hilton until 2023, now the Crowne Plaza, 230 rooms), the WestEnd office building (17,000 m²), roof
gardens of 15,000 m² and a car park for 1,700 cars. Since June 2026 a 6,500 m² solar park covers the car park's roof
(1,530 MWh a year). OSM maps the mall as one outline (4 levels, with a fixme for its parts), the Millennium garden's deck
(`building=roof`, level 2), the car park (3 levels from level 2), the two roof gardens (`leisure=park`,
`location=roof`) and the glass roof of the passage from the station; no heights. `scripts/landmarks_westend.py`.

**Measured**: the plan from Esri's World Imagery on the grid (the hotel and office bars along Váci út, the cinema
hall's curved wall round the roof garden, the skylights, the deck's round terrace, the car park's ramp drum); heights
from storeys in street photos and Mapillary panoramas, and the lean of the roofs in the imagery (0.35 m per m of
height): the mall's podium and its garden 15 m, the entrance block 13 m, the hotel's brick to 22.5 m under a
set-back top floor to 26 m, the offices 25 / 28.5 m, the cinema hall 24 m, the deck 9 m, the car park's decks at 4.8,
9.6 and 14.4 m. The canopy was triangulated from three panoramas on Nyugati tér and Váci út (the steel tree's crown at
13.6 m from three, the corners from two each): a plate 44 × 25 m, its corner over Váci út and the square 25 m up, the
corner towards the station 15.5 m, the far ones 23.5 and 14 m, held 4 m beyond the entrance block's front. Estimated to
±2 m. The canopy and the entrance are measured from the square, which lies 1.1 m under the mall's base (Váci út climbs
from it, 3 m over the mall's length). The entrance front from the owner's photo, which is perspective-corrected and
square to it: the canopy's near edge (25 m, falling 9.5 m) gives the scale and the camera (about 45 m out on the
square), and from there the piers, the glass between them, the posters, the sign and the doors (±1 m), and the front's
top at 12.3 m against the canopy's corner at 25 m. From the same pose the brick pylon under the station-side canopy
falls where the photo has it, that canopy's inner beam runs level at about 8 m, and its outer edge is at about 13.5 m.
The glass wedge from the photo (its end, a triangle rising to the pier) and from Váci út (a sloped glass face up to the
H&M sign, the dark block beyond it, as in the architects' photo).

**Drawn** (`westend`):

- **Canopy**: a plate of clear glass on a grid of steel beams (11 across, 6 along, drawn as plates under the glass so
  their lines stay straight), a steel edge all round, a truss with zigzag webs under the high side, a deep one under the
  low side resting on the entrance block, bracing in some bays. The steel tree: sixteen rods from a crown on a granite
  base on the entrance block, each splitting in two under the glass.
- **Entrance on Nyugati tér**: the glazed front, 16 m between two dark granite piers 2 m wide and 13.5 m tall, with
  the posters (a white panel and a photo on the left, two blue ones down to the ground on the right), the WESTEND sign
  (the W in a white box, then the letters) and the doors under a small glass canopy. North of the left pier a glass
  wedge leans on it and on the low block behind: 7 m high, sloping down to Váci út over 3.4 m, 22 m long, its end a
  triangle to the square; the H&M sign on the pier above it. The glazed canopy over the passage to the station reaches
  12 m out over the square: a steel beam along its inner edge at 8 m, the glass rising 5.6 m outwards over 7 m, an
  ochre brick pylon holding it on the square.
- **Along Váci út**: the hotel (punched windows, full-height glass strips) and the offices (ribbon windows, wings
  round two glazed courts) in red-brown brick over a granite and glass ground floor, their top storeys set back in grey
  metal; the cinema hall: salmon brick to 15 m, silver panels above.
- **Mall**: salmon brick to the service street with a strip of windows and a cream band, glass in the entrances from
  Váci út; the Semiramis roof garden on top: lawns, radial paths, the oval pond, the promenade over the street, trees,
  and the gallery and atrium skylights (the long one leans on the hotel, a chain of them follows the cinema hall's curved
  wall); a glass drum over the Niagara fountain.
- **Millennium garden**: a deck on cream columns with red feet, a car park under it; lawns, paths, two rows of trees
  along its edge, the round terrace under a ring roof, the fountains, the playground and the kiosk.
- **Car park**: three decks on columns with cream parapets and red rails, the ramp's drum at the east end, rows of
  solar panels on frames over the top deck. The trees the pipeline generates inside the complex are cleared
  (`Scene.clear`): they stood on the ground under the roofs.

**Photos**: the architects' photos ([Finta Stúdió](https://www.fintastudio.hu/en/projects/westend-city-center), 2000);
[Wikimedia Commons, Category:Westend, Budapest](https://commons.wikimedia.org/wiki/Category:Westend,_Budapest) (the
entrance at night, the H&M front); Flickr via Openverse (jaime.silva's [canopy](https://www.flickr.com/photos/20792787@N00/52739454) and [steel tree](https://www.flickr.com/photos/20792787@N00/52739458), CC BY-NC-ND);
Mapillary (CC BY-SA 4.0) panoramas on Nyugati tér and Váci út, and the service street, the decks and the roof garden;
the owner's photo of the main entrance (about 2019). Facts: [Wikipedia](https://en.wikipedia.org/wiki/WestEnd_City_Center),
[westend leasing](https://leasing.westend.hu/en/buildings/westend-bevasarlokoezpont),
[Telex on the solar park](https://telex.hu/gazdasag/2026/06/30/westend-napelempark-megujuloenergia-napenergia),
[BCSDH on the roof garden](https://bcsdh.hu/en/news/unique-environmental-and-community-value-we-visited-the-westend-rooftop-garden-with-experts/).

## Statues, busts and church windows

`scripts/landmarks_statues.py`, after two ideas in [warsaw-vibe-voxel][wvv] (its monuments as voxel art and its
windows on churches), drawn here with this map's own solids. It runs after every other landmark, because it looks at
what they drew.

**Statues**: every statue, bust and sculpture OSM maps as a node or a small area (`tourism=artwork` with
`artwork_type`, or `historic=memorial` with `memorial`) stands on a pedestal. Left out: those on a facade or inside a
building (within 0.8 m of a footprint), those under or over the street level, and those a landmark already draws
(Heroes' Square, Kossuth tér, the Liberty Statue). A figure faces the nearest street or path within 40 m. It is bronze
unless its `material` says stone or marble. The pedestal is grey granite or pale limestone, picked by the id.

- a statue: a figure about 2.4 m tall on a 2.2 m pedestal, scaled to the `height` tag when there is one; a rider when
  the name says "lovas";
- a bust: head and shoulders on a 1.6 m stele;
- a sculpture: a rounded mass on a low plinth.

**The best known**, from their photos (sizes estimated from people beside them):

| Monument | Drawn as |
| --- | --- |
| Savoyai Jenő (Buda Castle terrace) | green bronze rider on a 5.4 m pale pedestal with a band of reliefs, facing the Danube |
| Szent István (Szentháromság tér) | dark bronze rider holding the double cross, on a 5.6 m white pedestal over two steps, facing the Danube |
| Szent Gellért (Gellért Hill) | the bishop raising his cross, 7 m of bronze over a 4.4 m pedestal, before a half-ring of nine columns under an entablature; the waterfall down the hill in front |
| Turul (the palace gate by the funicular) | the bronze bird on a 6 m pillar, wings raised, a sword in its claws |
| Vörösmarty (Vörösmarty tér) | white marble: the poet seated over a ring of sixteen figures on a stepped base |
| Széchenyi and Deák (Széchenyi tér) | standing and seated, dark bronze on tall granite pedestals with seated figures at the corners, facing the Chain Bridge |
| Petőfi, Bem, József nádor, Eötvös, Ady, Semmelweis, Baross, Liszt (×2), Erzsébet királyné, Anonymus (hooded), Hadik, Saint George | their kind of figure (standing, an arm raised, seated, riding), pedestal size and stone, bronze or marble |
| Reagan, Nagy Imre, Columbo, Bud Spencer | life-size, standing on the pavement without a pedestal |

**Church windows**: a church's walls are the plain stone material, without the shader's grid of storeys, so the
churches left to OSM stood as blank blocks. Each church and each of its parts at least 9 m to the eaves gets
round-headed windows 1.7 m wide every 4.5 m along every straight wall at least 6 m long: one row from 3 m up to 10 m
(or 2 m under the eaves), and a second row under the eaves when they are 20 m or higher. A church whose walls a landmark
already paints (the Dohány Street Synagogue's stripes, say) is left alone.

## SideQuest Bar (Klauzál utca 26-28)

`scripts/landmarks_sidequest.py`: the bar that made the map, inside and out, so that people can walk in (it is not
counted among the landmarks above).

**Sources**: thirteen photos by the owner (not published) and the framed evacuation plan by the door (KIÜRÍTÉSI
TERV, ground floor, Fireeng, 2018), photographed at an angle and rectified on its frame (the legend's square signs come
out square within 10%). OSM: the bar's node (found by its website, `sidequest.py`), its building (relation 3476104,
with its courtyard ring) and the gateway's entrance node. What each photo gave:

| Photo | What it settled |
| --- | --- |
| The front at night from across the street | the order along the street: gateway, window A, the plaque pier, the door unit under the stepped hood, the sign pier with the lit beer-mug sign, window B, the corner pier; mullions and transom bars |
| The front from beside the gateway (two) | the gateway's dark doors with octagonal lights and the lit transom, the lattice transom over the door, the fridge behind window A |
| From the top of the stair to the door | the stair runs straight at the door; the diagonal pillar on its left; the white corner of the toilet block on its right, the mezzanine's railing beside the stair; the red pendants and the bulbs; the framed plan on the pier right of the door |
| From the mezzanine's window down onto the bar | the counter from window A towards the mezzanine (orange top, taps), the aisle, the back bar along the gateway's wall (lit glass shelf, bottles, two screens, game boxes); the cellar stair beside it |
| From the landing to the far end | the planked wall with two screens, the glass cabinet against the brick, armchairs and round tables, the orange dome pendant, black beams under the black ceiling |
| The mezzanine | the foosball table and its lit field, the leather sofa against the brick, two floor lamps, the high table, the window onto the bar, the railing |
| From the long room past the chalkboard pillar | the stair's oak treads on a black stringer rising beside the toilet block, the stone-block wall behind it, the sideboard and the map |
| From the long room to the bar | the door and its exit sign, the pier with the plan, the fridge in front of window A, the counter parallel to the back bar, the table by the fridge |
| From the door along the long room | the big screen on the end wall with a speaker each side, TapQuest in front of the pier, the Chesterfield under window B, the diagonal pillar |
| The evacuation plan | the floor plan (below) |
| The corridor | its width (1.1-1.2 m), the oak door on its left, the taupe wall at its mouth, rough painted stone opposite with an exit sign, the tiled toilet straight ahead |
| The darts corner | the recess at the far end: cream brick with a white pilaster, the dartboard and oche mat, a white door in its side wall; the op-art sideboard under the map on the stone wall, the landing overhead |

**Fitting the plan**: the plan has the street at the top and its "you are here" on the pier beside the door, where it
hangs. Its back wall behind the toilets leans 10° to the street, and so does OSM's courtyard edge: that fixed the
orientation (the counter on the gateway's side) and the depth. The width runs from the building's corner on the street
(the party wall with no. 30) to the gateway, 11.5 m, which makes the plan's door 0.9 m; across the street the plan's
scale is a little larger than along it (the rectified plan is not quite true, and the courtyard wall has to stay at
least a voxel thick). Read in the frame below, the plan puts the door at u 6-6.9; the pillar line at v 5.3-6.1 (the
end wall's pier to u 1, the free pillar u 3.3-4.7, the toilet block's corner u 6.75-8.1); the stair at u 5.8-6.75,
v 5.5-8, straight in from the door; the toilet block's wall beside it at u 6.8-7; the corridor along the back wall
(v 8.5-9.6) from u 5 to the toilets; the back wall from v 9.5 (u 5) to 10.5 (u 11); the far end of the long room at
v 11-12; the counter's outline at u 8.6-9.8, v 1.3-5.2, and a stair down to the cellar along the gateway's wall
(u 10.3-11, v 3.2-5.3).

**The frame**: u along the street from the corner (row 3080) towards the gateway, v into the building from the
facade (column 2441), w up from the floor (the pavement at the door, rounded up to a whole metre). Everything people
walk through (the door, the passages, the stair, the corridor) lies on whole metres, so that Minecraft's 1 m blocks keep
it: a half-metre wall beside a way takes its whole block there, and a chair or a stool (one voxel) becomes a post.

**Street front** (the night photos): a rusticated base in the building's own colour to 5 m (CLASSIC: the shader
paints no shop windows on it). From the corner: a pier; window B (u 1-3.5, the Chesterfield behind it); the sign pier
(3.5-4.5) with the lit beer-mug sign projecting 1 m at 3-4 m; the door unit (4.5-7: a side light and the open 1 m
door under a lattice transom, to 3.5 m) under the stepped hood (three steps 0.5, 1 and 1.5 m deep, 3.5-5.5 m: the
corbel of the oriel above); the plaque pier (7-8); window A (8-10.5, the bar's end and the fridge behind it); a pier;
the gateway (11.5-14.5: dark doors with lit octagonal lights under a lit transom). The windows are black-framed, set
back half a metre: a mullion, a transom bar at 2.5 m, glass to 4 m.

**Inside** (from v 1, the front's inner face; 5.5 m to the black ceiling, black beams at 5 m). Half a metre a
character, u across and v down; the gateway continues past u 12:

```
ground floor, 0.5-2 m                      3-5 m: the landing and the mezzanine
     u 0   1   2   3   4   5   6   7   8   9   10  11            u 0   1   2   3   4   5   6   7   8   9   10  11
v  0.0 ############..##########            v  0.0 ########################
       ##=====##===..##=====##G                   ##=====##=====##=====###
v  1.0 #.CCCCC.......ff.c....##            v  1.0 #                     ##
       S.CCCCC..........c..kk##                   #                     ##
v  2.0 S................c..kk##            v  2.0 #                     ##
       S..tt............c..kk##                   #                     ##
v  3.0 S..tt...tt....tt.c..kk##            v  3.0 #                     ##
       S.......tt....tt.c..kk##                   #                     ##
v  4.0 S.tt................kk##            v  4.0 #                     ##
       #.tt................kk##                   #                     ##
v  5.0 #OA....OO..|11OO########            v  5.0 #O     OO     OOwwww####
       #OA....OO..|22OO########                   #O     OO     OO......b#
v  6.0 P..........|33##########            v  6.0 P             ~.......b#
       P..........|44##########                   P             ~.......b#
v  7.0 P.vv.......|55#####...##            v  7.0 P             ~...FF..b#
       P.vv..........#####...##                   P          ~......FF.lb#
v  8.0 P...vv........#####...##            v  8.0 P          ~......FFCCb#
       P...vv......##dd###...##                   P          ~........CCb#
v  9.0 Pn....................##            v  9.0 P          ~........CCb#
       Pn....................##                   P          ~........CCb#
v 10.0 Pntt....#sss#######...##            v 10.0 P       ######..tt...lb#
       Pntt....d###############                   P       ################
v 11.0 #g......d###############            v 11.0 #       ################
       #g..O...################                   #       ################
v 12.0 #bbbObxb################            v 12.0 #bbbbbbb################
```

`#` wall, `.` floor, `=` glass, `G` gateway, `S` the big screen, `P` the planked wall, `b` brick, `O` pillars and the
pilaster, `A` TapQuest, `C` Chesterfield / sofa, `t` tables, `v` armchairs, `n` bench, `g` glass cabinet, `x` the
dartboard, `d` doors (closed), `s` sideboard, `f` fridge, `c` counter, `k` back bar, `|` the stair's stringer and rail,
`1`-`5` its treads (half-metres up), `~` railings, `w` the window onto the bar, `F` foosball, `l` floor lamps; blank: open
to the floor below.

- the long room (u 0.5-4, v 1-12): a dark plank floor; the projection screen on the end wall (v 1.5-4.5, 2-3.5 m up:
  the SideQuest logo on blue, a speaker each side), the Chesterfield against window B, tables and chairs. The pillar
  line at v 5-6: the pier on the end wall with TapQuest in front of it (its screen and marquee towards the windows,
  the pin-up above), the free pillar (u 3.5-4.5, grey over a diagonal, the Red Dead poster) and the corner of the
  toilet block (u 7-8, the chalkboard), with cornice capitals;
- beyond the pillars: the planked wall on the end wall (v 6-11) with two screens, grey velvet armchairs facing them,
  a leather bench and a round pub table; at the far end (v 11-12.5, the darts photo) cream brick with a white
  pilaster, the dartboard under its lamp and the oche mat, a white door in the recess's side wall (u 4-4.5), the glass
  display cabinet in the corner;
- the bar (u 7-11, v 1-5): the counter from window A (u 8.5-9, v 1-4, 1 m high, light wood with an orange top,
  stools, taps), the 1 m aisle behind it, reached at the mezzanine's end, the back bar against the gateway's wall (a
  dark cabinet, a lit glass shelf, bottles, two screens, a row of game boxes); the blue fridge by window A and the
  table in front of it; the exit sign over the door;
- the stair (u 6-7, v 5-7.5), straight in from the door: five oak treads on a black stringer with a rail, 0.5 m a
  step, to a landing at 3 m (u 6-7, v 7.5-10) over the corridor's mouth. The way to the far end and the toilets passes
  it on the left (u 4.5-5.5, 1 m) to the op-art sideboard and the map in a shallow recess of the stone wall;
- under the mezzanine (u 7-11, v 5-10.5, painted stone): the corridor (v 9-10, u 6-9, 1 m wide, 2.5 m high: the
  taupe wall under the landing, then the staff room's oak door, closed) to the toilet (u 9.5-11, v 7-10.5: white tiles
  to 1.5 m, grey floor tiles);
- the mezzanine (u 7-11, v 5.5-10.5, its floor at 3 m, 2.5 m under the ceiling), reached from the landing: the railing
  along its edge over the stair, the window onto the bar in its front wall (u 8-10, 1-2 m above its floor), brick
  behind the leather sofa, the foosball table with its lit field, two floor lamps, a high table;
- light: 35 Edison bulbs (LAMP voxels) 1-2.5 m under the ceiling, red glass pendants by the windows and the
  screen, orange ones at the far end (SIGN, so they glow in their colour); the screens, the fridge and the sign glow
  too. None hangs lower than 3 m, by the pillars, over the stair, the landing or the mezzanine. Their cords are left
  out: at 0.5 m a cord is a post, and dozens of them made the room a forest.

**Walking**: the door is an open 1 m gap; the ways are at least 1 m wide and 2.5 m high; the stair rises one voxel a
step. A breadth-first walk on the voxels (a 0.6 m body on a 0.1 m lattice, walk.ts's step, height and gravity, held
up by any solid voxel column under its footprint) gets from the pavement to the big screen, both ways through the pillar line, the
far end and the darts, the sideboard, behind the counter, up the stair to the landing, the mezzanine, its window and
the sofa, and along the corridor into the toilet, with no place reached only by a drop; the same holds with walk.ts's
own five sample points, and on the 1 m blocks Minecraft gets (there the stair is three one-block steps); every way
rises at most a voxel a step with at least 2.5 m of headroom. By day the hemisphere light reaches inside (only the sun
is shadowed); at night one entry in `meta.lamps` lights the room's floor and walls (its pool spills onto the pavement
too), and the bulbs, pendants, screens and signs glow. The view
`sidequest_inside` ("A SideQuest Bar belülről"; `/lm sidequest_inside` or "bar inside" in Minecraft) stands behind the
counter and looks along the room to the big screen; it carries `walk`, so walk mode chosen there starts on that spot
instead of on the nearest pavement.

**Not built**: the stair down to the cellar behind the counter (where it goes is not known; the aisle stays whole), the
blue chairs stored under the stair, the round table in front of the mezzanine's sofa (the way to the window).

**Not known** (a measured plan would settle them): the windows' and piers' widths (from the photos' proportions); the
room's height (5.5 m assumed) and the mezzanine's (3 m; the stair's thirteen treads say nearer 2.7); the staff room's
door and the toilets' partitions (the plan's thin lines there are hard to read); the courtyard wall's thickness (OSM
puts the courtyard 0.7-1.2 m behind the toilets); where the sideboard and the darts stand (from the photos only); the
counter's length (shortened by a metre at the mezzanine's end to leave a way behind it).

[parl-wiki]: https://en.wikipedia.org/wiki/Hungarian_Parliament_Building
[mb1]: https://en.wikipedia.org/wiki/Margaret_Bridge
[mb2]: https://structurae.net/en/structures/margaret-bridge
[mb3]: https://budappest.com/budapests-most-fascinating-bridge-just-turned-150-and-it-has-quite-the-story-to-tell/
[mb4]: https://aviewoncities.com/budapest/margaret-bridge
[mb5]: https://www.mapillary.com/app/?pKey=1318741037109764
[mb6]: https://www.mapillary.com/app/?pKey=2814668405563016
[mb7]: https://www.mapillary.com/app/?pKey=1047681093953969
[pb1]: https://en.wikipedia.org/wiki/Pet%C5%91fi_Bridge
[pb2]: https://structurae.net/en/structures/petofi-hid
[pb3]: https://hu.wikipedia.org/wiki/Pet%C5%91fi_h%C3%ADd
[pb4]: https://www.mapillary.com/app/?pKey=1502655207602097
[pa1]: https://metalocus.es/en/news/a-concrete-building-a-metal-envelope-puskas-arena-stadium-kozti
[pa2]: https://stadiumdb.com/stadiums/hun/puskas_arena
[pa3]: https://www.nss-sports.com/en/long-form/45574/puskas-arena-history-champions-league-final
[pa4]: https://www.mapillary.com/app/?pKey=1026724767077221
[pa5]: https://www.mapillary.com/app/?pKey=1669108093966349
[pa6]: https://www.mapillary.com/app/?pKey=1377568334002507
[pa7]: https://www.mapillary.com/app/?pKey=1139099811739948
[chain-wiki]: https://hu.wikipedia.org/wiki/Sz%C3%A9chenyi_l%C3%A1nch%C3%ADd
[p1]: https://www.flickr.com/photos/22672616@N06/6238170538
[p2]: https://www.flickr.com/photos/61533954@N00/5936664238
[p3]: https://www.flickr.com/photos/31191642@N05/3751893618
[p4]: https://www.flickr.com/photos/92872827@N00/6978728693
[p5]: https://www.flickr.com/photos/40879668@N08/14550322421
[p6]: https://www.rawpixel.com/image/5906792/photo-image-background-public-domain-free
[c1]: https://www.flickr.com/photos/125267949@N02/18730586459
[c2]: https://www.flickr.com/photos/37473766@N08/6368847359
[c3]: https://www.flickr.com/photos/57915000@N02/50419481788
[c4]: https://www.flickr.com/photos/92224929@N03/11146764573
[l1]: https://www.flickr.com/photos/22490717@N02/7244987354
[l2]: https://www.flickr.com/photos/22490717@N02/7252246776
[e1]: https://www.flickr.com/photos/15887936@N00/5644530976
[f1]: https://www.flickr.com/photos/22490717@N02/7314760410
[f2]: https://www.flickr.com/photos/22490717@N02/7260817042
[f3]: https://www.flickr.com/photos/22490717@N02/7326340764
[m3]: https://www.flickr.com/photos/34120957@N04/6001573321
[mt1]: https://hu.wikipedia.org/wiki/M%C3%A1ty%C3%A1s-templom
[mt2]: https://library.hungaricana.hu/en/view/VaroshazaKiado_0004/?pg=46
[mt3]: https://pp.bme.hu/ar/article/download/7458/6474/12823
[mt4]: https://infostart.hu/belfold/2008/01/14/elado-a-matyas-teplom-teteje-174172
[mt5]: https://www.flickr.com/photos/22490717@N02/7316727046
[mt6]: https://www.flickr.com/photos/22490717@N02/32458227992
[mt7]: https://www.flickr.com/photos/22490717@N02/32459151552
[mt8]: https://www.flickr.com/photos/32628129@N04/7581717864
[mt9]: https://www.flickr.com/photos/37804979@N00/48775868612
[mt10]: https://www.flickr.com/photos/37804979@N00/48775684456
[mt11]: https://www.flickr.com/photos/37804979@N00/48775682616
[mt12]: https://www.flickr.com/photos/37804979@N00/48775866827
[mt13]: https://www.flickr.com/photos/37804979@N00/48775866322
[mt14]: https://www.flickr.com/photos/27137274@N00/4639438993
[mt15]: https://www.flickr.com/photos/12238277@N04/28081702205
[mt16]: https://www.flickr.com/photos/27998473@N02/37171050191
[mt17]: https://www.flickr.com/photos/67515208@N00/17708326486
[mt18]: https://www.flickr.com/photos/67515208@N00/17546845308
[mt19]: https://www.mapillary.com/app/?pKey=151535536911491
[mt20]: https://www.mapillary.com/app/?pKey=293171512295853
[mt21]: https://www.mapillary.com/app/?pKey=732166905876553
[mt22]: https://www.mapillary.com/app/?pKey=1387495522745975
[mt23]: https://www.flickr.com/photos/55267995@N04/41478475935
[mt24]: https://www.flickr.com/photos/9502513@N02/14299331672
[b1]: https://www.flickr.com/photos/78051511@N03/10889731455
[b2]: https://www.flickr.com/photos/8721758@N06/4543651479
[b3]: https://www.flickr.com/photos/8721758@N06/4544245276
[k1]: https://www.flickr.com/photos/70323761@N00/52607938939
[k2]: https://www.flickr.com/photos/70323761@N00/52602521800
[k3]: https://www.flickr.com/photos/70323761@N00/52598371094
[s1]: https://www.flickr.com/photos/13963375@N00/208752054
[s2]: https://www.flickr.com/photos/36520408@N02/7979145609
[h1]: https://www.flickr.com/photos/22490717@N02/7296299580
[h2]: https://www.flickr.com/photos/11473706@N03/11425508795
[mh1]: https://www.flickr.com/photos/90955804@N04/18561323572
[mh2]: https://www.flickr.com/photos/22490717@N02/7335312170
[d1]: https://www.flickr.com/photos/9502513@N02/14262447794
[d2]: https://www.flickr.com/photos/9502513@N02/14076224310
[be1]: https://www.mapillary.com/app/?pKey=1095412846801805
[fc1]: https://welovebudapest.com/cikk/2018/5/4/felujitjak-az-ybl-miklos-altal-150-eve-tervezett-bakats-teri-templomot
[op1]: https://www.mapillary.com/app/?pKey=1026627203694803
[ek-wiki]: https://en.wikipedia.org/wiki/Erkel_Theatre
[ek1]: https://www.flickr.com/photos/65947222@N00/27722112281
[ek2]: https://commons.wikimedia.org/w/index.php?curid=54409407
[ek3]: https://www.mapillary.com/app/?pKey=499781117829836
[ek4]: https://www.mapillary.com/app/?pKey=465729726122093
[ek5]: https://www.mapillary.com/app/?pKey=739727695235948
[ek6]: https://www.mapillary.com/app/?pKey=2116782769191773
[ek7]: https://www.mapillary.com/app/?pKey=28266592059611814
[zoo1]: https://hungaryunlocked.com/visit-budapest-zoo/
[g1]: https://www.flickr.com/photos/89646254@N00/15371106670
[g2]: https://www.flickr.com/photos/89646254@N00/15370726517
[g3]: https://www.flickr.com/photos/89646254@N00/14936563983
[gm]: https://www.mapillary.com/app/?lat=47.48383&lng=19.05221&z=17
[bk1]: https://www.flickr.com/photos/54752966@N06/7329136868
[bk2]: https://www.flickr.com/photos/54752966@N06/7329623894
[bk3]: https://www.flickr.com/photos/83641890@N00/2345770960
[bkm]: https://www.mapillary.com/app/?lat=47.48143&lng=19.05547&z=17
[nm1]: https://www.flickr.com/photos/14993459@N08/3358153466
[nm2]: https://www.flickr.com/photos/14993459@N08/3357307061
[nm3]: https://www.flickr.com/photos/85465568@N02/8314791277
[nmm]: https://www.mapillary.com/app/?lat=47.49119&lng=19.06294&z=17
[kvm]: https://www.mapillary.com/app/?lat=47.48997&lng=19.06115&z=18
[rk1]: https://commons.wikimedia.org/wiki/File:R%C3%A1k%C3%B3czi_T%C3%A9r_Market_Hall_(a).jpg
[rk2]: https://commons.wikimedia.org/wiki/File:R%C3%A1k%C3%B3czi_t%C3%A9ri_v%C3%A1s%C3%A1rcsarnok._V%C3%ADg_utcai_homlokzat,_r%C3%A9szlete._-_Budapest.JPG
[rk3]: https://commons.wikimedia.org/wiki/File:R%C3%A1k%C3%B3czi_t%C3%A9r,_v%C3%A1s%C3%A1rcsarnok,_f%C5%91bej%C3%A1rat._Fortepan_88992.jpg
[rk4]: https://www.mapillary.com/app/?pKey=288411932833622
[rk5]: https://www.mapillary.com/app/?pKey=1976873746380832
[rk6]: https://www.mapillary.com/app/?pKey=1292517789086951
[rk7]: https://www.mapillary.com/app/?pKey=476312976982985
[rk8]: https://www.mapillary.com/app/?pKey=1103762735075886
[rkm]: https://www.mapillary.com/app/?lat=47.49298&lng=19.07325&z=18
[bl1]: https://telex.hu/belfold/2023/06/06/corvin-aruhaz-leleplezese-blaha-lujza-ter-rekonstrukcio-2
[bl2]: https://www.mapillary.com/app/?pKey=1195806995821216
[bl3]: https://www.mapillary.com/app/?pKey=1598710425293187
[bl4]: https://www.mapillary.com/app/?pKey=1029646523388230
[bl5]: https://www.mapillary.com/app/?pKey=1053334867305183
[bl6]: https://www.mapillary.com/app/?pKey=1092041573514324
[bl7]: https://www.mapillary.com/app/?pKey=1246565777594022
[bl8]: https://www.mapillary.com/app/?pKey=992939140270935
[bl9]: https://www.mapillary.com/app/?pKey=1165499785902890
[blm]: https://www.mapillary.com/app/?lat=47.49606&lng=19.0698&z=18
[a1]: https://www.flickr.com/photos/66537520@N00/136588164
[bt1]: https://www.flickr.com/photos/62201675@N00/267612913
[a38m]: https://www.mapillary.com/app/?lat=47.47651&lng=19.06296&z=17
[btm]: https://www.mapillary.com/app/?lat=47.49691&lng=19.04684&z=17

[p7]: https://www.flickr.com/photos/40467171@N00/6081095951
[p8]: https://www.flickr.com/photos/22490717@N02/7270463792
[p9]: https://www.flickr.com/photos/72558920@N00/2477047886
[p10]: https://www.mapillary.com/app/?pKey=1006909428488807
[p11]: https://www.mapillary.com/app/?pKey=1357774136497197
[ks1]: https://www.flickr.com/photos/10164913@N02/5266676848
[ks2]: https://www.flickr.com/photos/106447493@N05/34162525754
[ks3]: https://www.flickr.com/photos/70323761@N00/52599635959
[ks4]: https://www.flickr.com/photos/129231073@N06/37766924624
[ks5]: https://www.mapillary.com/app/?pKey=1263606861320493
[ks6]: https://www.mapillary.com/app/?pKey=1028282685814111
[ks7]: https://www.mapillary.com/app/?pKey=965541029617451
[g4]: https://www.flickr.com/photos/76641279@N04/15285489791
[g5]: https://www.flickr.com/photos/76641279@N04/15285490081
[wvv]: https://github.com/stared/warsaw-vibe-voxel
[hl1]: https://commons.wikimedia.org/w/index.php?curid=15389720
[hl2]: https://www.flickr.com/photos/55267995@N04/42381152771
[hl3]: https://www.flickr.com/photos/126280769@N05/14830559187
[hl4]: https://www.flickr.com/photos/22890158@N08/2337737826
[hl5]: https://manchesterhistory.net/architecture/1970/budahilton.html
[hl6]: https://library.hungaricana.hu/hu/view/VizugyiKonyvek_019/?pg=72
[hl7]: https://www.mapillary.com/app/?pKey=1416967025951106
[hl8]: https://www.mapillary.com/app/?pKey=1897257410808751
[hl9]: https://www.mapillary.com/app/?pKey=2428637407500482
[hlm]: https://www.mapillary.com/app/?lat=47.50255&lng=19.03393&z=18
[ct1]: https://en.wikipedia.org/wiki/Citadella
[ct2]: https://telex.hu/belfold/2026/04/05/citadella-felujitas-gellerthegy-atadas
[ct3]: https://buildingconnections.eu/en/mi-epul/2025/05/08/ujjaszuleto-erod-latvanyos-munkalatok-a-citadellan/
[ct4]: https://welovebudapest.com/cikk/2025/07/16/citadella-szabadsag-szobor-kereszt-rekonstrukcio-2025/
[ct5]: https://welovebudapest.com/cikk/2026/04/16/citadella-felujitas-gellert-hegy/
[ct6]: https://turizmus.com/cikk/programok/citadella-megujult-nyitas-zold-oazis-kulonleges-kiallitas-gellert-hegy
[ct7]: https://magyarnemzet.hu/belfold/2026/04/megujult-citadella-atadas-gellert-hegy
[ct8]: https://telex.hu/belfold/2022/03/16/citadella-zaszlo-rud-nemzeti-lobogo
[ct9]: https://www.mapillary.com/app/?pKey=1587874496467201
[ct10]: https://www.mapillary.com/app/?pKey=2101596563767178
[ct11]: https://www.mapillary.com/app/?pKey=905882832282586
[ct12]: https://www.mapillary.com/app/?pKey=1069276079299316
[ct13]: https://www.mapillary.com/app/?pKey=1692614062037544
[ct14]: https://www.mapillary.com/app/?pKey=2185087989108128
[ct15]: https://www.mapillary.com/app/?pKey=1423567003065467
[ct16]: https://www.mapillary.com/app/?pKey=825251471410503
[ct17]: https://dailynewshungary.com/citadella-reopening-budapest-top-panorama-free-park-exhibition
[ct18]: https://infostart.hu/belfold/2022/03/16/az-orszag-legnagyobb-nemzeti-lobogoja-disziti-marcius-15-tol-a-citadellat-kepek
[lc1]: https://telex.hu/belfold/2025/07/14/gellert-hegy-szabadsag-szobor-kereszt
[lc2]: https://444.hu/2024/08/12/kereszt-kerul-a-gellert-hegyen-a-szabadsag-szoborra
[lc3]: https://www.mapillary.com/app/?pKey=1080850971102692
