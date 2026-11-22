# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.6...HEAD
[1.0.6]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/SideQuestBar/voxelpest/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/SideQuestBar/voxelpest/releases/tag/v1.0.3
