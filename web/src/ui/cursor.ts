// The mouse pointer hides while a controller is in use in full screen (the website's Fullscreen API, the browser's own
// F11, the home-screen app, the desktop app's full-screen window) and comes back as soon as the mouse moves.
import type { Pad } from '../controls/input';

const d = document as Document & { webkitFullscreenElement?: Element | null };

// sync, so it also sees a full screen the page didn't ask for (F11, the compositor's key, the desktop app's window)
function fullscreen() {
  if (d.fullscreenElement || d.webkitFullscreenElement) return true;
  if (matchMedia('(display-mode: fullscreen)').matches) return true;
  return outerWidth >= screen.width && outerHeight >= screen.height && innerHeight >= screen.height - 1;
}

function active(p: Pad) {
  return p.on && (p.lx !== 0 || p.ly !== 0 || p.rx !== 0 || p.ry !== 0 || p.lt > 0 || p.rt > 0 || p.held.some(Boolean));
}

export function padCursor() {
  let hidden = false;
  const set = (on: boolean) => {
    if (on === hidden) return;
    hidden = on;
    document.body.classList.toggle('pad-cursor', on);
  };
  // a real move only: Chromium sends movement-less mousemoves when the page changes under a still pointer
  addEventListener('mousemove', (e) => { if (e.movementX || e.movementY) set(false); }, { passive: true });
  addEventListener('mousedown', () => set(false), { passive: true });
  for (const ev of ['fullscreenchange', 'webkitfullscreenchange']) d.addEventListener(ev, () => { if (!fullscreen()) set(false); });
  addEventListener('resize', () => { if (!fullscreen()) set(false); });
  // once a frame, after input.poll() and before anything mutes the pad
  return (p: Pad) => { if (!hidden && active(p) && fullscreen()) set(true); };
}
