import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
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
      const h = createHash('sha256');
      const files = readdirSync(root, { recursive: true, withFileTypes: true })
        .filter((d) => d.isFile()).map((d) => join(d.parentPath, d.name)).sort();
      if (!files.length) throw new Error(`version-tiles: no tiles in ${root}`);
      for (const f of files) h.update(f.slice(root.length)).update('\0').update(readFileSync(f));
      const m = JSON.parse(readFileSync(meta, 'utf8'));
      m.tiles.v = h.digest('hex').slice(0, 16);
      writeFileSync(meta, JSON.stringify(m));
      console.log(`version-tiles: ${files.length} tiles, v=${m.tiles.v}`);
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
  plugins: [dropMapParts(), versionTiles(), siteUrl()],
  worker: { format: 'es' },
  build: { chunkSizeWarningLimit: 2000, target: 'es2022' },
  // bun run dev with the Minecraft card on (?minecraft=1) and ./bv server running here: its player count
  server: { proxy: { '/api/minecraft': { target: 'http://127.0.0.1:8765', rewrite: () => '/status' } } },
});
