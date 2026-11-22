// The changelog modal: CHANGELOG.md from the repo root, bundled as text and rendered on first open, from the first
// version's heading on. The renderer covers what that file uses: headings, list items (continued on indented lines),
// paragraphs, `code`, [links](url) and reference links ([1.0.6] with a "[1.0.6]: url" line at the end).
import md from '../../../CHANGELOG.md?raw';

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function render(src: string): string {
  const refs = new Map<string, string>();
  const lines: string[] = [];
  let body = false;  // what comes before the first version's heading is the file's own preamble
  for (const l of src.split(/\r?\n/)) {
    if (/^##\s/.test(l)) body = true;
    if (!body && !/^\[/.test(l)) continue;
    const m = /^\[([^\]]+)\]:\s*(\S+)\s*$/.exec(l);
    if (m) refs.set(m[1].toLowerCase(), m[2]);
    else lines.push(l);
  }
  const link = (text: string, url: string) =>
    /^https?:\/\//.test(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener">${text}</a>` : text;
  const inline = (s: string) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => link(t, u))
    .replace(/\[([^\]]+)\](?!\()/g, (all, t) => refs.has(t.toLowerCase()) ? link(t, refs.get(t.toLowerCase())!) : all);

  const out: string[] = [];
  let para: string[] = [], items: string[] = [];
  const flush = () => {
    if (para.length) out.push(`<p>${inline(para.join(' '))}</p>`);
    if (items.length) out.push(`<ul>${items.map((i) => `<li>${inline(i)}</li>`).join('')}</ul>`);
    para = []; items = [];
  };
  for (const l of lines) {
    const h = /^(#{1,4})\s+(.*)$/.exec(l);
    if (h) {
      flush();
      out.push(`<h${h[1].length + 1}>${inline(h[2])}</h${h[1].length + 1}>`);
    } else if (/^\s*[-*]\s+/.test(l)) {
      if (para.length) flush();
      items.push(l.replace(/^\s*[-*]\s+/, ''));
    } else if (!l.trim()) flush();
    else if (items.length && /^\s+/.test(l)) items[items.length - 1] += ' ' + l.trim();
    else para.push(l.trim());
  }
  flush();
  return out.join('');
}

let html = '';
export const changelogHtml = () => (html ||= render(md));
