# Massachusetts Data Hub

Interactive dashboards and data analysis covering housing, immigration, education, healthcare, and affordability across the Commonwealth.

**Live Site:** https://massachusettsdatahub.com

**How this is built:** [PLAYBOOK.md](PLAYBOOK.md) - the build chain, the publishing traps, and the rules the data pages are held to.

---

## 📊 Dashboards

| Dashboard | Topic | Status | Sources |
|-----------|-------|--------|---------|
| [Immigration](immigration-dashboard.html) | Border encounters, NIM, fiscal impact, MA shelter crisis | ✅ Live | CBP, Census, ICE, CBO, Cato/NASEM |
| [MA Housing](ma-housing-dashboard.html) | Statewide, Boston, Essex County, Newburyport | ✅ Live | Warren Group, MLS PIN |
| [NH Housing](nh-housing-dashboard.html) | NH statewide with regional breakdowns | ✅ Live | Paragon MLS |
| [Haverhill Report](haverhill-market-report.html) | SF/Condo affordability deep dive | ✅ Live | MLS, Census QuickFacts |
| [Cost of Living](affordability-dashboard.html) | BEA price parities (state + metro), price-adjusted income, MIT living wage | ✅ Live | BEA, MIT, Census ACS |
| [Education (State)](education-statewide.html) | Enrollment shifts, spending, MCAS | ✅ Live | DESE, MCAS |
| [Education (Boston)](education-boston.html) | BPS absenteeism, gaps, demographics | ✅ Live | DESE, BPS |
| [Education (MV)](education-merrimack-valley.html) | Haverhill/Methuen/Lawrence — MCAS by grade, gaps, growth, absenteeism, graduation, accountability, spending | ✅ Live | DESE |
| [Healthcare](healthcare-dashboard.html) | Insurance rates, premiums, MA vs national | ✅ Live | DOI, KFF, CHIA |
| [Employment](employment-dashboard.html) | JOLTS, NFP revisions, hiring recession | ✅ Live | BLS JOLTS, CES |
| [Commercial RE](commercial-re-dashboard.html) | Boston office vacancy, CMBS, property tax | ✅ Live | Trepp, C&W, Colliers |
| [Tax Burden](tax-burden-dashboard.html) | All five layers of government burden — billed, withheld, embedded, metered, deferred | ✅ Live | IRS, DOR, DLS, CBO, DPU, Census |
| [MA vs NH Burden](tax-burden-nh-comparison.html) | Same household, both sides of the border, all five layers | ✅ Live | NH DRA, MA DOR, DLS, CBO, Census |
| [Tax & Budget](tax-budget-dashboard.html) | Income tax + surtax, state budget, rankings, cost of living | ✅ Live | DOR, BEA, BLS, Census |
| [Pensions](pension-dashboard.html) | $55.8B unfunded, PRIT, 99 municipal systems | ✅ Live | ACFR, PERAC, PPD, PRIT |
| [Energy](energy-dashboard.html) | RGGI carbon cost, electricity rates, Mass Save, GSEP | ✅ Live | EIA, RGGI Inc, ISO-NE, DPU |
| [Pay-to-Play](pay-to-play-dashboard.html) | OCPF donations from lobbying firms, sector rankings | ✅ Live | OCPF, OpenSecrets, SOC |

## 📁 Repository Structure

```
Massachusetts-Data-Hub/
├── index.html                          ← Landing page
├── template.html                       ← Reusable dashboard shell
├── MASTER_DATA.md                      ← All verified data points
├── README.md
├── immigration-dashboard.html          ← National + MA immigration
├── ma-housing-dashboard.html           ← MA housing market
├── nh-housing-dashboard.html           ← NH housing market
├── haverhill-market-report.html        ← Haverhill deep dive
├── affordability-dashboard.html        ← What it costs to live in MA (BEA + MIT)
├── education-statewide.html            ← MA education statewide
├── education-boston.html                ← Boston Public Schools
├── education-merrimack-valley.html     ← Haverhill/Methuen/Lawrence
├── healthcare-dashboard.html           ← Insurance & premiums (planned)
├── employment-dashboard.html           ← JOLTS & labor market (planned)
├── commercial-re-dashboard.html        ← Boston office/CMBS (planned)
├── tax-burden-dashboard.html           ← Total burden incidence model
├── tax-burden-nh-comparison.html       ← Cross-border burden comparison
├── tax-budget-dashboard.html           ← Tax, budget & rankings
├── pension-dashboard.html              ← Unfunded liabilities
├── energy-dashboard.html               ← Energy policy & carbon cost
├── pay-to-play-dashboard.html          ← Lobbying & campaign finance
├── data/burden-constants.json          ← Shared constants for BOTH burden dashboards
├── update-burden-constants.py          ← Regenerates the K block in both; see below
├── make-watermark.py                   ← Builds the MA/NH map watermark on the share cards
├── data/geo/                           ← State boundary GeoJSON + generated SVGs
└── pdftext.py                          ← Stdlib PDF text extraction for blocked sources
```

## 🗺️ The share-card watermark

Both cards carry a faint MA (Bay Blue) / NH (red) map behind the headline. Real
boundary geometry — Census-derived GeoJSON in `data/geo/`, simplified by
`make-watermark.py`. Regenerate with:

```bash
python make-watermark.py data/geo/massachusetts.geojson data/geo/new-hampshire.geojson
```

Two things about it are not optional, both learned by breaking them:

- **It's an inline SVG data-URI, not an external image or a CSS gradient.** html2canvas
  silently drops gradients, and `#cardShot` *is* the shareable PNG.
- **The SVG carries explicit `width`/`height`, not just a `viewBox`.** Without intrinsic
  dimensions html2canvas renders the card with no map at all — and does it silently. The
  first version looked perfect on screen and exported blank; caught by diffing an export
  against one rendered with the background turned off.

## 🔒 Shared burden constants

`tax-burden-dashboard.html` and `tax-burden-nh-comparison.html` both need the same
Massachusetts figures. Rather than hand-editing two files and eventually publishing two
dashboards that contradict each other, both read a generated block:

```bash
python update-burden-constants.py            # verify + write both files
python update-burden-constants.py --check    # verify only, write nothing
```

Edit `data/burden-constants.json`, never the `K` object inside the HTML. The script
enforces three gates and exits non-zero on any of them:

1. **Provenance** — every figure needs `source`, `url` and `verified`. A figure marked
   `verified: false` blocks publication (override with `--allow-unverified` for drafts).
2. **Derivation** — `meanHouseholdIncome` and `incomeShare` are computed from
   ACS `B19025 ÷ B11001`, never hardcoded, and all states must share one ACS release.
3. **Invariance** — the federal layers must be identical across states for a given
   household income. Layer 5 reduces algebraically to
   `deficit × income ÷ national aggregate income`, so any divergence means the state
   constants disagree with each other. This gate caught a live 17.3% inconsistency in
   the NH figures that was making the cross-border dashboard contradict its own
   headline finding.

⚠️ **Known limitation:** the script unifies the *constants*, not the *model code*. The
two dashboards still carry their own copies of the tax engine. Changing incidence logic
in one still requires changing the other.

## 🧾 Unverified constants

**None.** Every constant is sourced to a primary reference with a URL and a verification
date, and `python update-burden-constants.py` exits 0.

### The Layer 4 inclusion rule

Utility policy charges needed a stated rule rather than a judgment call:

> A charge is a **policy cost** if it exists because of a legislative or regulatory
> mandate, rather than because of the physical cost of generating and delivering energy.

On that test, from the filed tariffs:

| | Massachusetts | New Hampshire |
|---|---|---|
| Electric | **3.789¢/kWh** — EE 2.292, NMRS 0.625, SMART 0.583, EV 0.238, RE 0.050, ESMP 0.001 | **0.618¢/kWh** — System Benefits Charge only |
| Gas | **59.08¢/therm** — EE 41.70 + GSEP 17.38 | **16.30¢/therm** — Liberty LDAC |

Excluded on both sides as infrastructure or mechanism: distribution, transmission,
revenue decoupling, regulatory reconciliation, stranded cost, customer charge.

Electricity is genuinely like-for-like — both figures are **Eversource**, the same
company operating on both sides of the border. Gas is not: Eversource doesn't serve NH
gas, so that side is Liberty EnergyNorth.

**Both figures are conservative, in the same direction.** MA's is a *floor* — its own
tariff footnote puts 83C/83D offshore wind, solar programme and grid modernisation inside
the Distribution charge, unbroken out, and RPS/CES sits inside supply. NH's gas figure is
a *ceiling* — the LDAC bundles mechanisms MA excludes. So the real gap is wider than
shown.

The headline finding: **MA gas policy charges (59.08¢/therm) exceed the cost of the gas
itself (38.42¢/therm).** The old 18¢ placeholder understated it by more than 3×.

## 🚫 What is deliberately NOT counted

**State and local pension debt.** These are household calculators, and the test for every
line is whether a household actually pays it. An unfunded pension liability is not billed
to anyone — it's a claim on future tax capacity, and the portion collected today arrives
through the appropriation funded by the income and property taxes Layer 1 already counts.
Including it double-counts.

It is also the one item that cannot be sourced symmetrically across the border: the MA
figure omits most of the ~104 municipal systems PERAC tracks while NHRS is a single
statewide system covering municipal employees, and MA carries $13.7B of OPEB with no NH
counterpart sourced. Including it would tilt the comparison by construction.

The obligations are real, so both are **disclosed beside Layer 5** as per-household
stocks with that caveat attached, and told properly in `pension-dashboard.html`. The
inputs remain editable for anyone who disagrees; they simply default to zero.

Removing it also made the analysis better, not just safer: Layer 5 is now entirely
federal and therefore genuinely identical on both sides, and the compression finding now
holds at $75k where the old asymmetric guess (MA $2,000 vs NH $1,600) had been
manufacturing a $400 NH advantage out of nothing.

## 🔧 Reading PDFs that block automated download

`pdftext.py` extracts text from PDFs with the standard library only — no poppler, no
pypdf. Written because several primary sources here (NH DAS, CBO, Census) return 403 to
scripted clients and ship subset fonts whose glyph ids sit at a fixed offset below ASCII.

```bash
python pdftext.py FILE.pdf              # auto-detects the encoding offset
python pdftext.py FILE.pdf --offset 29  # force it
```

Handles indirect `/Length`, object streams, and both 1-byte and 2-byte text operands.
NH DAS revenue PDFs decode at offset 29.

**Downloading them:** a browser User-Agent does not help — those sites fingerprint the
TLS stack, so `curl`/PowerShell/WebFetch all fail where a real browser succeeds. Open the
site in a browser, then `fetch()` the file from the page's own JS context.

**Census:** the ACS API now requires `CENSUS_API_KEY` on every request. Keep it in `.env`
(gitignored). Query shape:

```
https://api.census.gov/data/2024/acs/acs1?get=NAME,B11001_001E,B19025_001E,B01003_001E&for=state:25,33&key=$CENSUS_API_KEY
```

## 🧱 Using the Template

1. Copy `template.html` to a new file (e.g., `healthcare/index.html`)
2. Update the hero title and stat badges
3. Add/rename tabs in the nav bar
4. Add chart data to `initCharts()` switch cases
5. Commit and push — GitHub Pages handles the rest

The template includes pre-solved bugs:
- ✅ Tab system that actually works (no `event.target` issues)
- ✅ Lazy chart initialization (prevents "exceeded max connections")
- ✅ Chart cleanup on tab switch (no memory leaks)
- ✅ Responsive grid (mobile → tablet → desktop)
- ✅ Utility functions (`nF()`, `dF()`, `pF()`, `safeChart()`)

## 📋 Master Data Reference

[MASTER_DATA.md](MASTER_DATA.md) is the single source of truth for all figures used across dashboards. Every entry includes the figure, source, source URL, and verification date.

When starting a new Claude chat, say:
> "See MASTER_DATA.md in my Massachusetts-Data-Hub repo for all verified figures."

## 🚀 Deployment

This site is hosted via GitHub Pages:
1. Settings → Pages → Deploy from branch: **main** / **root**
2. Live at: `https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/`

## 📄 Migration from Old Repos

Dashboards are being migrated from these repos:
- `duncanburns2013-dot/Immigration`
- `duncanburns2013-dot/Housing-Market-Data`
- `duncanburns2013-dot/Master-Massachusetts-Affordability-Employment-`
- `duncanburns2013-dot/Merrimac-Valley-Education-`

Old repos will remain active until migration is complete.

---

*Data compiled February 2026 · All data from official government sources*
