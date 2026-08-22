# Build Playbook

How this site is built, in the order it has to be built, and the traps that cost
real time on the way.

A note on the name: this is a playbook, not a roadmap. A roadmap says where a
project is going. What follows is the opposite — a record of what was already
done and what to do again, so the next site of this kind starts from here
instead of from scratch.

Nothing below is generic web advice. Every rule in it was paid for by something
breaking on this repository.

**Building your own?** Part I is how this site works and what to avoid.
[Part II](#part-ii--building-one-of-these-from-zero) is the order to build one
in, for any subject — a city budget, a school district, a regulator. If that is
what you came for, start there and refer back.

---

# Part I — How this site works

## 1. The argument comes first, then the design

This site makes one claim: **every figure is checkable.** Every structural
decision follows from that claim, and a decision that undercuts it is wrong even
when it looks better.

That is why:

- there is a `method.html` at all — 14 sections, 40 tables, 323 rows of
  *figure → source → date*, generated from `MASTER_DATA.md`;
- every dashboard carries a "sourced here" strip pointing into the section that
  documents it, so the answer to "where did that number come from" is one click,
  not three;
- a dashboard with no Method section does **not** get a link. Pointing "how this
  is sourced" at a page that does not source it is worse than not linking.

If you build something similar, decide the one claim first. The design is
downstream of it.

---

## 2. Architecture: flat files, generated in a fixed order

No framework, no bundler, no build server. Every page is a standalone HTML file
that opens correctly from `file://`. The "build" is a handful of Python scripts
that rewrite regions of those files in place.

This is not nostalgia. It buys three things that matter for a public-record
site: pages that outlive any toolchain, a diff you can actually read in review,
and a deploy that cannot fail for reasons unrelated to the content.

### The build chain

| Script | Writes | Notes |
|---|---|---|
| `build_about.py` | `about.html` | Bio facts, each read from a source |
| `build_method.py` | `method.html` | Renders `MASTER_DATA.md` |
| `method_links.py` | all 16 dashboards | Stamps the "sourced here" strip |
| `build_videos.py` | `videos.html` | 24 entries |
| `seo.py` | every page | Meta, canonical, JSON-LD, `sitemap.xml`, `robots.txt` |

**Order is load-bearing. `seo.py` runs last, always.**

`build_method.py` builds `method.html` using `about.html` as its HTML shell. That
shell carries About's canonical URL, so a freshly built Method page briefly
claims to be the About page. `seo.py` is what corrects it. Run them out of order
and you publish a page that tells search engines it is a different page.

The general rule: **any script that borrows another page's shell must be
followed by the script that owns page identity.**

---

## 3. Make every build script idempotent, with fences

The first version of these scripts were one-shot migrations: run once, edit by
hand forever after. That is a trap. The second time you need the change you
either hand-edit sixteen files or write the script again.

Every stamper now writes between sentinel comments and replaces what is between
them:

```python
F0, F1 = '<!-- == method-link start == -->', '<!-- == method-link end == -->'

block = F0 + NL + CSS + NL + strip + NL + F1 + NL
if F0 in s:
    a = s.index(F0)
    b = s.index(F1) + len(F1) + 1
    s = s[:a] + block + s[b:]      # replace in place
else:
    s = s.replace('</body>', block + '</body>', 1)   # first run
```

Run it a hundred times, get the same file. This is what makes a sixteen-page
change safe to iterate on.

**Trap:** when you first plant fences around existing markup, it is very easy to
swallow a neighbouring rule that happened to sit inside the region. On this repo
that ate the `.skip-link` styles in `videos.html`. It was caught by a pixel diff,
not by reading the diff. Put shared rules *outside* the fence.

### Fail the build instead of publishing something wrong

`method_links.py` ends by reading the page it points at and calling `sys.exit`
if any anchor is missing:

```python
missing = sorted({a for a, _ in SECTION.values() if 'id="%s"' % a not in m})
if missing:
    sys.exit('anchors missing from %s: %s' % (BASE, ', '.join(missing)))
```

A broken link that fails the build costs a minute. A broken link that ships
costs credibility on a site whose whole argument is checkability.

---

## 4. The data pipeline

Feeds are Python/Node scripts run by scheduled GitHub Actions, each committing
its own output.

**The important structural fact: the updaters rewrite the dashboard HTML
directly, not just a JSON file.** Most dashboards have their numbers baked into
the markup, and only a few read JSON at runtime:

| Reads JSON in the browser | Numbers written into the HTML |
|---|---|
| `ma-housing`, `haverhill-market-report`, `nh-housing`, `tax-burden`, `immigration` | `energy`, `affordability`, `tax-budget`, `healthcare`, `pension`, `pay-to-play`, `commercial-re`, `boston`, both `education` |

If you inherit this pattern, know which column a page is in before you assume a
refresh reached it. A feed that writes only JSON, for a page that reads only
markup, produces a dashboard that is confidently stale.

*(Some sources are private and deliberately undocumented here. That omission is
intentional; do not "fix" it.)*

### Guard rails that earned their place

- **Refuse to publish a partial series.** The per-state income fetch raises
  rather than returning what it got:
  ```python
  if len(out) < 45:
      raise RuntimeError(f"nominal_income returned {len(out)} of {len(STATES)} "
                         "states - refusing to publish a partial series")
  ```
  An earlier version swallowed every failure into `continue`, so a bad run
  returned `{}` and the writer published it.

- **Cross-source invariance.** `update-burden-constants.py` asserts that
  `households × meanHouseholdIncome ÷ incomeShare` returns the same national
  aggregate for every state. Before it existed, MA implied a $14.91T national
  total and NH implied $17.50T — a 17.3% disagreement, on a line captioned
  *"identical basis"*. It now fails the build.

  **Generalise this:** when two pages derive from a shared quantity, assert the
  shared quantity, not the outputs.

- **Match names exactly.** BEA publishes Springfield IL and Springfield MO. A
  bare `"Springfield"` prefix match silently returned whichever came last.

---

## 5. Publishing: GitHub Pages from a workflow artifact

`deploy-pages.yml` uploads the whole repo (`path: '.'`) and deploys it.

### Trap: CNAME must be inside the artifact

With `build_type: workflow`, the site is served from the artifact — not from the
branch. **If `CNAME` is not in the uploaded tree, the custom domain is cleared
on the next deploy.** Keep the file committed at root and check it before any
change to what the workflow uploads.

### Trap: colliding deploys

Data workflows commit on their own schedules. Two overlapping deploys can
publish out of order — an older tree landing after a newer one. The fix is a
concurrency guard:

```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

`cancel-in-progress: false` matters. Cancelling the in-flight deploy is how you
publish the older tree.

Data workflows that push to `main` use a *separate* group (`push-to-main`) and
retry with rebase, treating a conflict on generated files as "another run
already published this window" rather than as a merge to resolve.

### Trap: caching, and iframes cache separately

Pages serves `max-age=600`. That alone is survivable. What is not obvious is
that **an iframe caches independently of its parent** — you can ship a change,
reload, see the new page, and still be looking at a ten-minute-old frame inside
it. Hours were lost to "nothing changed."

The fix is a content hash in the embed URL, computed at build time:

```python
_h = hashlib.sha1(io.open('instrument.html','rb').read()).hexdigest()[:10]
_new = re.sub(r'src="instrument\.html\?embed=1(?:&amp;v=[0-9a-f]+)?"',
              'src="instrument.html?embed=1&amp;v=%s"' % _h, _idx)
```

Change the file, change the URL, get the new frame. Unchanged file, unchanged
URL, keep the cache.

---

## 6. Verification: never claim what you have not read

This is the section that saves the most time, and it is the one most often
skipped.

**Rules:**
1. No claim about how something looks without a screenshot you have actually
   looked at.
2. No figure that was not read out of the file.
3. No "that tool isn't available" before running discovery.
4. Label inference as inference, in the same sentence.

### Headless capture without a browser library

Chrome DevTools Protocol driven straight from Node — no Puppeteer, no install.
Node 24 has global `WebSocket` and `fetch`:

```
chrome --headless=new --remote-debugging-port=PORT
       --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars
```

`--use-angle=swiftshader` is what makes a WebGL scene render headlessly. Without
it the 3D instrument screenshots as a blank rectangle and you conclude, wrongly,
that it is broken.

Two small tools carry all of it: a screenshotter (`url out w h waitMs scale css
js`) and a JS evaluator. The optional trailing `js` argument is what lets you
drive the page into a state — scroll an element into view, open a panel — before
the shutter.

**For phones, use `Emulation.setDeviceMetricsOverride`, not `--window-size`.**
The window flag clamps at about 500px, so a "390px" screenshot is a lie, and you
will fix problems the user does not have while missing the ones they do.

### Never blanket-kill the browser

Capture scripts must launch with `Start-Process -PassThru` and wait on that PID
alone. Killing every Chrome process closes the windows the person is working in.

### Pixel-diff with an established noise floor

Before trusting a diff, capture the *same* page twice and measure the
difference. On this repo the floor is a worst channel of 1. Then a refactor that
should change nothing can be proven to change nothing — the `videos.html` fence
work finished at 0 of 1,344,000 pixels differing — and a 34% diff is
unambiguously a real regression rather than rendering jitter.

---

## 7. Design system

Three brand colours, used consistently:

| Colour | Hex |
|---|---|
| Cranberry | `#680A1D` |
| Bay Blue | `#14558F` |
| Berkshire Green | `#388557` |

Typography is three CSS variables — `--font-display`, `--font-text`,
`--font-mono` — and the mono face is doing real work: it marks anything
machine-derived (source lines, status chips, jump links), which visually
separates "what the data says" from "what the site says".

### Retheming pages you do not want to touch

The dashboards were built at different times, with their own `<style>` blocks
and their own layouts. Restyling them directly would have meant sixteen
regressions waiting to happen.

Instead `assets/hub-theme.css` — 35 custom properties, loaded by 22 pages —
is included **after** each page's own styles and only *redefines the tokens
those pages already reference*. No new selectors, so no specificity fights, and
no way for a theme change to move a chart or break a layout.

This is the cheapest retheming mechanism available for inherited pages: change
what the tokens mean, not what the rules are. It only works if the original
pages used tokens at all — which is the real argument for using them from day
one, even on a one-off page.

### Trap: reveal-on-scroll animations hide content when the script is absent

`.rv` is `opacity: 0` until an IntersectionObserver adds `.vis`. The Method page
inherited the *styles* from the About shell but not the *script*, which lives in
the body that `build_method.py` replaces.

Result: all fourteen section headings were invisible on the live site — not
subtly wrong, absent — and it survived several reviews because a heading you
have never seen is hard to notice missing.

**Two lessons.** Reveal styles and the script that undoes them must travel
together or not at all. And on a reference page, do not animate the headings at
all: they are the navigation. Content whose default state is invisible is a
liability.

Always include the reduced-motion escape:

```css
@media (prefers-reduced-motion: reduce){ .rv{opacity:1;transform:none} }
```

---

## 8. Mobile

Most readers are on a phone. Desktop being fine says nothing.

- **`vh` inside an iframe measures the iframe, not the screen.** A panel sized
  `82vh` inside a `78vh` frame clips its own controls off the bottom. Size
  against the frame, or do not embed.
- **A full-viewport canvas eats vertical scrolling.** `touch-action: pan-y` on
  the canvas returns the page to the reader while leaving horizontal drag to the
  scene.
- **Reorder without restructuring** using `display: contents` on the wrapper and
  `order` on the children — this is how the tab strip moved above the fold
  without touching the desktop layout.
- **Fit a 3D camera along the view's own axis in portrait.** Reusing the
  landscape fit shrinks the subject to a chip. Scale the required distance by
  `aspect`, and remember that a `maxDistance` clamp will silently discard a
  correct fit.
- Drop scene-space labels on narrow screens rather than shrinking them to
  illegibility.

---

## 9. Honesty rules for a data site

These are editorial, and they are the reason the Method page is worth anything.

- **"Updated", not "Verified".** *Verified* asserts that a human checked the
  figure against the source on a date. Only the maintainer can assert that. If
  what you know is the vintage of the data, say *Updated* and print the vintage.

- **A "live" mark must match what the feed actually fetches.** The energy feeds
  call EIA and nothing else, so only rows whose whole source is EIA carry it.
  RGGI, DPU filings, utility rate schedules and legislative fact sheets are
  hand-maintained; a chart blending one of those with EIA is not refreshed on
  its own. Marking all seventeen rows live would have been a false claim in the
  one place the site promises not to make them.

- **A future year in a source string is a document title, not a date.** "Boston
  GHG Inventory 2023; 2030 Climate Action Plan" was printing **2030** in a column
  headed *Updated*. Drop bare future years; leave fiscal years alone, because
  FY2027 is a real forward-looking budget figure.

- **Publish what is used.** Research that no dashboard draws on is held back
  from Method — sourcing a figure nothing shows invites the question of where it
  is.

- **Do not publish instructions to yourself.** The raw `MASTER_DATA.md` was once
  linked directly; GitHub Pages serves `.md` as plain text, so the first thing a
  reader met was a note addressed to an AI assistant. Render it, or do not link
  it.

---

## 10. SEO and structured data, in one place

`seo.py` owns page identity: title, description, canonical, Open Graph, Twitter
card, icons, JSON-LD, `sitemap.xml` (21 URLs) and `robots.txt`.

One file, so a change propagates everywhere. Adding an `image` to the `Person`
node touches every page carrying that node, not just About.

The schema graph is `WebSite` → `AboutPage` / `Dataset` / `DataCatalog` with a
shared `Person` and `Organization` by `@id`. Pages that are not datasets
(templates, comparison stubs, `404.html`) are explicitly excluded and get
`noindex` instead.

**Write descriptions that replace, never defer.** A generated description that
says "learn more about our data" is worse than none.

**Do not put a count in evergreen copy.** "Sixteen dashboards" is wrong the day
you add the seventeenth, and nobody remembers the sentence exists.

---

## 11. The pitfalls, ranked by what they cost

| Pitfall | Symptom | Fix |
|---|---|---|
| `CNAME` missing from the artifact | Custom domain silently reverts | Keep it committed at root |
| Iframe caching | "Nothing changed" after a correct deploy | Content-hash the embed URL |
| Reveal styles without their script | Content invisible, not broken | Ship both, or neither |
| Overlapping Pages deploys | Older tree published after newer | `concurrency: pages`, no cancel |
| `--window-size` for phone capture | Clamps ~500px; wrong problems fixed | `Emulation.setDeviceMetricsOverride` |
| Missing `--use-angle=swiftshader` | WebGL captures blank | Add the flag before concluding anything |
| Fences swallowing neighbouring CSS | Silent visual regression | Shared rules outside the fence; pixel-diff |
| `vh` inside an iframe | Controls clipped off the bottom | Size against the frame |
| One-shot migration scripts | Hand-editing N files next time | Fenced, idempotent, re-runnable |
| Partial API series published | Plausible, wrong numbers | Raise below a floor; never `continue` |
| Prefix-matching source names | Wrong row, no error | Match with the qualifier |
| Claiming a look without a screenshot | Confident wrong statements | Capture, read, then speak |

---

## 12. Adding a new dashboard

1. Build the page. Give every chart a heading and a visible `Source:` line —
   Method is generated from those, so a chart without one cannot be documented.
2. Add a section to `MASTER_DATA.md`: `| Figure | Source | Updated |`.
3. Map the page to that section in `method_links.py`. If it is not documented
   yet, put it in `UNDOCUMENTED` rather than linking it somewhere wrong.
4. Run the chain in order, `seo.py` last.
5. Add it to `README.md` and confirm it is in `sitemap.xml`.
6. If it has a feed, write the updater to rewrite **the page**, not only a JSON
   file, unless the page reads that JSON at runtime.
7. Capture it headless at 390px and at desktop width. Read both.

---

## 13. What is deliberately not here

- How MLS data is acquired. That is private and stays private.
- API keys. All feed credentials live in repository secrets and are referenced
  only by name in workflow YAML.

---

# Part II — Building one of these from zero

Everything above describes a site about Massachusetts. Nothing about the method
is. The same shape works for a city budget, a school district, a county
sheriff's office, a utility regulator, a national agency — any subject where the
official numbers exist, are scattered, and nobody has put them in one place.

What follows is the order to build it in. The order matters more than any
individual step, because the expensive mistakes are all *sequencing* mistakes:
designing before you know what you can source, automating before you know what
is worth automating, and adding pages faster than you can document them.

**The single most common failure is building the pages first.** Pages are the
cheap part. Do the spine first.

---

## Phase 0 — Decide the claim, and the edges

Write one sentence stating what the site proves. Ours is *every figure is
checkable*. Yours might be *this is what the district actually spends per
student*, or *these are every permit issued and how long each took*.

Then write down what you are **not** covering. A scope you can fully source
beats a broad one you can only partly source — on a site whose credibility is
the product, one undocumented chart discredits the documented ones around it.

Two tests before you continue:

- Can you name the primary source for every number you intend to show? Not the
  news article about it — the agency that published it.
- If someone disputes a figure, can you show them where it came from in one
  click? If the answer needs a conversation, the design is wrong.

## Phase 1 — Build the citation register before any page

Create the register first, as a plain markdown table:

```
| Figure | Source | Updated |
|--------|--------|---------|
```

Fill a row for every figure you intend to publish. **The rule that makes this
work: if you cannot fill the row, you do not get to publish the chart.**

This inverts the usual order and it is the whole trick. Most data sites are
built chart-first and have sourcing bolted on afterwards, which is why their
sourcing is thin — by then the charts exist and nobody wants to delete one.

The register is the spine. Every page is a view of it, and the public sourcing
page is a rendering of it rather than a separate document that drifts.

## Phase 2 — Build exactly one page, completely

Resist building five. Build one, all the way, including the parts that are
tedious.

- Every chart gets a **heading** and a visible **`Source:` line** directly
  beneath it. Your generator will read those later, so this is structure, not
  decoration.
- Define your colours and three type roles as **CSS custom properties from the
  very first page** — even though it feels premature with one page. Retheming
  later works by redefining what tokens *mean* (§7); that mechanism only exists
  if the pages referenced tokens in the first place. Retrofitting tokens across
  a dozen finished pages is a week you will not want to spend.
- Make it work from `file://`. If it needs a server to render, you have taken on
  a dependency you did not need.

## Phase 3 — Write the generator, fenced from day one

Now automate what you just did by hand. Four small scripts, roughly:

| Script | Job |
|---|---|
| `build_<register>.py` | Render the register into a real page |
| `<links>.py` | Stamp a "sourced here" strip onto every content page |
| `seo.py` | Own page identity: meta, canonical, JSON-LD, sitemap, robots |
| a runner | Run them in the right order, every time |

Three rules, all of them from §3:

1. **Fenced and idempotent from the first version.** Never write a one-shot
   migration you will need twice. Sentinel comments, replace in place.
2. **Fail the build rather than publish something wrong.** Anchors that do not
   resolve, links to sections that do not exist, tokens that went missing —
   `sys.exit`. It costs a minute now instead of credibility later.
3. **Fix the run order and write it down.** Whichever script owns page identity
   runs last, because anything that borrows another page's shell inherits its
   canonical URL.

## Phase 4 — Publish before it is finished

Get it on a real domain early, with an ugly page, rather than late with a
polished one. Deploy problems are structural and you want them surfaced while
the site is small.

Static hosting is enough — GitHub Pages, Netlify, Cloudflare Pages. If you use
Pages with a workflow build, the traps in §5 apply verbatim and all three will
cost you an afternoon each if you meet them cold:

- `CNAME` must be inside the uploaded artifact or the custom domain clears;
- serialise deploys with a concurrency group, and do **not** cancel in progress;
- anything embedded in an iframe caches independently of its parent, so put a
  content hash in the embed URL.

## Phase 5 — Automate only what is genuinely automatable

Not every source deserves a feed. Automate a source when it has a real API or a
stable machine-readable file **and** it changes often enough to matter. An
annual PDF does not need a scraper; it needs a calendar reminder.

For everything you do automate:

- **Write to whatever the page actually reads.** If the numbers are baked into
  the markup, the updater must rewrite the markup. A feed that only writes JSON,
  for a page that only reads markup, produces a confidently stale dashboard —
  and it will look fine to you, because the JSON is current.
- **Put a floor under every multi-part fetch.** Refuse to publish a partial
  series. Never swallow failures into `continue`.
- **Assert invariants across sources**, not just outputs — if two pages derive
  from a shared quantity, assert the shared quantity (§4).
- **Match names with their qualifiers.** Duplicate place names across
  jurisdictions are the classic silent wrong-row bug.
- **Keep credentials in repository secrets**, referenced only by name.
- **Check the schedules actually ran.** A cron that has been failing quietly for
  six weeks is worse than no cron, because the page looks maintained.

## Phase 6 — Build the verification harness early

This is the step everyone defers and everyone regrets deferring, because
verification is what lets you move fast later without breaking things quietly.

You need two small tools (§6): a headless screenshotter and a JS evaluator,
driven over the DevTools Protocol. No browser-automation library is required —
a modern Node has everything.

Then, in this order:

1. Capture the same page twice and **establish your noise floor.** Without it a
   diff means nothing.
2. Capture at a real phone viewport using device-metrics emulation, not a window
   size flag.
3. Add `--use-angle=swiftshader` before concluding that any WebGL content is
   broken.

The discipline this buys is the important part: **never claim how something
looks without a capture you have actually read.** That single rule catches more
mistakes than any test suite you would realistically write for a site like this.

## Phase 7 — The honesty pass, before you tell anyone about it

Re-read every label as an adversary would (§9):

- Does any column claim a *human verified* something when what you know is a
  data vintage? Say **Updated**, not Verified.
- Does any "live" or "auto-updating" badge sit on a row its feed does not
  actually cover? Either narrow the badge or drop it.
- Is any date actually a document title? Future years in source strings usually
  are.
- Does any evergreen sentence contain a count that will be wrong next month?
- Is anything published that nothing on the site uses? Hold it back.
- Are you serving internal notes as raw markdown by accident? (§5, and the
  exclusion step in this repo's deploy workflow.)

## A minimum viable tree

```
index.html                 the argument, and the way in
<subject>-dashboard.html   one file per topic, standalone
method.html                generated from the register
about.html                 who made this, and how to challenge it
REGISTER.md                figure -> source -> updated, the spine
assets/theme.css           tokens only, loaded after each page's own styles
build_method.py            register -> page
method_links.py            stamp "sourced here" onto every page
seo.py                     page identity, sitemap, robots, JSON-LD
data/*.json                only for pages that read at runtime
.github/workflows/         one per feed, plus the deploy
CNAME                      if you use a custom domain
```

## What to skip

- **A framework.** Static HTML with tokens is faster to build, trivially
  hostable, and readable in a diff five years from now.
- **A CMS.** The register is your CMS.
- **Animating reference content.** Fine for a landing page. On a page whose job
  is to be looked up, content that starts invisible is a liability — see the
  fourteen headings in §7 that were invisible in production and survived several
  reviews precisely because nobody had seen them.
- **Chasing completeness before credibility.** Ten fully-sourced figures beat a
  hundred unsourced ones.

## The honest sequencing summary

```
claim -> register -> one complete page -> generator -> publish
      -> feeds -> verification harness -> honesty pass -> more pages
```

Most people do it in roughly the reverse order, which is why most data sites are
a pile of charts with a sources page nobody maintains. The register first is
what makes everything after it cheap.
