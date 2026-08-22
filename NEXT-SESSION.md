# massachusettsdatahub.com — start here

Read this file in full before doing anything. Then read `BUILD-NOTES.md` at
`E:\massachusettsdatahub\BUILD-NOTES.md` — it holds the rejected design
directions and the instrument's internals.

## Where things are

| what | where |
|---|---|
| The site (all work) | `E:\Massachusetts-Data-Hub` — branch **`restyle/slate-halyard`**, 18 commits ahead of `main` (origin/main merged in 2026-08-19) |
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
- Boston Payroll's dark-neon dot-matrix interactive is **CUT** (2026-08-19).
  Not exempt, not embedded, not standalone — gone. See CUT, below.
- Every page is reachable from the directory. Verified, zero orphans.

## What is next, in order

1. ~~**THE MERGE.**~~ **DONE 2026-08-19** — all three, each verified on screen
   before the standalone file was deleted. The site is 26 pages → 24.
   - `education-boston.html` → ATB Education tab, now **8 sub-tabs, 30 charts**
     ("At a Glance" keeps the 6 that were already there; the 7 incoming tabs
     carry all 24). ATB went 65 → 89 canvases. The two pages had **disjoint
     class vocabularies**, so incoming markup was translated to ATB's
     (kg/kpi/v/lb, g g2, cd, cw, co, tw) and its palette namespaced as EC/EGC.
   - `boston-payroll.html` — built as a panel, then **CUT the same day** on
     Duncan's instruction (it had already been decided in another session; this
     handoff was stale and said to build it). Worth keeping the finding: ATB's
     Payroll tab had been iframing `boston-payroll-interactive.html`, **a file
     that never existed, so the tab was shipping a 404 error page.** That is
     now gone along with the panel.
   - `the-invasion.html` → **fourth section of `immigration-dashboard.html`**
     ("Money Trail", `i-` prefix, 8 panels). Both files defined `.card`,
     `.callout`, `.container`, `.grid-2`, `.grid-3`, `.num`, `.tab`, `.active`,
     and `.tab` meant *nav button* in one and *panel* in the other. All 284
     Invasion rules are machine-scoped under `.inv` (transform verified
     lossless: 995 declarations in, 995 out) and its own tab machinery dropped.
   - The turn band on `index.html` claimed "computed at runtime" over a
     hardcoded dashboard count that was already stale by three. It counts the
     cards now.

   **Left deliberately undone, and why:** in ATB's Education tab the six "At a
   Glance" charts are near-duplicates of six deeper ones (e1≈overviewAll,
   e2≈gapChange, e3≈accNHS+accHS, e4≈gradRace, e5≈absentRace, e6≈gradeScoreELA).
   Nothing was dropped — cutting them is an editorial call for Duncan.
2. **Films.** Duncan picks 10–12 of his best (mostly parodies — that is correct,
   films carry the POV). He has the MP4 masters locally. Upload those to
   YouTube, embed. Do NOT build a scraper: X needs auth and its posts vanish,
   and YouTube just moved its channel page to `lockupViewModel`, so anything
   written against `videoRenderer` silently returns zero.
3. **Accessibility pass.** Use the `accessibility-wcag` skill. This session
   produced five separate invisible-text bugs by hand-checking contrast.

   **Measured 2026-08-19 — do not re-derive, and do not eyeball these.** The
   composited ground matters: the hero blue is a `linear-gradient`, not a
   `background-color`, and the stat boxes are `rgba(255,255,255,.1)` over it,
   so a naive parent-walk reads the light page ground and reports a PASS on
   text that is invisible. Composite properly before judging.
   - `immigration-dashboard.html` hero: **`$1.83B` renders at 1.01:1 — it is
     invisible on screen.** All five hero labels are 1.92:1; `10.8M` 2.19:1;
     `7.4M` 2.38:1. Only `-84%` (3.14) and `137K` (3.04) scrape past. This is
     the documented Bay-Blue hero trap and it is the worst instance found.
   - (The payroll panel's own 1.31:1 source caption is moot — the panel is cut.)
   - The sub-tab bars sitewide are plain `<button>`s with no
     `role="tablist"`/`aria-selected`. Fix them together, not page by page.
4. **SEO** (`searchfit-seo` skill) — the site is currently invisible to search.
5. **Deploy** to Vercel. Domain is on their nameservers, no project connected.
   **Ask before pushing or deploying. Never push unasked.**

## The front page below the instrument — rebuilt 2026-08-19

The instrument itself is approved and must not change. Everything under it was
rebuilt on a live WebGL field.

**What is there now**
- `assets/ma351-field.js` (50KB) — all 351 municipalities as simplified
  polygons, Douglas-Peucker at tol 0.0042, 4.9% of the original 108,907
  vertices, cos-corrected aspect 1.613. Extracted from `data/ma351.js` (2.3MB).
  Verified against the instrument's own readout: min 2.18 Hancock, median
  12.44, max 20.50 Wendell.
- A three.js point cloud in `index.html`: 27,446 points laid along every
  boundary, one draw call, custom GLSL, cursor-repulsion in the vertex shader,
  scroll-driven threshold reveal west to east.
- The 21 cards are now 19 index rows. No cards, no emoji, no eyebrow, no
  coloured rail, no animated rainbow.

**Traps this cost, do not rediscover**
- three.js **frustum-culls Points using the raw attribute positions**. The
  vertex shader relocates every point into world space, so the computed
  bounding sphere is meaningless and the entire cloud vanishes with no error.
  `frustumCulled = false`.
- Size the field from panel **width**. Deriving it from panel height feeds back
  on itself, because the padding that creates the band is part of that height.
- A diverging ramp puts the median at its lightest point and most of the state
  sits near the median. Mix an ink floor into the fragment colour or the middle
  of Massachusetts renders light-on-light and disappears. Same failure the
  instrument solved by drawing boundaries instead of implying them.
- Only boundary **vertices** reads as a scatter, not a state. Walk each edge and
  lay points at fixed spacing.
- The Claude browser pane suspends rAF, so a WebGL loop never advances there and
  `drawCalls` reads 0. Force a render and read pixels, or use headless.

**Skills that changed the answer** (load these before design work here)
`impeccable:impeccable` → its `bolder` playbook and `reference/craft-floor.md`.
The craft floor names cards-of-icon-plus-heading-plus-text as the lazy page
structure, bans eyebrows above a heading outright, and calls a coloured
border-left over 1px the most recognisable tell of AI-generated UI. Run its
detector when done: `node <impeccable>/scripts/detect.mjs --json index.html`.

**The award research, so it does not have to be redone**
- Explore Primland — scroll-driven camera glide over real terrain, fog layers.
- Oryzo — scroll drives camera depth, not 2D parallax.
- Cartier — scroll moves between scenes; GLSL + GSAP + Lenis.
- Hubtown — cursor-reveal over a live WebGL hero.
- Shopify Editions — particle-dispersing type, depth-layered panels on scroll.
- Codrops WebGL gallery — `step(uProgress, normalized_index)` grid reveal.
- 29 of 47 Q1-2026 Awwwards SOTD winners ran three.js; the consistent stack is
  three.js + GSAP ScrollTrigger. Jurors test on real devices, so a hero that
  drops to 18fps fails regardless of how it looks.

**Still open here**
- `Last refreshed` in the turn band is hardcoded; nothing writes it.
- The sources strip and footer at the very bottom were not touched.
- Frame rate of the field has not been measured on Duncan's machine.

## CUT — decided and removed. Do not rebuild these.

Every one of these was decided in conversation. If a decision only lives in a
chat, the next session cannot see it — write it here the same day.

| What | When | Note |
|---|---|---|
| Cold-open intro on `index.html` | 2026-08-18 | "No website does this." It is a splash screen however well argued. |
| Footage bedded under the instrument | 2026-08-17 | Tested twice. Defocused = invisible; sharp = competes. |
| Boston payroll dot-matrix interactive | 2026-08-19 | Panel, iframe and `boston-payroll-interactive.html` all removed. |
| `budget-explainer.html` + its card | 2026-08-19 | Removed. Only inbound link was its own card. |

Recover any of them from git if a decision reverses: `git checkout aaa05a2 -- <path>`.

## Traps already paid for — do not rediscover these

- **Never blanket-kill Chrome.** `Get-Process chrome | Stop-Process` closes
  Duncan's own browser while he works alongside you. Launch with
  `Start-Process -PassThru` and wait on that PID; `--headless=new` exits on its
  own after `--screenshot`, so no kill is usually needed. (If orphans do pile
  up they will silently starve later captures — 83 of them made four of eight
  screenshots come back missing.)
- **A headless frame can lie about a page that is fine.** A probe injected
  before `</body>` did not run at all in two separate captures: once because
  escaped newlines had become literal line breaks inside a JS string (whole
  block failed to parse), once because virtual time stalled on a `loading=lazy`
  iframe so the probe timer never fired. Both looked like merge defects and
  were not. Force the iframe eager, and read the DOM in a real browser before
  believing a still.
- **The browser pane serves a cached page.** A regression check that said "all
  three sections intact" had been run against the pre-merge copy. Cache-bust
  with a query string, and assert on something only the new file contains.
- **Both `.tab` systems and both `.container` rules survive a merge.** Check
  specificity: `.inv .container` (0,2,0) beats the host's `.container` (0,1,0),
  which is the only reason the measure is right. Measure it, do not assume it.

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
