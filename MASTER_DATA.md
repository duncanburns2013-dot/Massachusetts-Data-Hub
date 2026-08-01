# Massachusetts Data Hub — Master Data Reference

> **Last Reviewed:** August 01, 2026
> **Maintainer:** Duncan Burns
> **Purpose:** Reference for hand-verified data points used across dashboards

---

## 📋 How to Use This File

When starting a new Claude chat, say:
> "See MASTER_DATA.md in my Massachusetts-Data-Hub repo for all verified figures."

Every entry includes: **figure → source → source URL → date verified → which dashboard uses it**

### ⚠️ This file is NOT the source of truth for API-fed figures

Anything a workflow refreshes on a schedule is authoritative in `data/*.json`, not here.
This file is a hand-kept reference and **will drift** between reviews. Where a row is
marked 🔄 below, read the JSON instead — that is what the dashboards actually render.

| Feed | Source of truth | Refresh |
|------|----------------|---------|
| MLS PIN housing (MA/Essex/Boston/Newburyport) | `data/mls-history.json` + live T12M in the dashboards | daily |
| NH PrimeMLS | `data/nh-figures.json` | daily |
| Census ACS | `data/census-latest.json` | monthly (20th) |
| BLS employment | `data/employment-latest.json` | monthly |
| CBP encounters | `data/cbp-encounters-latest.json` | monthly (25th) |
| IRS SOI migration | `data/irs-soi-migration-latest.json` | monthly (1st) |
| CPI / cumulative inflation | `cpi_update_status.txt` | monthly |

For everything else — the hand-verified policy, fiscal and study figures — change it here
FIRST, then update the relevant dashboard.

---

## 🛂 Immigration

### National — Border Encounters (CBP)

| Fiscal Year | SWB Encounters | Source | Verified |
|-------------|---------------|--------|----------|
| FY2017 | 415,517 | CBP | ✅ Feb 2026 |
| FY2018 | 521,090 | CBP | ✅ Feb 2026 |
| FY2019 | 977,509 | CBP | ✅ Feb 2026 |
| FY2020 | 458,088 | CBP | ✅ Feb 2026 |
| FY2021 | 1,734,686 | CBP | ✅ Feb 2026 |
| FY2022 | 2,378,944 | CBP | ✅ Feb 2026 |
| FY2023 | 2,475,669 | CBP | ✅ Feb 2026 |
| FY2024 | 2,136,800 | CBP | ✅ Feb 2026 |
| FY2025 (full year) | 237,538 | CBP (USBP only) | 🔄 Jul 2026 |
| FY2026 (thru May 2026) | 61,726 | CBP (USBP only) | 🔄 Jul 2026 |

- **FY2025 pace:** Lowest since 1970
- **FY2021-24 total:** ~10.8M nationwide encounters
- **Source URL:** https://www.cbp.gov/newsroom/stats/southwest-land-border-encounters

> **⚠️ Methodology break at FY2025 — do not compare across it.**
> FY2017–FY2024 are **total** SWB encounters (Border Patrol + Office of Field Operations
> ports of entry), from OHSS/KHSM. CBP stopped publishing the OFO port-of-entry component
> for FY2025+, so FY2025 and FY2026 above are **Border Patrol only** and are therefore not
> like-for-like with the years above them. The immigration dashboard's total series
> deliberately ends at FY2024 for this reason.
> Live figures: `data/cbp-encounters-latest.json` (🔄 refreshed monthly on the 25th).

### National — Net International Migration (Census)

| Year | NIM (persons) | Source | Verified |
|------|--------------|--------|----------|
| 2019 | 1,031,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2020 | 818,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2021 | 1,041,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2022 | 2,020,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2023 | 2,358,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2024 | 2,384,000 | Census Vintage 2025 | ✅ Feb 2026 |
| 2025 proj | 321,000 | Census Vintage 2025 | ✅ Feb 2026 |

- **Census methodology revision (Dec 2024):** 69–102% undercount in prior estimates
- **2022-24 revised total:** +6.8M (revised upward)
- **Source URL:** https://www.census.gov/programs-surveys/popest.html

### National — Deportation Math

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Entered (FY2021-24) | ~8M | CBP + Census | ✅ Feb 2026 |
| Interior removals (Biden admin) | ~600K (~150K/yr) | ICE ERO | ✅ Feb 2026 |
| Net remaining | ~7.4M | Calculated | ✅ Feb 2026 |

### National — Fiscal Impact

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Cato/NASEM cumulative surplus (1994-2023) | $14.5T | Cato White Paper 2025 | ✅ Feb 2026 |
| College grad share of surplus | $11.7T (81%) | Cato/NASEM | ✅ Feb 2026 |
| Non-college grad share | $2.8T (19%) | Cato/NASEM | ✅ Feb 2026 |
| Noncitizen share of surplus | $6.3T | Cato/NASEM | ✅ Feb 2026 |
| CBO state/local net cost (2023) | $9.2B | CBO June 2025 | ✅ Feb 2026 |
| Undocumented tax contributions (national) | $96.7B | ITEP 2024 | ✅ Feb 2026 |
| Incarceration rate vs natives | 44% less likely | Cato/NASEM | ✅ Feb 2026 |

- **Key finding:** Legal immigrants net positive at all levels; undocumented net negative at state/local
- **Cato caveat:** Paper does NOT separate legal from illegal; counts US-born children as "US-born"

### Massachusetts — Immigration Costs

| Category | Annual Cost | Source | Verified |
|----------|------------|--------|----------|
| Total annual immigration cost | ~$2.35B | Multiple state sources | ✅ Feb 2026 |
| Illegal-only cost estimate | $800M–$1.5B | CIS/FAIR/state data | ✅ Feb 2026 |
| Undocumented tax contributions (MA) | ~$1.4B total ($446M state/local) | ITEP | ✅ Feb 2026 |

### Massachusetts — Shelter Crisis

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| FY2024 shelter spending (actual) | ~$978M | EOHLC / State Auditor | ✅ Feb 2026 |
| FY2025 shelter spending | ~$978M | EOHLC | ✅ Feb 2026 |
| FY2026 shelter budget | $276M | Gov. Healey budget | ✅ Feb 2026 |
| Cost per family per week | $3,496 | State Auditor | ✅ Feb 2026 |
| $100K fee per shelter family | Proposed | Legislature | ✅ Feb 2026 |

### Massachusetts — H-1B Workers

| Year | H-1B Workers (MA) | Source | Verified |
|------|--------------------|--------|----------|
| Peak | 21,834 | USCIS | ✅ Feb 2026 |
| Current | ~7,550 | USCIS | ✅ Feb 2026 |

### Massachusetts — Concentration Cities

🔄 Live values: `data/census-latest.json` (ACS 5-year, vintage 2024, refreshed monthly on the 20th).
The figures below are that file's current contents; the Feb 2026 column showed an older ACS vintage.

| City | Foreign-Born % | Source | Verified |
|------|---------------|--------|----------|
| Chelsea | 46% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Everett | 46% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Lawrence | 45% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Revere | 44% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Malden | 41% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Lynn | 37% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Brockton | 34% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Framingham / Quincy | 33% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Lowell | 30% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Boston | 28% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Waltham | 26% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Worcester | 25% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Methuen / Somerville | 24% | ACS 2024 (5-yr) | 🔄 Jul 2026 |
| Springfield | 10% | ACS 2024 (5-yr) | 🔄 Jul 2026 |

- **60-mile radius of Beacon Hill** — inner-ring cities bearing disproportionate burden
- **Lawrence multilingual population:** 78.1%
- **Chelsea multilingual population:** 70.6%
- **Everett:** 63.4% · **Revere:** 56.3% · **Lynn:** 53.5% · **Malden:** 50.9%
- **MA median household income:** $103,960 (ACS 2024 5-yr)

### Massachusetts — Population & Migration

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| IRS returns lost (cumulative 2011–2023) | 184,719 | IRS SOI | 🔄 Aug 2026 |
| AGI lost (cumulative 2011–2023) | $24.7B | IRS SOI | 🔄 Aug 2026 |
| Net outflow, latest year (2022-23) | 16,921 returns | IRS SOI | 🔄 Aug 2026 |
| Net AGI loss, latest year (2022-23) | $4.18B | IRS SOI | 🔄 Aug 2026 |
| 2024 US growth from immigration | 84% | Census | ✅ Jan 2026 |
| MA NIM "nosedive" (2025 proj) | Historic decline | Census Vintage 2025 | ✅ Feb 2026 |

---

## 🏠 Housing & Real Estate

### Massachusetts — Median Prices (Warren Group)

| Region | Median Price | YoY Change | Source | Verified |
|--------|-------------|------------|--------|----------|
| Massachusetts | $638,000 | +3.7% | Warren Group | ✅ Jan 2026 |
| Greater Boston | $800,000 | +4.2% | Warren Group | ✅ Jan 2026 |
| Essex County | $699,000 | +5.1% | Warren Group | ✅ Jan 2026 |

- **Source URL:** https://www.thewarrengroup.com/

### Massachusetts — Average Prices (MLS PIN, 5-Year)

🔄 **Source of truth: `data/mls-history.json`** (closed sales per calendar year), regenerated
by `update-mls-figures.py`. The dashboards read that cache directly — do not hand-edit a
price here or there. Values below are the cache as of its 2026-07-17 generation.

| Year | MA Statewide | Essex County | Boston | Newburyport |
|------|-------------|--------------|--------|-------------|
| 2021 | $662,660 | $713,369 | $1,086,945 | $941,914 |
| 2022 | $720,966 | $766,970 | $1,066,003 | $1,077,706 |
| 2023 | $755,208 | $813,741 | $1,082,495 | $1,113,346 |
| 2024 | $809,406 | $870,718 | $1,132,848 | $1,234,211 |
| 2025 | $853,462 | $896,083 | $1,299,708 | $1,325,882 |

- **5-Year Growth (2021→2025):** MA +28.8%, Newburyport +40.8%, Essex +25.6%, Boston +19.6%
- **Note:** These are AVERAGES (skewed by luxury); Warren Group MEDIANS used for affordability analysis

#### Live trailing-12-month window (changes daily — do not transcribe)

The dashboards' last column is **not calendar 2026** — it is a rolling trailing-12-month
window rewritten every day. As of **August 01, 2026**: MA $863,658 · Essex $904,416 ·
Boston $1,309,225. Quote it with its as-of date or not at all.

### Massachusetts — Market Indicators

| Metric | Calendar 2025 | Trailing 12mo (as of 2026-08-01) | Source |
|--------|--------------|----------------------------------|--------|
| Avg DOM | 35.6 days | 37.7 days | MLS PIN 🔄 |
| SP/LP Ratio | 101.18% | — | MLS PIN 🔄 |
| Units Sold | 38,870 | 38,279 | MLS PIN 🔄 |
| Median Price | $670,000 | — | MLS PIN 🔄 |

> Earlier revisions of this file listed the trailing-12-month figures (DOM 38, units 38,279)
> under a "2025" heading. They are the live window, not the calendar year — split out above.

### Haverhill Specific

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Median household income | $88,326 | Census QuickFacts ACS 2020-2024 | ✅ Feb 2026 |
| MA median household income | $103,960 | ACS 2024 (5-yr), `data/census-latest.json` | 🔄 Jul 2026 |
| Condo median (Haverhill) | $390,000 | MLS | ✅ Feb 2026 |
| SF median (Haverhill) | $605,000 | MLS | ✅ Feb 2026 |
| Income needed for condo | ~$86K | Calc: 6.5%, 20% down, 28% DTI | ✅ Feb 2026 |
| Income needed for SF | ~$124K | Calc: 6.5%, 20% down, 28% DTI | ✅ Feb 2026 |

### New Hampshire — Market Data (PrimeMLS)

🔄 Source of truth: `data/nh-figures.json`, refreshed daily by `update-nh-figures.py`.
Values below are that file as of **2026-08-01**. (Feed is PrimeMLS, not Paragon.)

| Region | Median Price | Avg Sale | Avg DOM | SP/LP |
|--------|-------------|----------|---------|-------|
| NH Statewide | $441,616 | $528,884 | 29 days | 100.41% |

- **Active inventory:** 2,922 listings · median list $649,000 · avg list $864,326
- Also tracked per-market: Portsmouth, Salem, Derry, Windham

### Boston — Commercial Real Estate (CMBS)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Office vacancy (C&W) | 19.0% | Cushman & Wakefield Q2 2026 | ✅ Aug 2026 |
| Office vacancy (Colliers) | 23.7% | Colliers Q2 2026 | ✅ Aug 2026 |
| Office vacancy (CBRE) | 18.7% | CBRE Q2 2026 | ✅ Aug 2026 |
| National office vacancy | 20.1% | Cushman & Wakefield Q2 2026 | ✅ Aug 2026 |
| CMBS office delinquency | 11.57% | Trepp, June 2026 | ✅ Aug 2026 |
| CMBS all-property delinquency | 7.35% | Trepp, June 2026 | ✅ Aug 2026 |
| Pre-COVID vacancy | ~7.5% | Multiple sources | ✅ Feb 2026 |

> **Vacancy definitions differ by brokerage — these are not competing estimates of one
> number.** C&W 19.0%, CBRE 18.7% and Colliers 23.7% all describe Greater Boston Q2 2026
> on different footprints (submarket set, building class, sublease treatment). Quote the
> brokerage with the figure, and don't mix them in a single time series.
| Major sale discounts (2025) | 31–62% losses | Boston Globe / CommercialEdge | ✅ Feb 2026 |
| Boston property tax dependence | ~73% of $4.8B budget | Boston.gov | ✅ Feb 2026 |
| National avg office value decline | ~37% | Green Street | ✅ Feb 2026 |

---

## 💼 Employment & Labor

### Massachusetts — Current Labor Market

🔄 Source of truth: `data/employment-latest.json`, refreshed monthly from the BLS API.
Values below are that file as of **2026-07-31** (reference month June 2026).

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| MA unemployment rate | 4.4% | June 2026 | BLS LAUS 🔄 |
| MA unemployment level | 170,985 | June 2026 | BLS LAUS 🔄 |
| MA labor force | 3,873,506 | June 2026 | BLS LAUS 🔄 |
| MA total nonfarm | 3,719,500 | June 2026 | BLS CES 🔄 |
| US unemployment rate | 4.2% | June 2026 | BLS 🔄 |
| US job openings | 7.594M | May 2026 | BLS JOLTS 🔄 |

> **⚠️ BLS discontinued monthly state-level JOLTS in 2026.** National JOLTS is still monthly;
> state figures are annual now, first annual release July 2026. Any "MA job openings rate"
> quoted monthly is a pre-2026 series and cannot be extended.

### Massachusetts — JOLTS (historical, pre-discontinuation)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Job openings rate (peak) | ~5.5% | BLS JOLTS | ✅ Feb 2026 |
| Job openings rate (2025) | ~4.2% | BLS JOLTS | ✅ Feb 2026 |
| MA premium over national rate | Nearly gone | BLS JOLTS | ✅ Feb 2026 |

### National — Labor Market (2025)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| NFP downward revision (Apr 2024–Mar 2025) | -911,000 jobs | BLS benchmark | ✅ Feb 2026 |
| Healthcare jobs added (2025) | +713,000 | BLS CES | ✅ Feb 2026 |
| Business/professional services lost | -97,000 | BLS CES | ✅ Feb 2026 |
| Manufacturing lost | -68,000 | BLS CES | ✅ Feb 2026 |
| Federal government jobs lost since peak | -277,000 (-9.2%) | BLS CES | ✅ Feb 2026 |
| Perceived job-finding probability | 43.1% (record low) | NY Fed SCE Dec 2025 | ✅ Feb 2026 |
| Private sector hiring plans | Lowest since 2009 | Challenger/BLS | ✅ Feb 2026 |

- **Key finding:** "Hiring recession" — low-hire/low-fire environment, worst since 2009 by multiple measures
- **Healthcare masks weakness:** 713K healthcare jobs > total net gains, meaning all other sectors flat/negative

---

## 🎓 Education

### Statewide Enrollment Shifts (2019–2025)

| Sector | Change | Source | Verified |
|--------|--------|--------|----------|
| K-12 overall | -3.5% | DESE | ✅ Feb 2026 |
| Local public schools | -6.4% | DESE | ✅ Feb 2026 |
| Private schools | -1% | DESE | ✅ Feb 2026 |
| Vocational/technical | +18% | DESE | ✅ Feb 2026 |
| Charter schools | +11% | DESE | ✅ Feb 2026 |
| Homeschooling | +56% | DESE | ✅ Feb 2026 |

### Gateway Cities vs. Wealthy Towns (DESE FY2024 / MCAS 2025)

| Metric | Gateway Cities (7) | Wealthy Towns (7) | Gap |
|--------|-------------------|-------------------|-----|
| Per pupil spending | $22,887 | $26,166 | +$3,278 (+14%) |
| Overall proficiency | 20.9% | 67.6% | +46.6 pts (3.2x) |
| Failure rate | 35.4% | 7.1% | 5x higher failure |
| Teacher salary | $83,140 | $101,150 | +$18,010 (+22%) |

- **Key finding:** Wealthy towns spend only 14% more but achieve 3.2x higher proficiency
- **Sources:** DESE PerPupilExpenditures.xlsx (FY2024), NextGenMCAS.xlsx (Spring 2025), TeacherSalaries.xlsx (2020-21)

---

## 🏥 Healthcare & Insurance

### 2026 MA Rate Increases (Division of Insurance)

| Carrier | Approved Increase | Verified |
|---------|------------------|----------|
| Harvard Pilgrim | 12.2% | ✅ Feb 2026 |
| Blue Cross Blue Shield | 11.9% | ✅ Feb 2026 |
| Tufts Health | 11.1% | ✅ Feb 2026 |
| Health New England | 9.4% | ✅ Feb 2026 |
| UnitedHealthcare | 9.3% | ✅ Feb 2026 |
| MGB Health Plan | 7.2% | ✅ Feb 2026 |
| Fallon Health | 7.1% | ✅ Feb 2026 |

- **Average increase:** 9.9% (3x inflation rate of ~3%)
- **State benchmark:** 3.6%
- **Consumers affected:** 711,563
- **Saved via negotiations:** $54M

### Premium Comparisons

| Year | MA Family Premium | US Average | MA Premium Gap |
|------|-------------------|------------|----------------|
| 2024 | $28,151 | $24,540 | +14.7% |
| 2025 | — | $26,993 | — |

- **MA premium cost growth (2021-23):** +12.1%
- **MA wage growth (2021-23):** +9.7%
- **Sources:** KFF Employer Health Benefits Survey, CHIA Annual Reports

---

## 📊 Cost of Living

### SNAP vs. Poverty

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| MA SNAP participation rate | 15.6% | USDA-FNS FY2024 | ✅ Feb 2026 |
| MA poverty rate | 10.4% | Census ACS 2023 | ✅ Feb 2026 |
| MA SNAP beneficiaries | 1.11M | USDA-FNS | ✅ Feb 2026 |
| Gap (SNAP - poverty) | 5.2 pp | Calculated | ✅ Feb 2026 |

### SNAP Fraud Detection

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Expected fraud (national model) | ~$50M | USDA-FNS Trafficking Studies | ✅ Feb 2026 |
| Detected fraud (MA) | $0.69M | MA BSI Q1 FY2025 | ✅ Feb 2026 |
| Detection rate | ~1.4% | Calculated | ✅ Feb 2026 |
| Leading fraud type | Identity fraud (31%) | LexisNexis True Cost of Fraud | ✅ Feb 2026 |

---

## 🏦 Gold & Treasury

### US Treasury Gold Holdings

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Total holdings | 261.5M fine troy oz | Treasury.gov | ✅ Feb 2026 |
| Holdings change (2012-2025) | Flat / zero change | Treasury.gov | ✅ Feb 2026 |
| Fort Knox | 147.3M oz | Treasury.gov | ✅ Feb 2026 |
| West Point | 54.1M oz | Treasury.gov | ✅ Feb 2026 |
| Denver | 43.9M oz | Treasury.gov | ✅ Feb 2026 |

### Global Central Bank Buying

| Year | Annual Purchases (tonnes) | Source | Verified |
|------|--------------------------|--------|----------|
| 2010-2021 avg | ~473t | World Gold Council | ✅ Feb 2026 |
| 2022 | 1,082t (record) | World Gold Council | ✅ Feb 2026 |
| 2023 | 1,037t | World Gold Council | ✅ Feb 2026 |
| 2024 | 1,045t | World Gold Council | ✅ Feb 2026 |
| H1 2025 | 415t (~830t pace) | World Gold Council | ✅ Feb 2026 |

- **Unreported purchases (2022):** 741 tonnes (likely China, Russia)
- **Gold price (2026):** Hit $4,889/oz

---

## 🔗 Dashboard Registry

All dashboards live at `https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/<file>`.
Migration off the old repos is complete — the paths below are the real ones in this repo.

| Dashboard | File | Auto-refreshed by | Cadence |
|-----------|------|-------------------|---------|
| Immigration (National + MA) | `immigration-dashboard.html` | `update-cbp-encounters.py` | monthly (25th) |
| MA Housing Market | `ma-housing-dashboard.html` | `update-mls-figures.py` | daily |
| NH Housing Market | `nh-housing-dashboard.html` | `update-nh-figures.py` | daily |
| Haverhill Market Report | `haverhill-market-report.html` | `update-mls-figures.py` | daily |
| Master Affordability | `affordability-dashboard.html` | `update-affordability-dashboard.py` + CPI | monthly |
| MA Education (Statewide) | `education-statewide.html` | — (manual) | — |
| Boston Education | `education-boston.html` | — (manual) | — |
| Merrimack Valley Education | `education-merrimack-valley.html` | — (manual) | — |
| Healthcare Insurance | `healthcare-dashboard.html` | — (manual) | — |
| Employment | `employment-dashboard.html` | `scripts/fetch-bls-data.js` | monthly |
| Commercial RE | `commercial-re-dashboard.html` | — (manual) | — |
| Energy | `energy-dashboard.html` | `update-energy-dashboard.py` | monthly (15th) |
| Tax & Budget | `tax-budget-dashboard.html` | `update-irs-soi-migration.py` | monthly (1st) |
| Pension | `pension-dashboard.html` | — (manual) | — |
| Pay to Play | `pay-to-play-dashboard.html` | — (manual) | — |

### Old repos (superseded — these still serve older copies)

- https://duncanburns2013-dot.github.io/Immigration/
- https://duncanburns2013-dot.github.io/Housing-Market-Data/housing-market-dashboard.html
- https://duncanburns2013-dot.github.io/Housing-Market-Data/nh-housing-market-dashboard.html
- https://duncanburns2013-dot.github.io/Housing-Market-Data/haverhill-market-report.html
- https://duncanburns2013-dot.github.io/Master-Massachusetts-Affordability-Employment-/dashboard.html
- https://duncanburns2013-dot.github.io/Merrimac-Valley-Education-/
- https://duncanburns2013-dot.github.io/Merrimac-Valley-Education-/boston-dashboard.html

---

## 📝 Update Log

| Date | What Changed | Updated By |
|------|-------------|------------|
| 2026-02-05 | Initial creation — all data compiled from prior chats | Claude + Duncan |
| 2026-08-01 | Refreshed the manual dashboards. Commercial RE → Q2 2026 (C&W Boston 19.0%, US 20.1%; Colliers 23.7%; CBRE 18.7%; Trepp office delinquency 11.57%). Tax & Budget verified already current (FY2027 H.5555 enacted $63.4B, signed 2026-07-09, parsed July 2026). Healthcare held at the 2024 MA/US pair with KFF's 2025 national figure ($26,993) noted, since no MA 2025 comparator is published. Made the CPI badge and immigration hero self-stamping so they can't go stale again. | Claude + Duncan |
| 2026-08-01 | Repo audit. Reconciled this file against the live API feeds it had drifted from: ACS figures → vintage 2024, MA median income $104,800 → $103,960, MLS 5-yr table → `mls-history.json` values, NH → PrimeMLS 2026-08-01, IRS cumulative 86,382/$12.1B → 184,719/$24.7B (matching the live dashboard). Split the trailing-12-month window out from calendar 2025, recorded the CBP FY2025 methodology break and the BLS state-JOLTS discontinuation, corrected the dashboard registry. Marked API-fed rows 🔄. | Claude + Duncan |

---

*To update: Edit this file directly on GitHub, or tell Claude "update MASTER_DATA.md with [new figures]"*
