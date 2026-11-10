// The desktop app (desktop/, Electron) gives the page window.voxelpestDesktop; the website has none. With it the menu
// (ui/menu.ts) also has Full screen and Quit, Esc opens it and F11 toggles full screen. The app's arguments are the
// page's query string, so a kiosk can say fullscreen=always (no way back to a window) and nolink=true (no link out of
// the app; stripLinks works on the website too). The app enforces both on its side as well.
export interface DesktopHost {
  quit(): Promise<void>;
  // goes full screen or back to a window when `on` is given; answers whether the window is full screen
  fullscreen(on?: boolean): Promise<boolean>;
}

declare global {
  interface Window { voxelpestDesktop?: DesktopHost }
}

export const desktop: DesktopHost | null = window.voxelpestDesktop ?? null;

const qs = new URLSearchParams(location.search);
export const fullscreenAlways = qs.get('fullscreen') === 'always';
export const noLinks = qs.get('nolink') === 'true' || qs.get('nolink') === '1';

// links to anywhere but this page's own origin lose their href (an <a> without one is plain text), now and whenever
// the page writes new ones: the about box on a change of language, the bar's card, the Minecraft card
export function stripLinks() {
  const inside = (a: HTMLAnchorElement) => {
    try {
      const u = new URL(a.href, location.href);
      return u.protocol === location.protocol && u.host === location.host;
    } catch { return false; }
  };
  const strip = () => {
    for (const a of document.querySelectorAll<HTMLAnchorElement>('a[href]')) {
      if (inside(a)) continue;
      for (const k of ['href', 'target', 'rel']) a.removeAttribute(k);
    }
  };
  document.body.classList.add('nolink');
  strip();
  new MutationObserver(strip).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['href'] });
  window.open = () => null;
}
