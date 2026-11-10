import assert from 'node:assert/strict';
import { test } from 'node:test';
import { linkEnv, mime, parseArgs, resolve, sameOrigin } from './site.mjs';

test('resolves files and directories', () => {
  assert.equal(resolve('/site', '/'), '/site/index.html');
  assert.equal(resolve('/site', ''), '/site/index.html');
  assert.equal(resolve('/site', '/data/tiles/16/1_2.bin'), '/site/data/tiles/16/1_2.bin');
  assert.equal(resolve('/site', '/data/tiles/'), '/site/data/tiles/index.html');
  assert.equal(resolve('/site', '/a%20b/./c.png'), '/site/a b/c.png');
});

test('refuses to leave the site', () => {
  for (const p of ['/../Cargo.toml', '/%2e%2e/%2e%2e/etc/passwd', '/..%2f..%2fetc/passwd', '/data%5c..%5cx', '/a%00b', '/%zz']) {
    assert.equal(resolve('/site', p), null, p);
  }
});

test('names the types the viewer needs', () => {
  assert.equal(mime('/s/assets/mesher.worker-x.js'), 'text/javascript; charset=utf-8');
  assert.equal(mime('/s/data/meta.json'), 'application/json');
  assert.equal(mime('/s/data/tiles/1/0_0.bin'), 'application/octet-stream');
});

test('reads the arguments', () => {
  const a = parseArgs(['view=parliament', '--remote-debugging-port=9222', '--verbose', 'fullscreen=always', 'nolink=true']);
  assert.deepEqual(a.query, ['view=parliament', 'fullscreen=always', 'nolink=true']);
  assert.ok(a.fullscreenAlways && a.nolink);
  assert.deepEqual(parseArgs([]), { query: [], fullscreenAlways: false, nolink: false });
  const b = parseArgs(['fullscreen=yes', 'nolink=false', 'nolink=true']);
  assert.ok(!b.fullscreenAlways && !b.nolink);
  assert.ok(parseArgs(['nolink=1']).nolink);
});

test('compares origins, custom scheme included', () => {
  const app = new URL('voxelpest://localhost/');
  assert.ok(sameOrigin(new URL('voxelpest://localhost/data/meta.json?v=1'), app));
  assert.ok(!sameOrigin(new URL('https://side-quest.bar/'), app));
  assert.ok(!sameOrigin(new URL('http://localhost:5173/'), app));
  assert.ok(sameOrigin(new URL('http://localhost:5173/x'), new URL('http://localhost:5173/')));
});

test('undoes the AppImage environment for a link', () => {
  const env = {
    APPDIR: '/tmp/.mount_x', APPIMAGE: '/home/u/v.AppImage', OWD: '/home/u/dl', HOME: '/home/u', GTK_THEME: 'Adwaita:dark',
    LD_LIBRARY_PATH: '/tmp/.mount_x/usr/lib:', XDG_DATA_DIRS: '/tmp/.mount_x/usr/share:/usr/share',
    PATH: '/tmp/.mount_x/usr/bin:/usr/bin', ORIGINAL_XDG_CURRENT_DESKTOP: 'KDE', XDG_CURRENT_DESKTOP: 'Unity', LANG: 'hu_HU.UTF-8',
    CHROME_DESKTOP: 'voxelpest.desktop', NO_AT_BRIDGE: '1', FC_FONTATIONS: '1', EGL_PLATFORM: 'wayland',
  };
  const { env: out, cwd } = linkEnv(env);
  assert.equal(cwd, '/home/u/dl');
  for (const k of ['APPDIR', 'APPIMAGE', 'OWD', 'GTK_THEME', 'LD_LIBRARY_PATH', 'ORIGINAL_XDG_CURRENT_DESKTOP', 'CHROME_DESKTOP', 'NO_AT_BRIDGE']) {
    assert.ok(!(k in out), k);
  }
  assert.equal(out.XDG_DATA_DIRS, '/usr/share');
  assert.equal(out.PATH, '/usr/bin');
  assert.equal(out.XDG_CURRENT_DESKTOP, 'KDE');
  assert.equal(out.LANG, 'hu_HU.UTF-8');
  assert.deepEqual(linkEnv({ HOME: '/h', PATH: '/usr/bin', CHROME_DESKTOP: 'x' }), { env: { HOME: '/h', PATH: '/usr/bin' }, cwd: undefined });
});
