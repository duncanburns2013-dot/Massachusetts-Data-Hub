# massachusettsdatahub.com — start here

Read this file in full before doing anything. Then read `BUILD-NOTES.md` at
`E:\massachusettsdatahub\BUILD-NOTES.md` — it holds the rejected design
directions and the instrument's internals.

## Where things are

| what | where |
|---|---|
| The site (all work) | `E:\Massachusetts-Data-Hub` — branch **`restyle/slate-halyard`**, 12 commits |
| `main` | untouched. **Nothing has been pushed.** |
| Stale clone — do not edit | `C:\Users\dunca\code\Massachusetts-Data-Hub` (17 commits behind) |
| Serve it | `python -m http.server 8360 --directory E:\Massachusetts-Data-Hub` |
| Live (old, pre-restyle) | https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/ |

The repo commits to itself daily via ten GitHub Actions. Pull before working.

## The verification rule — non-negotiable

**Never claim how anything looks without a headless screenshot you have read.**
Every single page inspected this session had a defect the code did not predict.
Roughly one defect per three pages. If you have not looked, you do not know.

```powershell
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --headless=new `
  --hide-scrollbars --window-size=1400,900 --virtual-time-budget=8000 `
  --screenshot="out.png" --user-data-dir="<fresh dir>" "http://localhost:8360/<page>"
```

- **Do NOT use the SwiftShader flags.** They force software rendering: ~350s per
  capture versus ~3s on the real GPU. Same frame.
- **`--dump-dom` cannot read live state.** It does not composite, so rAF is
  suspended and every value reads back as its seed. Paint values into a fixed
  overlay div and screenshot that instead.
- **CSS transitions cannot be sampled** either — they run on the frame clock,
  which headless starves. Timers work; interpolation does not. Check motion in a
  real browser.
- Heavy pages (16+ charts) hang the renderer. Use a short budget (~2500ms) and a
  hard timeout, and capture before the chart animations finish.
- `index.html`'s hero is `100vh`, so a taller capture window just makes a taller
  hero. To photograph the card grid, temporarily set `.stage{height:150px}`,
  capture, then put it back.

## What is done

- All 26 pages share `assets/hub-theme.css` — the official MA palette
  (Bay Blue `#14558F`, Berkshire Green `#388557`, Cranberry `#680A1D`) on slate,
  with Adobe Fonts kit `irk1bar`: Halyard Display / Text + IBM Plex Mono.
- The instrument is in the repo at `instrument.html` with `data/ma351.js` and a
  Blender-baked AO plate at `assets/ao_rate.png`.
- `index.html` leads with the instrument full-viewport, then a turn band, then
  the directory. Cards have a full-height rule that widens on hover.
- The Invasion and All Things Boston folded in. Peoples Audit and HHS-MA-DOGE
  stay separate (one is a Vite build, one is a deliberate aesthetic exception).
- Boston Payroll is deliberately EXEMPT from the theme — dark neon interactive.
- Every page is reachable from the directory. Verified, zero orphans.

## What is next, in order

1. **THE MERGE — the actual next job.**
   - `education-boston.html` (**24 charts**) into All Things Boston's Education
     tab (**12+ charts**). Count charts before and after; do not lose any.
   - `boston-payroll.html` (0 charts, dot-matrix interactive) becomes a panel
     inside ATB's Payroll tab — it is a different format, not a duplicate.
   - `the-invasion.html` into `immigration-dashboard.html`. Largest of the three:
     two full tab systems to reconcile.
   - Delete the standalone files and their cards ONLY after verifying the
     content arrived.
2. **Films.** Duncan picks 10–12 of his best (mostly parodies — that is correct,
   films carry the POV). He has the MP4 masters locally. Upload those to
   YouTube, embed. Do NOT build a scraper: X needs auth and its posts vanish,
   and YouTube just moved its channel page to `lockupViewModel`, so anything
   written against `videoRenderer` silently returns zero.
3. **Accessibility pass.** Use the `accessibility-wcag` skill. This session
   produced five separate invisible-text bugs by hand-checking contrast.
4. **SEO** (`searchfit-seo` skill) — the site is currently invisible to search.
5. **Deploy** to Vercel. Domain is on their nameservers, no project connected.
   **Ask before pushing or deploying. Never push unasked.**

## Traps already paid for — do not rediscover these

- **Half-converted is the worst state.** A page with new type on an old dark
  ground reads worse than either. Finish a page or leave it alone.
- Several dashboards carry their own `TEMPLATE LAYOUT OVERRIDES` block with
  `font-family … !important` on class selectors. Prefix theme selectors with
  `html` to outrank them.
- Colour tokens do double duty. `--navy` was both a hero background and the body
  text colour; remapping it turned every paragraph blue. Check usage first.
- Heroes went from near-black to Bay Blue, so anything designed against the dark
  ground (muted greys, semantic red/green) now fails contrast. Light variants:
  `#8FD9AE` and `#FFB3BE`, both 4.5:1 on `#14558F`.
- Scope semantic overrides tightly. `[class*="hero"] .up` also caught the KPI
  values and turned them green.
- Python's `io.open(...,'w')` on Windows writes CRLF and makes every diff look
  like a full-file rewrite. Write bytes, or pass `newline='\n'`.
- `git add` can fail with "Permission denied" writing a loose object — Defender.
  Fix: `git config core.fsyncObjectFiles false`, then retry. **Never delete
  loose objects.**
- Footage behind content does not work here. Tested twice: soft enough not to
  compete = invisible; sharp enough to see = competes. Do not re-propose it.
- A cold-open intro was built and cut. "No website does this." Do not re-propose.

## How Duncan works

Verify before asserting. Label inference as inference. Say plainly when
something is unverified — he would rather hear "I have not checked" than a
confident wrong answer. Getting things wrong has cost him days across projects.
He will paste other AIs' reviews: check every claim against the artifact first.
