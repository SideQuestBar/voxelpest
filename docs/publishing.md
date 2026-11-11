# Publishing

The web viewer and the Minecraft server are two separate deployments built from the same map; the desktop app is a
local build.

## Web viewer

A static site on Cloudflare Pages. `./bv publish-web` builds it (`web/dist`, about 8 800 files
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

## Minecraft server (`minecraft/`)

The same map at 1 block = 1 m, for Java and Bedrock players, at
**mc.side-quest.bar**. Nobody can break it; there are commands to fly and to teleport to the landmarks (`/lm opera`).
`./bv publish-minecraft` builds the world and uploads it; the server restarts on the new map by itself. Settings:
`~/.config/voxelpest/minecraft.env` (from `minecraft/minecraft.env.example`). The setup, the commands, how
updates reach the server and how the conversion works are in [minecraft/README.md](../minecraft/README.md).

Neither depends on the other: they can run on different machines, and either can be published alone.

## Analytics

Analytics are off by default. With `UMAMI_URL` (your [Umami](https://umami.is) server) and `UMAMI_ID` (the website's id) in `web.env`, the published site loads Umami's script and reports visits and what people do: the mode, the vehicle, the places chosen, the date, time and weather set, the bar's card and pin, the help, the menu. It never sends a position (the locate button reports only whether it found you on the map), nor the page's query string, and it respects the browser's Do Not Track.


## Desktop app (`desktop/`)

The web viewer in an [Electron](https://www.electronjs.org) window, for WebGPU
(Chromium has it on Linux, on Vulkan; the system webviews don't), as a Linux AppImage that carries the map (about
240 MB, the map and Chromium). `./bv desktop` builds the site as `./bv site` does, with the same settings, and writes
`build/voxelpest-<version>-x86_64.AppImage`; nothing is uploaded. The app starts
full screen. Esc, or a controller's Menu button, opens a menu to leave full screen (F11 too), go to SideQuest Bar or
quit. Its bottom bar names the map's data sources where the website shows the help line; the help (the ? button)
covers the map, walking and driving for the mouse and keys, a touch screen or a controller. The viewer's URL
parameters can be given as arguments: `./voxelpest-1.0.0-x86_64.AppImage view=parliament hour=20 lang=hu`. Links
open in the desktop's browser. For a kiosk, `fullscreen=always` takes leaving full screen out of the menu (and the
app refuses it), and `nolink=true` turns every link out of the app into plain text (and the app opens none). `ui=0` hides everything
over the picture, as on the website (`./voxelpest-1.0.0-x86_64.AppImage ui=0 view=parliament`); Esc still opens the
menu to quit.
`./bv desktop dev` runs it on the viewer's dev server, in a window, with devtools on F12. It runs on Wayland as it
is; if it ever stays on the loading screen, `--ozone-platform=x11` runs it through XWayland.

**Releases and updates.** `.github/workflows/desktop.yml` builds the AppImage on GitHub Actions the same way. Pushing
a version tag makes a GitHub release of it:

```
# bump "version" in desktop/package.json and web/package.json (the workflow checks both against the tag), commit
git tag v1.0.3 && git push origin master v1.0.3
```

The release carries the AppImage and `latest-linux.yml`, the feed the installed apps read: on start the app asks
GitHub for the latest release, downloads a newer AppImage in the background (only the blocks that changed) and
replaces its own file when it quits, so the next start is the new version. The file takes the new version's name
when the old one had the version in it; an AppImage renamed to, say, `voxelpest.AppImage` keeps its name. Nothing is
asked or shown, and `update=false` keeps a copy (a kiosk's) at its version. This needs the repository's releases to
be public, and only the AppImage run as a file updates itself. A tag with a hyphen (`v1.1.0-beta.1`) makes a
pre-release, which the installed apps pass over. Run by hand (Actions, desktop, Run workflow), the workflow only
builds; the AppImage is the run's artifact. The site's settings come from the repository's Actions variables, all
optional: `BAR_URL`, `MINECRAFT`, `MC_ADDRESS`, `MC_STATUS_URL`, `UMAMI_URL`, `UMAMI_ID`.
