# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Map: grown to 8.6 × 8.6 km: 1 km more at the top takes in all of Margaret Island up to Árpád Bridge, Újlipótváros and
  Rózsadomb, and 0.5 km more on the left the whole track field of Kelenföld station and the M4 depot. A `margitsziget`
  view.

### Changed

- Viewer: the site's map tiles come four to a file (the four that share a parent, which the viewer always asks for
  together): the same bytes in a quarter of the requests, and ~6 000 files instead of ~24 000, under Cloudflare Pages'
  20 000.

### Fixed

- Map: a row of the WestEnd roof garden's deck furniture stood 2.3 km south of it since the map grew on 22 November.
- Map: St Stephen's Basilica follows OpenStreetMap's new outline of it (it was skipped with the fresh data).

## [1.1.1] - 2026-11-26

### Changed

- Viewer: the FPV drone always stays first person: a drag or the wheel no longer swings its camera round.

### Fixed

- Viewer: on a phone held sideways the plane's and the helicopter's instruments covered the aircraft; they are now
  small dials in the bottom row, between the bar and Places.

## [1.1.0] - 2026-11-26

### Added

- Map: Heroes' Square redone, and the Museum of Fine Arts, Műcsarnok and Vajdahunyad Castle modelled.
- Map: Sándor Palace and the BME CH building modelled.
- Map: Corvin Cinema, Corvin Plaza, the Museum of Applied Arts, Semmelweis University, the Slovak Lutheran church,
  St Margaret's Church, Arena Mall and the MTK Sportpark modelled.
- Map: extended 0.5 km west and 1.5 km south, taking in Déli station, more of Ferencváros and the National Athletics
  Centre.
- Map: extended a further 2.3 km west and 1 km south, taking in Kelenföld station and Etele tér, Lágymányos, Sas-hegy
  and the whole of Népliget.
- Map: the Ludovika Arena, Budapest Park, the Groupama Aréna, the Telekom Campus, the MVM Dome, Müpa, the MOL Campus,
  the Kelenföld power station, Bikás Park, Kelenföld station, Etele Plaza, the BME campus, Allee, the Szent Margit
  Gimnázium, MOM Park, the Szilágyi Dezső tér church, Batthyány tér (St Anne's and the market hall) and St Teresa of
  Avila modelled, with views for them.
- Map: the zoo's Great Rock and Palm House, the House of Music, St Elizabeth's and the Greek Catholic church on Rózsák
  tere, Szent József on Horváth Mihály tér, Déli station and the National Athletics Centre modelled.
- Viewer: fly mode, with an FPV drone, a small plane and a helicopter, and their OSD and instruments.
- Viewer: the changelog, opened from the version in the About box.

### Fixed

- Map: the Gellért baths' garden round the pools is paved and planted.
- Map: Bartók Béla út lowered to the level of Szent Gellért tér.

### Changed

- Viewer: in fly mode a drag swings the camera round the aircraft and the wheel zooms; swung round, the drone is seen
  from outside. It swings back behind on its own.
- Viewer: the aircraft can land: a touchdown on anything flat and dry is a landing if gentle and a crash if too hard
  (or on the river). Before, touching the ground at all counted as a crash.
- Viewer: after a crash the plane and the helicopter come back well above where they last flew clear.
- Viewer: the plane holds its attitude when the stick is let go, so the attitude sets its speed; it can be slowed for a
  landing.
- Viewer: the drone's video feed only glitches slightly now and then, instead of breaking up with distance and buildings.
- Viewer: fly mode reworked on real flight physics. The plane flies on lift, drag and angle of attack and holds a
  trimmed speed; the helicopter trades height for speed as it leans, with translational lift and a collective that stays
  put, and is quicker (about 145 kt flat out); the drone has thrust along its body and no height hold. Vertical speed
  now comes from the physics, as on a real aircraft.
- Viewer: the drone is seen through an analogue video feed that grains, tears and snows as its link weakens; its
  low-battery warning is gone.
- Viewer: a sense of speed in the air: the chase camera widens, pulls back, leans and shakes with speed, and streaks
  flow past.
- Viewer: the plane's and the helicopter's instruments redrawn like real ones, with a turn coordinator, a three-hand
  altimeter, a lagging vertical speed indicator, and a tachometer or torque and rotor rpm.
- Viewer: the map takes about a third of the memory it did (each voxel face is 16 bytes instead of 48, and the lamp
  and tree maps are smaller), so phones hold more of it in detail.
- Viewer: only what changed is drawn: shadows are redrawn when the sun, the view or the tiles change, and a still map
  is drawn about 30 times a second, which spares the battery.
- Docs: the README covers fly mode.
- Docs: the new landmark modules and the two map fixes documented.
- Map: the A38's gangways rebuilt as covered steel footbridges from the quay down to the ship.
- Map: Rákóczi Bridge's red lighting masts stand on the deck, leaning over the road, instead of blocks in the river.
- Map: the grid starts 2816 m further west, and ends 128 m short of where it did in the east; the landmark modules' coordinates moved with it.

## [1.0.6] - 2026-11-11

### Fixed

- Dissolving tiles no longer turn black on NVIDIA GPUs (the discard now happens after `fwidth()`).

## [1.0.5] - 2026-11-11

### Added

- Full offline mode for the web version.
- Admin command on the Minecraft server to set the time of day.

### Fixed

- The MOL Bubi mention removed from the bicycle texture and the screenshot.

### Changed

- Docs: the option to hide the UI documented.

## [1.0.4] - 2026-11-10

### Added

- Better Open Graph tags and a GitHub link.

### Fixed

- Link autofocus in the about modal.
- The cursor is hidden in fullscreen when a gamepad is in use.

## [1.0.3] - 2026-11-10

### Added

- The desktop app is built on GitHub Actions and updates itself from GitHub releases.
- License.

### Changed

- README updated with screenshots and a banner.

## 1.0.2 - 2026-11-10

### Added

- Minecraft players are teleported onto the ground beside each landmark.
- The Minecraft server can run under a deployment tool, with configurable mount paths.

### Fixed

- The mode buttons respond to taps on phones, and walking and driving no longer hang on slow frames.
- The current plugin config is always copied into the local Minecraft server.
- Vehicles no longer sink through the street after clipping a post, and fall rescues are throttled.

### Changed

- README trimmed, with the detailed sections moved into `docs/`.

## 1.0.1 - 2026-11-10

### Fixed

- Crash recovery and lower memory use, for stability on iOS.

## 1.0.0 - 2026-11-10

### Added

- Initial release.
- Version numbers on the about page.

[Unreleased]: https://github.com/SideQuestBar/voxelpest/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/SideQuestBar/voxelpest/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.6...v1.1.0
[1.0.6]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/SideQuestBar/voxelpest/releases/tag/v1.0.3
