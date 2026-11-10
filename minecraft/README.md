# Budapest in Minecraft

The voxel map as a Minecraft server at **mc.side-quest.bar**, 1 block = 1 m, for Java and Bedrock players. Nobody can
change it. Players fly over the city, teleport to the landmarks and can't get hurt. It is a deployment of its own,
separate from the web viewer's (Cloudflare Pages, `./bv publish-web`): they share the map data and nothing else.

```
./bv minecraft             # the world from web/public/data -> build/minecraft (~5 min); the plugin if it changed
./bv server                # run it on this machine
./bv publish-minecraft     # upload it to the server (settings: ~/.config/voxelpest/minecraft.env)
```

## What's in here

| Path | What it is |
| --- | --- |
| `../scripts/minecraft.py` | The converter: the viewer's level-2 tiles (1 m cells) → Anvil region files, `landmarks.yml`, `map.yml`, `preview.png` in `build/minecraft/` (~5 min, 411 MB, 105 000 chunks) |
| `../scripts/minecraft_blocks.py` | Measures the colours of the blocks the converter may use from the game's own textures → `scripts/minecraft_blocks.json`. Run it again for a new Minecraft version |
| `../scripts/publish_minecraft.sh` | Publishing (`./bv publish-minecraft`): builds the world and the plugin (if changed), uploads them with the server's files and settings, starts the container |
| `plugin/` | The voxelpest Paper plugin (Java 25, Maven). `voxelpest.jar` is the built copy that gets uploaded |
| `server/start.sh` | The container's entrypoint: swaps a new map in, copies the plugin, sets what the image doesn't (no End, Geyser's Floodgate login), picks the plugins the image fetches, then runs the image's own start |
| `server/geyser-config.yml` | Geyser's first settings (Floodgate login, so Bedrock players need no Java account) |
| `docker-compose.yml` | One container, `voxelpest-minecraft`, in [itzg/minecraft-server](https://docker-minecraft-server.readthedocs.io/) (`stable-java25`): it downloads Paper and the plugins (newer builds at every start), writes `server.properties` from the settings, runs Paper with Aikar's flags. `./bv server` runs the same file locally |
| `minecraft.env.example` | The settings, to copy to `~/.config/voxelpest/minecraft.env` |

On the server, everything is in one directory (`MC_DIR`, `/srv/voxelpest-minecraft` by default):

```
docker-compose.yml  .env  server/      uploaded by publish_minecraft.sh (.env from your minecraft.env)
map/                the newest map: world/, landmarks.yml, map.yml, plugins/voxelpest.jar, plugins/config.yml
data/               the running server: world, player data, other plugins' settings, logs
```

## First time

1. **DNS**: an A record for `mc.side-quest.bar` pointing to the server's public IP. Bedrock doesn't read SRV records,
   so the plain A record is what both editions use.
2. **Firewall**: open **25565/tcp** (Java) and **19132/udp** (Bedrock) to the internet, in OVH's network firewall and
   in the machine's own (`ufw allow 25565/tcp`, `ufw allow 19132/udp`). The plugin's status port (8765) is bound to
   127.0.0.1 unless `STATUS_BIND` says otherwise.
3. **Settings**: `cp minecraft/minecraft.env.example ~/.config/voxelpest/minecraft.env`, then set `MC_HOST` (your
   ssh target, a Tailscale name works), `EULA=true` (you agree to the [Minecraft EULA](https://aka.ms/MinecraftEULA))
   and check the addresses. The server needs Docker with the compose plugin, and your ssh user must be allowed to run it.
4. `./bv publish-minecraft`. The first start downloads Paper, the plugins and Mojang's server files (a minute or two).
   Then `docker logs -f voxelpest-minecraft` ends with `Done (…)! For help, type "help"`.
5. Console: `docker exec -it voxelpest-minecraft rcon-cli`, or `docker attach voxelpest-minecraft` (leave with Ctrl-P
   Ctrl-Q; typing `stop` restarts the server). `op <name>`
   for the admin command `/voxelpest`.

## Updating the map

Change the map as usual (landmarks, `./bv voxelize`), then:

```
./bv publish-minecraft                  # world (~5 min), upload, done
./bv publish-minecraft --no-build       # upload the last build
./bv publish-minecraft --config-only    # only the server's settings and messages
```

`map.yml` is uploaded last. The plugin checks it every 30 seconds, and when its build time differs from the running
map's:

- online players get a 60-second countdown in chat, then a message saying the map is being updated;
- the server stops and Docker starts it again;
- `start.sh` sees the new `map.yml` and replaces the overworld's regions;
- about half a minute later the new map is up.

With nobody online it restarts straight away. Anything built in the game is replaced at each update, since the map is
the source.

The plugin's settings and messages are `plugin/src/main/resources/config.yml`. The server reads the uploaded copy
(`map/plugins/config.yml`) and reloads it within 30 s, without a restart. The plugin itself is rebuilt by
`./bv minecraft` and `./bv publish-minecraft` when its sources are newer than `voxelpest.jar`, if Maven and JDK 25
are installed (`./bv plugin` rebuilds it by hand).

## Run it locally

```
./bv server
```

It runs the real server's `docker-compose.yml` in Docker or podman, on local folders (`build/minecraft` as the map,
`build/mc-data` as the server's, kept as your files). It builds the world first if `build/minecraft` isn't there, asks
once whether you agree to the Minecraft EULA, starts the container and follows its log (Ctrl-C leaves it running).
Join at `localhost` (Bedrock: the machine's LAN address, port 19132). `./bv server console` is the console (rcon-cli),
`./bv server logs` the log again, `./bv server stop` stops it. When `./bv minecraft` writes a new map, the server
stops within 30 s and the container starts again on it. Settings such as `MEMORY` (2G), `ONLINE_MODE` or `MC_VERSION`
can go in `~/.config/voxelpest/env`. Java and Maven are only needed to rebuild the plugin (`./bv plugin`).

## In the game

| Command | |
| --- | --- |
| `/lm` | the landmarks, clickable (aliases `/landmark`, `/warp`) |
| `/lm <name>` | teleport there, flying: `/lm opera`, `/lm hosok`, `/lm Halászbástya`, `/lm chain`. Ids, English and Hungarian names, accents optional |
| `/fly` | flying on or off (on when you join; double-jump to take off) |
| `/flyspeed 1-10` | flying speed (3 when you join) |
| `/spawn` | back to the start: Kossuth tér, by the flag in front of the Parliament (also `/lm flag`) |
| `/bar` | straight to SideQuest Bar's door on Klauzál utca, with what the bar is (`/lm sidequest` shows it from above) |
| `/map` | the web viewer's link |
| `/terms` | the links to SideQuest Bar's Terms of Service and Privacy Policy, which cover this server (aliases `/privacy`, `/rules`, `/tos`); the welcome message links them too |
| `/voxelpest reload` | (op) reload the settings and landmarks |

The landmarks are the web viewer's views (`meta.json`), from the same camera positions: add a view in
`scripts/voxelize.py` and it becomes a teleport. Hungarian names are in `ALIASES` in `scripts/minecraft.py`. One more,
`bar`, stands on the pavement at the bar's door (`meta.sidequest.door`, from `scripts/sidequest.py`): `/bar` and
`/lm bar` go there.

**Protection** (`Protection.java`): players join in adventure mode and can't break, place, use buckets or trample.
Fire, explosions, liquids flowing, leaves decaying, grass spreading, ice, growth, pistons and mob griefing are all
cancelled. Nobody takes damage or gets hungry, mobs don't spawn and the weather stays clear. A world border and a soft
edge keep players on the map. The sun follows Budapest's clock (`time: real`; `day` and `cycle` are the other choices).
Players with the `voxelpest.build` permission (nobody by default; give it with a permissions plugin such as LuckPerms)
can change blocks.

**Logs and privacy**: the server's logs hold players' IP addresses, chat and commands. The privacy policy
(side-quest.bar/privacy, sections 3.9 and 10) says they are kept for 90 days, so the plugin deletes the rotated
`logs/*.log.gz` older than `logs.keep-days` (config.yml) at start and once a day. Change the two together.

**Versions**: the server runs Minecraft 26.3 (Paper). ViaVersion and ViaBackwards let other Java versions in, and
Geyser and Floodgate let Bedrock players in (phones, tablets, Windows) on port 19132 without a Java account. Consoles
can't add servers without workarounds. All of them are fetched at every start when there's a newer build. A new
Bedrock release usually needs a new Geyser, so restart the container after one: `docker restart voxelpest-minecraft`.

To move to a new Minecraft version: set `MC_VERSION` in minecraft.env, run `uv run python scripts/minecraft_blocks.py
<version>` (the block colours), bump `paper.version` in `plugin/pom.xml` and `api-version` in `plugin.yml`, then
`./bv publish-minecraft`. Paper upgrades older chunks by itself, so the world works across versions anyway.

## The web viewer's Minecraft card

`web/src/ui/promo.ts` has a **Play in Minecraft** card (top left): the player count, refreshed every 30 s, and a
panel with how to join (the Java address with a copy button, the Bedrock address and port with an "Add to
Minecraft" link, `minecraft://?addExternalServer=...`, and the commands). It is behind a feature flag, off by
default: `MINECRAFT=true` in the viewer's web.env turns it on (`VITE_MINECRAFT` at build time); `?minecraft=1` or
`?minecraft=0` in the URL overrides it. With it off, the viewer makes no requests about the server.

The count comes from `MC_STATUS_URL` in web.env if set: the plugin's `GET /status`
(`{"online":3,"max":50,"version":"26.3",...}`, CORS open) published by you, e.g. behind an HTTPS proxy with
`STATUS_BIND`/`STATUS_PORT` in minecraft.env. Otherwise api.mcstatus.io asks the server. In `./bv web`, Vite proxies
`/api/minecraft` to a server on this machine (`./bv server`), so `?minecraft=1` shows the local count.

## How the conversion works (`scripts/minecraft.py`)

- **Coordinates**: x = the grid's column, z = its row (Minecraft's north is the grid's −row, 41.5° west of true
  north), y = metres above sea level − 36. The map's base (94 m) is y 58 and the Danube's surface is y 62. Below the
  map there's stone, then deepslate under y 0, then bedrock at −64. New players start on Kossuth tér by the flag, facing the Parliament (`spawn: flag` in config.yml).
- **Blocks**: every palette colour becomes the nearest block in CIELAB from a family chosen by its material, using
  the colours that `minecraft_blocks.py` measured from the game's textures:
  - facades: concrete, terracotta, wool, stone, sandstone, planks;
  - roofs: terracotta, tiles, bricks, copper;
  - leaves: persistent;
  - lamps: froglights and lanterns;
  - water: still water, which the plugin keeps from flowing.

  No pink, magenta or purple blocks are used.
- **Windows**: OSM's plain walls get windows the way the viewer's shader draws them: stained glass panes in front of a
  dark room, some of them lit (shroomlight, froglights) and glowing at night. Glass buildings get curtain walls with
  spandrels.
- **Thin things** (posts, spires, cables, railings: the viewer's detail voxels) become walls joined to their
  neighbours, iron bars or lanterns.
- The chunks are written lit-less (`isLightOn: 0`); the server lights them the first time they load.

What 1 m blocks lose against the viewer's 0.5 m voxels: thin cornices and window frames, stepped rather than smooth
roofs, and some railings.
