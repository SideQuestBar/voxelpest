import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { defineConfig } from 'vite';

// public/ also holds the shipped map as tarball parts (./bv pack, ./bv unpack): they are for git, not for the site
function dropMapParts() {
  let out;
  return {
    name: 'drop-map-parts',
    apply: 'build',
    configResolved(c) { out = resolve(c.root, c.build.outDir); },
    closeBundle() {
      for (const f of readdirSync(out)) if (f.startsWith('voxelpest-data.tar.gz')) rmSync(join(out, f));
    },
  };
}

// The map is published in bundles: the four tiles that share a parent in one file, tiles/{s}/{x}_{y}.pak for the
// children (2x, 2y), (2x+1, 2y), (2x, 2y+1), (2x+1, 2y+1) of tile (x, y) of the next coarser level. The quadtree
// (src/engine/tiles.ts) only ever asks for all four at once, so this is the same bytes in a quarter of the requests,
// and a quarter of the files: Cloudflare Pages takes 20 000 at most. A bundle: eight little-endian uint32, the offset
// (from the bundle's start) and length of each child's gzip (0: no such tile), then the gzips. web/public/data keeps
// the tiles one per file (scripts/minecraft.py reads them); the dev server bundles them as they are asked for.
function pak(dir, s, x, y) {
  const kids = [[0, 0], [1, 0], [0, 1], [1, 1]].map(([dx, dy]) => {
    const f = join(dir, String(s), `${2 * x + dx}_${2 * y + dy}.bin`);
    return existsSync(f) ? readFileSync(f) : null;
  });
  if (!kids.some(Boolean)) return null;
  const head = Buffer.alloc(32);
  let off = 32;
  kids.forEach((k, i) => { head.writeUInt32LE(k ? off : 0, 8 * i); head.writeUInt32LE(k ? k.length : 0, 8 * i + 4); off += k ? k.length : 0; });
  return Buffer.concat([head, ...kids.filter(Boolean)]);
}

function bundleTiles(root) {
  let n = 0, files = 0;
  for (const s of readdirSync(root)) {
    const keys = new Set();
    for (const f of readdirSync(join(root, s))) {
      const m = /^(\d+)_(\d+)\.bin$/.exec(f);
      if (m) keys.add(`${+m[1] >> 1}_${+m[2] >> 1}`);
    }
    for (const k of keys) {
      const [x, y] = k.split('_').map(Number);
      writeFileSync(join(root, s, `${k}.pak`), pak(root, s, x, y));
      n++;
    }
    for (const f of readdirSync(join(root, s))) if (f.endsWith('.bin')) { rmSync(join(root, s, f)); files++; }
  }
  console.log(`bundle-tiles: ${files} tiles in ${n} bundles`);
}

function serveBundles() {
  let root;
  return {
    name: 'serve-bundles',
    apply: 'serve',
    configResolved(c) { root = join(c.publicDir, 'data', 'tiles'); },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const m = /\/data\/tiles\/(\d+)\/(\d+)_(\d+)\.pak(\?|$)/.exec(req.url || '');
        if (!m) return next();
        const b = pak(root, m[1], +m[2], +m[3]);
        if (!b) { res.statusCode = 404; return res.end(); }
        res.setHeader('Content-Type', 'application/octet-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.end(b);
      });
    },
  };
}

// The tiles' URLs never change between maps, so a cache in between (the browser's, or a Cloudflare zone whose Browser
// Cache TTL turns Pages' max-age=0 into 4 hours) served a phone the old map's tiles under the new meta.json. A hash
// of every tile's path and bytes goes into dist's meta.json as tiles.v; the viewer asks for tiles with ?v=<hash>, so
// a new map has new URLs, and public/_headers can cache tiles for good. bun run dev reads public/ as it is: no ?v there.
function versionTiles() {
  let out;
  return {
    name: 'version-tiles',
    apply: 'build',
    configResolved(c) { out = resolve(c.root, c.build.outDir); },
    closeBundle() {
      const meta = join(out, 'data', 'meta.json');
      const root = join(out, 'data', 'tiles');
      bundleTiles(root);
      const h = createHash('sha256');
      const files = readdirSync(root, { recursive: true, withFileTypes: true })
        .filter((d) => d.isFile()).map((d) => join(d.parentPath, d.name)).sort();
      if (!files.length) throw new Error(`version-tiles: no tiles in ${root}`);
      for (const f of files) h.update(f.slice(root.length)).update('\0').update(readFileSync(f));
      const m = JSON.parse(readFileSync(meta, 'utf8'));
      m.tiles.v = h.digest('hex').slice(0, 16);
      writeFileSync(meta, JSON.stringify(m));
      console.log(`version-tiles: ${files.length} bundles, v=${m.tiles.v}`);
      writeOffline(out, m.tiles.v);
    },
  };
}

// offline.json: what the website's "Save for offline" (src/offline.ts) puts in Cache Storage, as URLs relative to the
// page: the shell (the page, bundles, icons) and the whole map, the tiles with the ?v= tiles.ts asks for. Written here
// rather than in a plugin of its own: Rollup runs closeBundle hooks in parallel, and this needs the final meta.json.
function writeOffline(out, v) {
  const skip = new Set(['offline.json', 'sw.js', '_headers', '404.html', 'og.jpg']);
  const shell = ['./'], data = [];
  let bytes = 0;
  for (const d of readdirSync(out, { recursive: true, withFileTypes: true })) {
    if (!d.isFile()) continue;
    const rel = join(d.parentPath, d.name).slice(out.length + 1).split('\\').join('/');
    if (skip.has(rel) || rel.startsWith('voxelpest-data.tar.gz')) continue;
    bytes += statSync(join(d.parentPath, d.name)).size;
    if (rel.startsWith('data/tiles/')) data.push(`${rel}?v=${encodeURIComponent(v)}`);
    else if (rel.startsWith('data/')) data.push(rel);
    else shell.push(rel);
  }
  shell.sort();
  data.sort();
  writeFileSync(join(out, 'offline.json'), JSON.stringify({ v, bytes, shell, data }));
  console.log(`offline: ${shell.length} shell files, ${data.length} map files, ${(bytes / 1e6).toFixed(0)} MB`);
}

// index.html's %SITE%: the address the site is published at, for the canonical link and the preview image (Open
// Graph wants absolute URLs). VITE_SITE_URL comes from WEB_DOMAIN (./bv site, publish_web.sh).
const site = (process.env.VITE_SITE_URL || 'https://map.side-quest.bar').replace(/\/+$/, '');
function siteUrl() {
  return { name: 'site-url', transformIndexHtml: (html) => html.replaceAll('%SITE%', site) };
}

const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'));

export default defineConfig({
  define: { __APP_VERSION__: JSON.stringify(version) },  // the about box shows it
  base: './',
  plugins: [dropMapParts(), versionTiles(), serveBundles(), siteUrl()],
  worker: { format: 'es' },
  build: { chunkSizeWarningLimit: 2000, target: 'es2022' },
  // bun run dev with the Minecraft card on (?minecraft=1) and ./bv server running here: its player count
  // CHANGELOG.md sits in the repo root, one level up (ui/changelog.ts imports it)
  server: { fs: { allow: ['..'] }, proxy: { '/api/minecraft': { target: 'http://127.0.0.1:8765', rewrite: () => '/status' } } },
});
