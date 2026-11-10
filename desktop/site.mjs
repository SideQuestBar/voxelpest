// The desktop app's plain logic, apart from Electron so that `node --test` can check it: where a request's path leads
// inside the site, what a file is served as, what the arguments say, which links stay in the app, and the
// environment a link opens in.
import path from 'node:path';

/** The file a request's path names under `root`, or null if it tries to leave it. A directory means its index.html.
 * Decoded first, then split, so that `..%2f` is caught as well as `..`. */
export function resolve(root, pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }
  const parts = [];
  for (const part of decoded.split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..' || part.includes('\\') || part.includes('\0')) return null;
    parts.push(part);
  }
  if (!parts.length || decoded.endsWith('/')) parts.push('index.html');
  return path.join(root, ...parts);
}

const TYPES = {
  html: 'text/html; charset=utf-8', js: 'text/javascript; charset=utf-8', mjs: 'text/javascript; charset=utf-8',
  css: 'text/css; charset=utf-8', json: 'application/json', webmanifest: 'application/manifest+json', png: 'image/png',
  jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', svg: 'image/svg+xml', ico: 'image/x-icon',
  wasm: 'application/wasm', woff2: 'font/woff2', txt: 'text/plain; charset=utf-8',
};

export const mime = (file) => TYPES[path.extname(file).slice(1).toLowerCase()] ?? 'application/octet-stream';

/** The app's arguments: `key=value` pairs that become the page's query string (`view=parliament hour=20 lang=hu`);
 * Chromium's and Electron's own switches (`--...`) are not the page's. Two are the app's business too, for a kiosk:
 * `fullscreen=always` (never leaves full screen) and `nolink=true` (no link opens anything outside the app). And
 * `update=false` keeps the app at its version (main.mjs otherwise updates it from the project's releases). */
export function parseArgs(argv) {
  const query = argv.filter((a) => a.includes('=') && !a.startsWith('-'));
  // the first one counts, as with URLSearchParams.get
  const value = (key) => query.find((a) => a.slice(0, a.indexOf('=')) === key)?.slice(key.length + 1);
  return {
    query,
    fullscreenAlways: value('fullscreen') === 'always',
    nolink: ['true', '1'].includes(value('nolink')),
    update: !['false', '0'].includes(value('update')),
  };
}

export const sameOrigin = (a, b) => a.protocol === b.protocol && a.hostname === b.hostname && a.port === b.port;

// variables Chromium sets for itself (linkEnv)
const CHROMIUM_OWN = ['CHROME_DESKTOP', 'NO_AT_BRIDGE', 'FC_FONTATIONS', 'EGL_PLATFORM'];

/** The environment and directory for a program a link opens (xdg-open, then a browser). Inside an AppImage, its AppRun
 * points LD_LIBRARY_PATH, XDG_DATA_DIRS and the like into the mount and runs from inside it: a browser it starts
 * would load the image's libraries, and keep a directory that goes away with the app. Chromium also renames the
 * desktop (ORIGINAL_XDG_CURRENT_DESKTOP) and sets a few variables for itself: CHROME_DESKTOP would make a Chrome the
 * link starts take this app's name, NO_AT_BRIDGE would turn off a GTK browser's accessibility. */
export function linkEnv(env) {
  const out = { ...env };
  for (const k of CHROMIUM_OWN) delete out[k];
  if (out.ORIGINAL_XDG_CURRENT_DESKTOP) {
    out.XDG_CURRENT_DESKTOP = out.ORIGINAL_XDG_CURRENT_DESKTOP;
    delete out.ORIGINAL_XDG_CURRENT_DESKTOP;
  }
  const appdir = env.APPDIR;
  if (!appdir) return { env: out, cwd: undefined };
  for (const k of ['APPDIR', 'APPIMAGE', 'ARGV0', 'OWD', 'GDK_BACKEND', 'GTK_THEME']) delete out[k];
  for (const [k, v] of Object.entries(out)) {
    if (typeof v !== 'string' || !v.includes(appdir)) continue;
    const kept = v.split(':').filter((p) => p && !p.startsWith(appdir));
    if (kept.length) out[k] = kept.join(':');
    else delete out[k];
  }
  return { env: out, cwd: env.OWD || env.HOME || '/' };
}
