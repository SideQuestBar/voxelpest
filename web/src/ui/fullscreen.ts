// The full-screen button (the Fullscreen API, or webkit's). iPhone Safari can't make a page full screen: there the
// button stays hidden and the home-screen app (manifest: display fullscreen) is the way; so it does inside that app.
import { track } from '../analytics';
import { onLang, T } from '../i18n';

type Doc = Document & { webkitFullscreenEnabled?: boolean; webkitFullscreenElement?: Element | null; webkitExitFullscreen?: () => void };
type El = HTMLElement & { webkitRequestFullscreen?: () => void };

// the button's state and switch, for the menu (ui/menu.ts); null where the button stays hidden
export interface FullScreen { on(): boolean; toggle(): Promise<boolean> }

export function fullscreenButton(btn: HTMLButtonElement, hint: (text: string) => void): FullScreen | null {
  const d = document as Doc, root = document.documentElement as El;
  const app = matchMedia('(display-mode: fullscreen), (display-mode: standalone)').matches || (navigator as { standalone?: boolean }).standalone;
  if (!(d.fullscreenEnabled || d.webkitFullscreenEnabled) || app) {
    // an iPhone's browser can't: the button says how instead (from the home screen the site opens full screen)
    if (!app && matchMedia('(pointer: coarse)').matches) {
      const label = () => { btn.setAttribute('aria-label', T().fullscreen); btn.title = T().fullscreen; };
      label();
      onLang(label);
      btn.onclick = () => { track('fullscreen', { how: 'hint' }); hint(T().fullscreenHow); };
      btn.hidden = false;
    }
    return null;
  }
  const current = () => d.fullscreenElement ?? d.webkitFullscreenElement ?? null;
  const sync = () => {
    const on = !!current(), t = T();
    btn.classList.toggle('on', on);
    btn.setAttribute('aria-label', on ? t.fullscreenExit : t.fullscreen);
    btn.title = btn.getAttribute('aria-label')!;
  };
  // resolves false when the browser refuses (no click or key just before: a controller's button doesn't count)
  const toggle = async () => {
    try {
      if (current()) await (d.exitFullscreen ? d.exitFullscreen() : d.webkitExitFullscreen?.());
      else if (root.requestFullscreen) await root.requestFullscreen({ navigationUI: 'hide' });
      else root.webkitRequestFullscreen?.();
      return true;
    } catch { return false; }
  };
  btn.onclick = () => { track('fullscreen', { on: !current() }); void toggle(); };
  for (const ev of ['fullscreenchange', 'webkitfullscreenchange']) document.addEventListener(ev, sync);
  onLang(sync);
  sync();
  btn.hidden = false;
  return { on: () => !!current(), toggle };
}
