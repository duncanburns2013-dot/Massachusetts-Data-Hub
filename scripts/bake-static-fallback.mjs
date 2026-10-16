// Bake the employment dashboard's computed figures into its static HTML.
//
// WHY THIS EXISTS
// fetch-bls-data.js rewrites the data arrays, and the page's renderDerived()
// turns them into every headline figure at load. The text sitting inside those
// elements in the file was never touched again: in October 2026 the rendered
// page read August while the source still said "May 2026: -2,900 jobs", "4.5%"
// and "+17,600". That source is what a crawler, a no-JavaScript fetch, a search
// snippet or anyone quoting the file sees -- a dashboard that is current on
// screen and five months stale everywhere else.
//
// So this runs the page's OWN script, unchanged, against a stub DOM, records
// what renderDerived() writes into each element, and writes the same text back
// into the file. One derivation, two outputs: the browser and the fallback
// cannot disagree, and nothing is re-implemented here that could drift.
//
// WHAT IT TOUCHES
// Only elements renderDerived() writes, matched by id. textContent goes in when
// the element holds plain text; innerHTML only into <tbody> (no nesting to
// misjudge); className when it changed. An id the script writes that the file
// cannot take is reported, never guessed at.
//
//   node scripts/bake-static-fallback.mjs [page]      (default employment-dashboard.html)
//
// Exits non-zero if the page script throws before renderDerived() finishes, so a
// broken page fails the job instead of baking half its figures.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGE = path.join(ROOT, process.argv[2] || 'employment-dashboard.html');
let html = fs.readFileSync(PAGE, 'utf8');

const block = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).find(s => s.includes('function renderDerived'));
if (!block) { console.error('no inline script with renderDerived() in ' + PAGE); process.exit(1); }

// A stub that absorbs anything chart or layout code does to it.
const absorb = () => new Proxy(function () {}, {
  get: (t, k) => (k === Symbol.toPrimitive ? () => '' : k === 'length' ? 0 : absorb()),
  apply: () => absorb(), construct: () => absorb(), set: () => true,
});

const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const written = new Map();         // id -> { text?, html?, cls? }
function element(id, init = '') {
  const rec = written.get(id) || {};
  const el = {
    _text: init,
    get textContent() { return this._text; },
    set textContent(v) { this._text = String(v); rec.text = this._text; written.set(id, rec); },
    get innerHTML() { return this._text; },
    set innerHTML(v) { rec.html = String(v); written.set(id, rec); },
    get className() { return rec.cls || ''; },
    set className(v) { rec.cls = String(v); written.set(id, rec); },
    classList: absorb(), style: absorb(), dataset: {},
    addEventListener() {}, setAttribute() {}, getAttribute: () => null,
    getContext: () => absorb(), querySelectorAll: () => [], querySelector: () => null,
  };
  return el;
}
const els = new Map();
const document = {
  getElementById(id) {
    if (!ids.has(id)) return null;
    if (!els.has(id)) els.set(id, element(id));
    return els.get(id);
  },
  // Only the [data-field="x"] form is read by renderDerived(); hand back the
  // element's current text so the page reads what a browser would.
  querySelector(sel) {
    const m = /^\[data-field="([^"]+)"\]$/.exec(sel);
    if (!m) return null;
    const t = new RegExp(`data-field="${m[1]}"[^>]*>([^<]*)<`).exec(html);
    return t ? element('__field_' + m[1], t[1]) : null;
  },
  querySelectorAll: () => [], createElement: () => absorb(), addEventListener() {},
  body: absorb(), documentElement: absorb(),
};
const sandbox = { document, Chart: absorb(), console, Math, Date, JSON, Number, String, Array, Object, isNaN, parseFloat, parseInt, Intl };
sandbox.window = sandbox;
sandbox.setTimeout = () => 0; sandbox.requestAnimationFrame = () => 0;
sandbox.addEventListener = () => {};
vm.createContext(sandbox);

// Run the page script up to and including renderDerived(), not the chart setup
// after it: the figures are what is being baked, the canvases are not.
const cut = block.lastIndexOf('renderDerived();');
if (cut < 0) { console.error('renderDerived() is never called in ' + PAGE); process.exit(1); }
try {
  vm.runInContext(block.slice(0, cut + 'renderDerived();'.length), sandbox, { timeout: 5000 });
} catch (e) {
  console.error('page script failed before renderDerived() finished: ' + e.message);
  process.exit(1);
}

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
let baked = 0; const skipped = [];
for (const [id, rec] of written) {
  if (id.startsWith('__field_')) continue;
  const open = new RegExp(`<(\\w+)\\b[^>]*\\sid="${id}"[^>]*>`).exec(html);
  if (!open) { skipped.push(id + ' (no element)'); continue; }
  const tag = open[1], start = open.index, bodyAt = start + open[0].length;
  let tagText = open[0];
  if (rec.cls != null) {
    tagText = /\bclass="[^"]*"/.test(tagText)
      ? tagText.replace(/\bclass="[^"]*"/, `class="${rec.cls}"`)
      : tagText.replace(/^<(\w+)/, `<$1 class="${rec.cls}"`);
  }
  let end, inner;
  if (rec.html != null) {
    if (tag !== 'tbody') { skipped.push(id + ' (innerHTML into <' + tag + '>)'); continue; }
    end = html.indexOf('</tbody>', bodyAt);
    inner = rec.html;
  } else if (rec.text != null) {
    end = html.indexOf('<', bodyAt);
    if (html.slice(end, end + tag.length + 3) !== `</${tag}>`) {
      skipped.push(id + ' (holds markup)'); continue;
    }
    inner = esc(rec.text);
  } else {
    end = html.indexOf('<', bodyAt);
    inner = html.slice(bodyAt, end);
  }
  const next = html.slice(0, start) + tagText + inner + html.slice(end);
  if (next !== html) { html = next; baked++; }
}

fs.writeFileSync(PAGE, html);
console.log(`baked ${baked} static fallback value(s) into ${path.basename(PAGE)}` +
            ` (${written.size} written by renderDerived)`);
if (skipped.length) console.warn('  not baked: ' + skipped.join(', '));
