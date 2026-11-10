// usage: node tools/shot.mjs out.png [query] [w] [h]    (dev server running: bun run dev, or URL=...)
// needs Playwright: bun add -d playwright && bunx playwright install chromium
// Waits until the viewer has loaded and every tile the view wants is meshed, then saves the canvas.
// SWIFTSHADER=1 renders in software (no GPU; slow: add shadow=2048 to the query).
import fs from 'node:fs';
import { chromium } from 'playwright';

const [out = 'shot.png', q = '', w = 1600, h = 1000] = process.argv.slice(2);
const args = process.env.SWIFTSHADER ? ['--enable-unsafe-swiftshader', '--use-angle=swiftshader'] : ['--enable-gpu', '--use-angle=default'];
const browser = await chromium.launch({ args: [...args, '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[console]', m.type(), m.text().slice(0, 300)); });
page.on('response', (r) => { if (r.status() >= 400) console.log('[http]', r.status(), r.url()); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
const t0 = Date.now();
// noon and a clear sky unless the query says otherwise, not Budapest's live time and weather
await page.goto(`${process.env.URL || 'http://localhost:5173/'}?${/(^|&)(live|hour|weather|snow)=/.test(q) ? q : `live=0&${q}`}`);
await page.waitForFunction(() => window.__ready === true, null, { timeout: +(process.env.TMO || 300000) });
let calm = 0; // settled: no tile loading for a few consecutive checks
for (let i = 0; i < 600 && calm < 3; i++) {
  await page.waitForTimeout(1000);
  calm = (await page.evaluate(() => window.__three.lod?.loading ?? 1)) === 0 ? calm + 1 : 0;
}
// render now and read the buffer in the same task: in software rendering a frame can take seconds
const url = await page.evaluate(() => {
  const t = window.__three;
  t.lod?.update(true);
  t.render();
  return t.renderer.domElement.toDataURL('image/png');
});
fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
console.log(out, 'in', Date.now() - t0, 'ms,', await page.evaluate(() => window.__three.lod?.shown), 'tiles shown');
await browser.close();
