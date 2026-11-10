// The website as an installable app: the manifest (public/manifest.webmanifest, the desktop app's icon) and a small
// service worker (public/sw.js: the page and its bundles for a quick or offline start, never the map's tiles). The
// About box offers "Install as an app" where the browser lets a page ask (Chromium); elsewhere the browser's own menu
// does it (Safari: Share, Add to Home Screen). Not in the desktop app, nor on the dev server.
import { track } from './analytics';
import { onLang, T } from './i18n';
import { desktop } from './ui/desktop';

type InstallEvent = Event & { prompt(): Promise<void>; userChoice: Promise<{ outcome: string }> };

export function initPwa(btn: HTMLButtonElement) {
  if (desktop) return;
  if (import.meta.env.PROD && 'serviceWorker' in navigator) void navigator.serviceWorker.register('sw.js').catch(() => {});
  let ask: InstallEvent | null = null;
  const label = () => { btn.textContent = T().install; };
  label();
  onLang(label);
  addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    ask = e as InstallEvent;
    btn.hidden = false;
  });
  btn.onclick = async () => {
    if (!ask) return;
    await ask.prompt();
    const { outcome } = await ask.userChoice;
    track('install', { outcome });
    ask = null;
    btn.hidden = true;
  };
  addEventListener('appinstalled', () => { btn.hidden = true; });
}
