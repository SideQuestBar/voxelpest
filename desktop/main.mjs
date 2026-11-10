// Budapest in voxels as a desktop app: the static site (web/dist) in an Electron window. Electron rather than a
// system webview for WebGPU: Chromium has it on Linux (behind a switch, on Vulkan), WebKitGTK has none.
//
// The site is a resource directory next to the app (out of the asar archive), served from disk by the app's own
// voxelpest:// scheme, where a missing file is a real 404: the mesher worker reads one as an empty tile.
// ./bv desktop dev sets VOXELPEST_DEV_URL and the window loads the viewer's dev server instead.
import { spawn } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { app, BrowserWindow, ipcMain, Menu, protocol, shell } from 'electron';
import electronUpdater from 'electron-updater';  // CommonJS: no named exports
import { linkEnv, mime, parseArgs, resolve, sameOrigin } from './site.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const SCHEME = 'voxelpest';
const TITLE = 'Budapest in voxels';
const DEV_URL = process.env.VOXELPEST_DEV_URL;
// packaged: resources/web (electron-builder's extraResources); run from the source tree: the site's build
const SITE = app.isPackaged ? path.join(process.resourcesPath, 'web') : path.resolve(here, '../web/dist');
// argv is [binary, ...] when packaged, [electron, '.', ...] from the source tree
const args = parseArgs(process.argv.slice(app.isPackaged ? 1 : 2));
// links the app hands to the desktop (minecraft:// is the Minecraft card's "Add to Minecraft")
const OPENABLE = new Set(['http:', 'https:', 'mailto:', 'minecraft:']);

const start = new URL(DEV_URL ?? `${SCHEME}://localhost/`);
if (args.query.length) start.search = args.query.join('&');

// WebGPU: Chromium keeps it behind this switch on Linux, where Dawn runs it on Vulkan. Not the often-quoted
// --enable-features=Vulkan as well: that is Vulkan for compositing, which native Wayland refuses (the GPU process
// crashed in a loop: "'--ozone-platform=wayland' is not compatible with Vulkan")
app.commandLine.appendSwitch('enable-unsafe-webgpu');

// a standard, secure scheme: an origin of its own, module workers, fetch, a secure context for WebGPU
protocol.registerSchemesAsPrivileged([{
  scheme: SCHEME,
  privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true, codeCache: true },
}]);

async function serve(request) {
  const file = resolve(SITE, new URL(request.url).pathname);
  if (!file) return new Response(null, { status: 404 });
  try {
    return new Response(await readFile(file), { headers: { 'content-type': mime(file) } });
  } catch (err) {
    // a tile the map doesn't have is empty ground: the worker expects a plain 404 for it
    if (err.code === 'ENOENT' || err.code === 'EISDIR' || err.code === 'ENOTDIR') return new Response(null, { status: 404 });
    console.error(`voxelpest: ${file}: ${err.message}`);
    return new Response(null, { status: 500 });
  }
}

function openExternal(raw) {
  let url;
  try { url = new URL(raw); } catch { return; }
  if (!OPENABLE.has(url.protocol)) return;
  if (process.platform !== 'linux') return void shell.openExternal(url.href);
  const { env, cwd } = linkEnv(process.env);
  const child = spawn('xdg-open', [url.href], { env, cwd, detached: true, stdio: 'ignore' });
  child.on('error', (err) => console.error(`voxelpest: can't open ${url.href}: ${err.message}`));
  child.unref();
}

const isApp = (url) => {
  try { return sameOrigin(new URL(url), start); } catch { return false; }
};

// what the viewer asks through the preload's window.voxelpestDesktop (web/src/ui/desktop.ts); only the app's pages
ipcMain.handle('version', (e) => (isApp(e.senderFrame?.url) ? app.getVersion() : ''));
ipcMain.handle('quit', (e) => { if (isApp(e.senderFrame?.url)) app.quit(); });
ipcMain.handle('fullscreen', (e, on) => {
  const win = BrowserWindow.fromWebContents(e.sender);
  if (!win || !isApp(e.senderFrame?.url)) return false;
  if (typeof on !== 'boolean') return win.isFullScreen();
  const want = on || args.fullscreenAlways;  // fullscreen=always: there is no going back to a window
  win.setFullScreen(want);
  return want;
});

function createWindow() {
  const win = new BrowserWindow({
    title: TITLE,
    width: 1440, height: 900, minWidth: 480, minHeight: 360,
    // full screen like a game, except on the dev server; F11 or the menu leave it, unless fullscreen=always
    fullscreen: !DEV_URL || args.fullscreenAlways,
    // the loading screen's colour (web/index.html), so the window doesn't flash white before it paints
    backgroundColor: '#c9d3dc',
    icon: path.join(here, 'icons/icon.png'),
    webPreferences: { preload: path.join(here, 'preload.cjs'), contextIsolation: true, sandbox: true, spellcheck: false },
  });
  // the compositor's own full-screen key, say
  if (args.fullscreenAlways) win.on('leave-full-screen', () => win.setFullScreen(true));
  // links leave the app for the desktop's browser; with nolink=true they go nowhere
  win.webContents.on('will-navigate', (e) => {
    if (isApp(e.url)) return;
    e.preventDefault();
    if (!args.nolink) openExternal(e.url);
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (!args.nolink && !isApp(url)) openExternal(url);
    return { action: 'deny' };
  });
  if (DEV_URL) {
    win.webContents.on('before-input-event', (e, input) => {
      if (input.type === 'keyDown' && input.key === 'F12') win.webContents.toggleDevTools();
    });
  }
  void win.loadURL(start.href);
}

// Updates from the project's GitHub releases (package.json's build.publish; .github/workflows/desktop.yml makes one
// per version tag, with the latest-linux.yml the updater reads). Only the AppImage can replace itself: it downloads
// the new one in the background (the blocks that changed, by the release's blockmap) and swaps the file when the app
// quits, so the next start is the new version. Nothing is asked or shown; a failure (offline, a read-only AppImage)
// is a line on stderr and the app stays as it is. update=false turns it off.
function update() {
  if (!app.isPackaged || !process.env.APPIMAGE || !args.update) return;
  const { autoUpdater } = electronUpdater;
  autoUpdater.logger = {
    info: () => {}, debug: () => {},
    warn: (m) => console.error(`voxelpest: update: ${m}`),
    error: (m) => console.error(`voxelpest: update: ${m}`),
  };
  autoUpdater.on('update-downloaded', (info) => console.error(`voxelpest: update: ${info.version} installs on quit`));
  autoUpdater.checkForUpdates().catch(() => {});  // already logged
}

// no menu bar, and none of its shortcuts (reload, zoom, devtools): Esc and F11 belong to the viewer
Menu.setApplicationMenu(null);
app.on('window-all-closed', () => app.quit());
app.whenReady().then(() => {
  protocol.handle(SCHEME, serve);
  createWindow();
  update();
});
