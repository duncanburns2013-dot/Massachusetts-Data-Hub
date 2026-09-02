# Massachusetts Data Hub — Master Data Reference

> **Last Reviewed:** August 22, 2026
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
| 2022 | $720,966 | $766,970 | $1,066,003 | $1,077,707 |
| 2023 | $755,209 | $813,741 | $1,082,495 | $1,113,346 |
| 2024 | $809,407 | $870,718 | $1,132,849 | $1,234,212 |
| 2025 | $853,462 | $896,083 | $1,299,708 | $1,325,883 |
| 2026 | $866,387 | $904,504 | $1,320,806 | $1,228,098 |

- **5-Year Growth (2021→2025):** MA +28.8%, Newburyport +40.8%, Essex +25.6%, Boston +19.6%
- **Note:** These are AVERAGES (skewed by luxury); Warren Group MEDIANS used for affordability analysis

#### Live trailing-12-month window (changes daily — do not transcribe)

The dashboards' last column is **not calendar 2026** — it is a rolling trailing-12-month
window rewritten every day. As of **September 02, 2026**: MA $866,387 · Essex $904,504 ·
Boston $1,320,806. Quote it with its as-of date or not at all.

### Massachusetts — Market Indicators

| Metric | Calendar 2025 | Trailing 12mo (as of 2026-09-02) | Source |
|--------|--------------|----------------------------------|--------|
| Avg DOM | 35.6 days | 38 days | MLS PIN 🔄 |
| SP/LP Ratio | 101.18% | 100.92% | MLS PIN 🔄 |
| Units Sold | 38,870 | 38,631 | MLS PIN 🔄 |
| Median Price | $670,000 | $679,000 | MLS PIN 🔄 |

> Earlier revisions listed the trailing-12-month figures under a "2025" heading —
> most recently "Units Sold 39,323 ✅ Feb 2026", which is the live window, not the
> calendar year, and not a February figure. They are separated above.

### Haverhill Specific

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Median household income | $88,326 | Census QuickFacts ACS 2020-2024 | ✅ Feb 2026 |
| MA median household income | $103,960 | ACS 2024 (5-yr), `data/census-latest.json` | 🔄 Jul 2026 |
| Condo median (Haverhill) | $387,962 | MLS | ✅ Feb 2026 |
| SF median (Haverhill) | $610,000 | MLS | ✅ Feb 2026 |
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

### National — Employment Situation Release Dates

Machine-readable copy lives in [`data/bls-release-schedule.json`](data/bls-release-schedule.json); the employment updater reads it to stamp "Released &lt;date&gt;" on the national block.

| Reference Month | Released | Source | Verified |
|-----------------|----------|--------|----------|
| November 2025 | Dec 16, 2025 | BLS schedule | ✅ Aug 2026 |
| December 2025 | Jan 09, 2026 | BLS schedule | ✅ Aug 2026 |
| January 2026 | Feb 11, 2026 | BLS schedule | ✅ Aug 2026 |
| February 2026 | Mar 06, 2026 | BLS schedule | ✅ Aug 2026 |
| March 2026 | Apr 03, 2026 | BLS schedule | ✅ Aug 2026 |
| April 2026 | May 08, 2026 | BLS schedule | ✅ Aug 2026 |
| May 2026 | Jun 05, 2026 | BLS schedule | ✅ Aug 2026 |
| June 2026 | Jul 02, 2026 | BLS schedule | ✅ Aug 2026 |
| July 2026 | Aug 07, 2026 | BLS schedule | ✅ Aug 2026 |
| August 2026 | Sep 04, 2026 | BLS schedule | ✅ Aug 2026 |
| September 2026 | Oct 02, 2026 | BLS schedule | ✅ Aug 2026 |
| October 2026 | Nov 06, 2026 | BLS schedule | ✅ Aug 2026 |
| November 2026 | Dec 04, 2026 | BLS schedule | ✅ Aug 2026 |

- **Not a first-Friday rule.** April 2026 went out on the *second* Friday (May 8) and June 2026 on a *Thursday* (Jul 2, moved for July 4). These dates cannot be computed — they must be read from the published schedule.
- **Source URL:** https://www.bls.gov/schedule/news_release/empsit.htm

### Massachusetts — State Employment & Unemployment Release Dates

The MA vintage. Lands ~3 weeks after the national release, which is why the MA blocks on the employment dashboard legitimately sit a month behind the national block. Same JSON file, `state_employment` key.

| Reference Month | Released | Source | Verified |
|-----------------|----------|--------|----------|
| November 2025 | Jan 07, 2026 | BLS schedule | ✅ Aug 2026 |
| December 2025 | Jan 27, 2026 | BLS schedule | ✅ Aug 2026 |
| January 2026 | Apr 08, 2026 | BLS schedule | ✅ Aug 2026 |
| February 2026 | Apr 22, 2026 | BLS schedule | ✅ Aug 2026 |
| March 2026 | May 06, 2026 | BLS schedule | ✅ Aug 2026 |
| April 2026 | May 22, 2026 | BLS schedule | ✅ Aug 2026 |
| May 2026 | Jun 23, 2026 | BLS schedule | ✅ Aug 2026 |
| June 2026 | Jul 21, 2026 | BLS schedule | ✅ Aug 2026 |
| July 2026 | Aug 21, 2026 | BLS schedule | ✅ Aug 2026 |
| August 2026 | Sep 18, 2026 | BLS schedule | ✅ Aug 2026 |
| September 2026 | Oct 20, 2026 | BLS schedule | ✅ Aug 2026 |
| October 2026 | Nov 20, 2026 | BLS schedule | ✅ Aug 2026 |
| November 2026 | Dec 18, 2026 | BLS schedule | ✅ Aug 2026 |

- **Even less regular than the national schedule.** The January 2026 reference month did not appear until **April 8, 2026**.
- **Source URL:** https://www.bls.gov/schedule/news_release/laus.htm
- **Maintenance:** BLS publishes ~13 months ahead. When the newest reference month is missing, the updater logs a `::warning::` in the Actions run and renders an em dash instead of inventing a date — that warning is the cue to top up the table above and the JSON.
- **Note:** bls.gov HTML 403s non-browser clients, so this cannot be scraped from CI (the same block that stalled the CBP feed). `api.bls.gov` serves the figures but carries no release dates.

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

## 🧾 Tax Burden — Federal & Massachusetts

Machine-readable source of truth: [`data/burden-constants.json`](data/burden-constants.json).
Both burden dashboards are generated from it by `update-burden-constants.py`. Change the
JSON, not the HTML.

| Figure | Value | Source | URL | Verified |
|---|---|---|---|---|
| Federal standard deduction TY2026 | $16,100 single / $32,200 MFJ | IRS Rev. Proc. 2025-32 | irs.gov/pub/irs-drop/rp-25-32.pdf | ✅ Aug 2026 |
| Social Security wage base 2026 | $184,500 | SSA contribution & benefit base | ssa.gov/oact/cola/cbb.html | ✅ Aug 2026 |
| MA income tax rate | 5.0% flat | M.G.L. c. 62 §4 | malegislature.gov | ✅ Aug 2026 |
| MA 4% surtax threshold TY2026 | $1,107,750 | M.G.L. c. 62 §§4(d), 5A; DOR | mass.gov/info-details/massachusetts-4-surtax-on-taxable-income | ✅ Aug 2026 |
| MA interest, dividends & long-term gains | 5% | M.G.L. c. 62 §4(a),(c) | mass.gov/info-details/massachusetts-income-tax-rates | ✅ Aug 2026 |
| MA short-term capital gains | 8.5% (cut from 12%, St. 2023 c. 50) | M.G.L. c. 62 §4(c) | same | ✅ Aug 2026 |
| MA motor fuel excise | **26.5¢/gal** (24¢ + 2.5¢ UST) | M.G.L. c. 64A §1; c. 21J §3 | mass.gov/info-details/motor-fuel-excise-tax | ✅ Aug 2026 |
| MA avg single-family tax bill FY2026 | $8,113 | DLS *City & Town*, Feb 2026 | mass.gov/info-details/fy2026-statewide-average-single-family-tax-bill | ✅ Aug 2026 |
| MA avg single-family assessed value FY2026 | $742,986 → 1.092% effective | DLS *City & Town*, Feb 2026 | same | ✅ Aug 2026 |
| MA corporate & business excise FY2025 | $4.662B | DOR FY2025 close, Aug 2025 | mass.gov/news/fiscal-year-2025-revenue-collections-totaled-43708-billion | ✅ Aug 2026 |
| MA households | 2,829,804 | Census ACS 2024 1-yr, B11001 | censusreporter.org/profiles/04000US25-massachusetts/ | ✅ Aug 2026 |
| MA aggregate household income | $408.376B | Census ACS 2024 1-yr, B19025 | same | ✅ Aug 2026 |
| **MA mean household income** | **$144,312** (B19025 ÷ B11001) | Derived — the allocation divisor | same | ✅ Aug 2026 |
| MA population | 7,044,056 | Census ACS 2024 5-yr, B01003 | same | ✅ Aug 2026 |
| MA share of national household income | 2.6918% (derived) | ACS B19025 ÷ national B19025 | same | ✅ Aug 2026 |
| MA share of national population | 2.1032% (derived) | ACS B01003 | same | ✅ Aug 2026 |
| US households | 132,737,144 | Census ACS 2024 1-yr, B11001 | censusreporter.org/tables/B11001/ | ✅ Aug 2026 |
| US aggregate household income | $15.171T | Census ACS 2024 1-yr, B19025 | censusreporter.org/tables/B19025/ | ✅ Aug 2026 |
| Federal deficit FY2025 | $1.8T (5.8–5.9% of GDP) | CBO Monthly Budget Review, Oct 2025 | cbo.gov/publication/61307 | ✅ Aug 2026 |
| **Federal corporate income tax receipts FY2025** | **$452,089,303,420** (net) | U.S. Treasury, Final Monthly Treasury Statement Sept 2025, Table 4 | api.fiscaldata.treasury.gov — mts_table_4 | ✅ Aug 2026 |
| Federal corporate receipts FY2024 | $529,866,802,638 — FY25 is −14.7% | same | same | ✅ Aug 2026 |
| MA unfunded pension + OPEB (stock) | $55.8B total · $42.1B pension-only · $19,719/household | Commonwealth ACFR FY2024; PERAC | See pension-dashboard.html | ✅ Aug 2026 |
| MA annual pension appropriation FY2026 | $4.9B — ~8% of the state budget, **already in Layer 1** | Commonwealth budget FY2026 | same | ✅ Aug 2026 |
| **MA residential electricity, all-in** | **28.82¢/kWh** (May 2026; 29.90¢ May 2025, −3.6%) | EIA Electric Power Monthly Table 5.6.A via API v2 | api.eia.gov/v2/electricity/retail-sales/data/ | ✅ Aug 2026 |
| **NH residential electricity, all-in** | **27.33¢/kWh** (May 2026; 24.02¢ May 2025, **+13.8%**) | same | same | ✅ Aug 2026 |
| US / New England residential electricity | 18.44¢ / 28.14¢ (May 2026) | same | same | ✅ Aug 2026 |
| **MA electric policy charges** | **3.789¢/kWh** — EE 2.292 + NMRS 0.625 + SMART 0.583 + EV 0.238 + RE 0.050 + ESMP 0.001 | Eversource MA filed tariff, Rate R1, eff. 1 Jul 2026 | eversource.com/…/electric-delivery-rates/egma | ✅ Aug 2026 |
| **MA gas policy charges** | **59.08¢/therm** — EE 41.70 + GSEP 17.38 | Eversource MA Summary of Gas Rates | eversource.com/docs/default-source/rates-tariffs/summary-rates-gas.pdf | ✅ Aug 2026 |
| MA gas commodity cost | 38.42¢/therm (eff. 1 May 2026) — **less than the policy riders above** | Eversource MA Cost of Gas | eversource.com/…/ma-cost-of-gas | ✅ Aug 2026 |
| MA electric distribution / transmission | 9.443¢ / 4.673¢ per kWh — excluded as infrastructure | same tariff | same | ✅ Aug 2026 |
| MA pension-only unfunded (stock) | $42.1B · $14,877/household | Commonwealth ACFR FY2024; PERAC | See pension-dashboard.html | ✅ Aug 2026 |
| MA state/local accrual in the burden model | **$0 — excluded by design**, see note below | Scope decision | — | ✅ Aug 2026 |

### ⚠️ The two MA median-income figures — do not merge them

| Vintage | Value | Concept | Use |
|---|---|---|---|
| Census **CPS ASEC** via FRED `MEHOINUSMAA646N` | **$113,900** | Median household income 2024 | Context / presets |
| Census **ACS 1-year** B19013 | **$104,828** | Median household income 2024 | Context / presets |
| Census **ACS 1-year** B19025 ÷ B11001 | **$144,312** | *Mean* household income | **Allocation divisor** |

CPS and ACS disagree by ~$9K on the same concept. Carry both and cite which one any
given chart uses — this is exactly the kind of thing a hostile reader finds first.

**~~Known defect to fix~~ — FIXED 2026-08-11.** `tax-budget-dashboard.html` labelled
$113,900 as "Census 2024 ACS"; it is the **CPS** figure and is now labelled "Census CPS
ASEC (2024)" in both places, with the $104,828 ACS comparator named inline. The same file
carried an unlabelled "$7,732/year" property tax figure; the hero stat, the prose and the
stat card now read **$8,113 (FY2026)**. The FY2025 county table keeps its own FY2025
source line — it was already labelled correctly and its county figures are FY2025.

The `chartIncomeReal` cross-state bar series still uses 113,900 for MA. Left alone
deliberately: the other seven states' vintage is undocumented, and swapping MA to ACS
without knowing theirs would trade a labelling error for a comparability error. **Open
item:** establish the vintage of the other states, then make all eight consistent.

**Never use a median as an allocation divisor.** Per-household shares must sum back to
the statewide pool, which only works with the mean. The reconciliation panel on the
burden dashboard checks this.

---

## 🏛️ State Budget — the scope reconciliation

> **Read this before quoting any Massachusetts budget total.** Three different numbers
> circulate for the same fiscal year. They are all correct; they are different scopes.
> Quoting one without naming its scope is how the same year ends up with three answers.

The official GAA workbooks split every account into four types. The **headline figure the
press release and the media quote is the first three, and excludes Intragovernmental
Service Spending.**

| Account type | FY24 | FY25 | FY26 GAA | FY26 *proj.* | **FY27 GAA** |
|---|---:|---:|---:|---:|---:|
| Budgetary Direct Appropriations | 53.384 | 54.749 | 57.905 | 61.661 | **60.292** |
| Section 2E Consolidated Transfer | 1.940 | 2.245 | 2.290 | 2.452 | **2.288** |
| Budgetary Retained Revenues | 0.739 | 0.724 | 0.779 | 0.764 | **0.836** |
| Intragovernmental Service Spending | 0.737 | 0.787 | 0.853 | 0.838 | **0.901** |
| **All four types** | 56.800 | 58.505 | 61.826 | 65.715 | **64.317** |
| **HEADLINE SCOPE** (first three) | 56.063 | 57.718 | 60.974 | 64.877 | **63.416** |

$B. Source: official mass.gov GAA export `gaabudgets.xlsx`. ✅ Verified Aug 2026.

**Proof the definition is right, not inferred:** 60.292 + 2.288 + 0.836 = **$63.416B**,
matching `summary-fy-27-enacted-budget-summary.csv`'s Total row of **$63,416,035,478** to
the dollar, and the press release's "$63.42 billion".

### FY2027 enacted — key figures

| Figure | Value | Source | Verified |
|---|---|---|---|
| FY2027 GAA, headline scope | **$63.416B** (+4.01% over FY26) | H.5555, signed 9 Jul 2026 | ✅ Aug 2026 |
| **Governor's vetoes** | **$0 — none.** Signed the conference report untouched | Globe / CommonWealth Beacon, 9 Jul 2026 | ✅ Aug 2026 |
| Votes | Senate 39–1, House 142–6 | State House News | ✅ Aug 2026 |
| Chapter 70 | **$7,658,399,506** (+$793.5M, +11.6%) — *final year of the SOA ramp* | `sect3.xlsx` | ✅ Aug 2026 |
| — municipal / regional split | $6,695,466,289 / $962,933,217 | same | ✅ Aug 2026 |
| Unrestricted General Government Aid | **$1,363,109,516** (+$40M, +3.0%) | same | ✅ Aug 2026 |
| SpEd Circuit Breaker | $654.6M (+35.0%); $806.6M incl. Fair Share supp. | `gaabudgets.xlsx` | ✅ Aug 2026 |
| Fair Share surtax deployed | ~$2.7B (~64% education / ~36% transportation) | MTF | ✅ Aug 2026 |
| Emergency Assistance family shelter | $259.9M (−6.0%; was $325.3M in FY24) | `gaabudgets.xlsx` | ✅ Aug 2026 |
| State Retiree Benefits Trust (OPEB) deposit | **$400M**, down from $550M in FY24 (−27%) | line 1595-6152 | ✅ Aug 2026 |
| Line items in `tax-budget-dashboard.html` | 860, **all 860 verified against the official GAA** | `gaa1.xlsx` diff | ✅ Aug 2026 |

### ⚠️ Enacted ≠ spent — the supplemental gap

Like-for-like (identical 913-account universe, headline scope, inter-fund transfer lines
excluded from both sides):

| FY | Enacted | Actual / projected | Overrun |
|---|---:|---:|---:|
| FY24 | 55.870 | 55.958 | +0.2% |
| FY25 | 57.567 | 63.303 | **+10.0%** |
| FY26 | 60.956 | 64.859 (proj.) | **+6.4%** |
| FY27 | 63.400 | — not begun | — |

Plotted as `h5Outturn` on `tax-budget-dashboard.html`.

> **Do not compute this by summing `gaaspend.xlsx` raw.** That file contains inter-fund
> transfer accounts — `1595-0029` (GF → Education & Transportation Fund) alone is **$5.3B**
> in FY25 — which were never appropriated and appear on only one side. Summing raw
> overstates the FY25 "overrun" as +25.7% instead of the true +10.0%. Exclude accounts whose
> description begins *Transfer* or *XFR*, and restrict to accounts present in both workbooks.

### ⚠️ Local-aid CSV ingestion gotcha

`summary-fy-27-local-aid-aid-to-municipalities.csv` carries a **`Total Municipal Aid`
footer row inside the data body**, plus a blank row before it. A naive `read_csv().sum()`
double-counts it and reports Chapter 70 at **$13.39B instead of $6.70B** — a 100%
overstatement. Filter out any row whose municipality name contains "Total" before
aggregating. The per-town figures themselves are correct.

Note also that the municipal CSV **omits regional school districts** (Triton, Pentucket,
Whittier and the rest). Regional Ch70 flows to the *district*, not the member towns, which
is why Newbury, Rowley, West Newbury and Salisbury show only $13K–$19K of Chapter 70 and
are effectively UGGA-only. Use `sect3.xlsx` when districts matter.

---

## 🗽 Tax Burden — New Hampshire

| Figure | Value | Source | URL | Verified |
|---|---|---|---|---|
| NH individual income tax | **0%** — I&D repealed 1 Jan 2025 | NH DRA; HB 2 (2023) ch. 79 §§86-88 | revenue.nh.gov/news-and-media/repeal-nh-interest-and-dividends-tax-now-effect | ✅ Aug 2026 |
| NH I&D rate history | 5% → 4% (2023) → 3% (2024) → 0% (2025) | NH DRA | revenue.nh.gov/taxes-glance/interest-dividends-tax | ✅ Aug 2026 |
| NH capital gains tax | **None — never levied** (not a 2025 change) | NH DRA | revenue.nh.gov/taxes-glance | ✅ Aug 2026 |
| NH general sales tax | None | NH DRA | revenue.nh.gov | ✅ Aug 2026 |
| NH Meals & Rooms tax | 8.5% | RSA 78-A | revenue.nh.gov/taxes-glance/meals-rentals-tax | ✅ Aug 2026 |
| NH Business Profits Tax | 7.5% | RSA 77-A | revenue.nh.gov/taxes-glance/business-taxes | ✅ Aug 2026 |
| NH Business Enterprise Tax | 0.55% on compensation + interest + dividends paid | RSA 77-E | same | ✅ Aug 2026 |
| NH Real Estate Transfer Tax | $0.75 per $100, **each side** | RSA 78-B | revenue.nh.gov | ✅ Aug 2026 |
| NH households | 570,689 | Census ACS 2024 1-yr, B11001 | censusreporter.org/profiles/04000US33-new-hampshire/ | ✅ Aug 2026 |
| NH aggregate household income | $73.393B | Census ACS 2024 1-yr, B19025 | same | ✅ Aug 2026 |
| **NH mean household income** | **$128,604** (B19025 ÷ B11001) | Derived — allocation divisor | same | ✅ Aug 2026 |
| NH median household income 2024 | $99,782 | Census ACS 2024 1-yr, B19013 | same | ✅ Aug 2026 |
| NH population | 1,394,868 | Census ACS 2024 5-yr, B01003 | same | ✅ Aug 2026 |
| NH share of national household income | **0.4838%** (derived) | ACS B19025 ÷ national B19025 | same | ✅ Aug 2026 |
| NH share of national population | 0.4165% (derived) | ACS B01003 | same | ✅ Aug 2026 |
| **NH average municipal property rate 2025** | **$15.83 per $1,000 → 1.583%** (was $20.96 in 2019) | NH Fiscal Policy Institute | nhfpi.org/resource/property-taxes-in-new-hampshire-how-they-work-and-how-they-compare/ | ✅ Aug 2026 |
| NH per-capita property tax FY2022 | $3,388 — **2nd highest state**, behind NJ $3,617 | NHFPI | same | ✅ Aug 2026 |
| NH property tax reliance | 60% (NHFPI) vs 63–64% (InDepthNH) — **carry both** | NHFPI / InDepthNH | same | ✅ Aug 2026 |
| **NHRS unfunded liability** | **$5.58B**, 68.6% funded (30 Jun 2024) · $9,778/household | NHRS ACFR + GASB 67/74, FY2025 release | nhrs.org/docs/default-source/gasb/ | ✅ Aug 2026 |
| NH municipal rate range | $2.62 – $36.54 per $1,000 | InDepthNH, Apr 2026 | indepthnh.org | ✅ Aug 2026 |
| NH property tax share of state+local revenue | 63–64% | InDepthNH / NHFPI, Apr 2026 | same | ✅ Aug 2026 |
| **NH business taxes FY2025 (BPT+BET)** | **$1,102.6M** — Gen $670.5M + Ed $432.1M | NH DAS Monthly Revenue Focus, June FY2025 accrual | das.nh.gov/accounting/FY%2025/FY2025_Monthly_Revenue_June_Preliminary_Accrual.pdf | ✅ Aug 2026 |
| NH business taxes FY2024 | $1,217.9M (FY25 is −9.5%, and −12.4% vs the $1,259.0M plan) | same | same | ✅ Aug 2026 |
| NH BPT / BET split | 75% / 25% — **assumed** | DAS publishes them combined; split needs NH DRA | revenue.nh.gov/taxes-glance/business-taxes | ⚠️ Split unverified |
| NH Interest & Dividends revenue FY2025 | $90.8M, down 50.7% from FY2024's $184.3M | NH DAS, June FY2025 accrual | same | ✅ Aug 2026 |
| NH General + Education Fund revenue FY2025 | $3,122.7M, 1.3% below plan | NH DAS, June FY2025 accrual | same | ✅ Aug 2026 |
| NH road toll (gas) | **23.75¢** = 22.2¢ toll + ~1.55¢ oil discharge surcharge | RSA 260:32 (base $0.18, +4.2¢ per 2014 SB 367); RSA 146-A | gc.nh.gov/rsa/html/XXI/260/260-32.htm | ✅ Aug 2026 |
| NH BET share of business taxes | 25.7% (5-yr TY2019–23 avg); TY2023 BET = $253M | NHFPI | nhfpi.org/resource/business-enterprise-tax-rate-decreases-have-lowered-revenue-with-limited-economic-benefit/ | ✅ Aug 2026 |
| NH BET rate history | 0.75% → 0.72% (2016) → 0.675% (2018) → 0.6% (2019) → 0.55% (2022–) | NHFPI | same | ✅ Aug 2026 |
| **NH electric policy charges** | **0.618¢/kWh** — System Benefits Charge, the only mandated rider | Eversource NH filed tariff, Rate R | eversource.com/…/electric-delivery-rates/nh | ✅ Aug 2026 |
| **NH gas policy charges** | **16.30¢/therm** — Liberty EnergyNorth LDAC (a *ceiling*, bundles mechanisms MA excludes) | NHPUC DG 24-098; see also DE 25-071 | new-hampshire.libertyutilities.com | ✅ Aug 2026 |
| NH electric distribution / transmission | 6.727¢ / 4.445¢ per kWh — excluded as infrastructure | Eversource NH Rate R | same | ✅ Aug 2026 |
| NH stranded cost recovery | **−0.148¢/kWh — a credit, not a charge** | Eversource NH Rate R | same | ✅ Aug 2026 |
| NH state/local accrual in the burden model | **$0 — excluded by design**, same rule as MA | Scope decision | — | ✅ Aug 2026 |

### 🚫 Why pension debt is excluded from the burden calculators

The burden dashboards count what a household **pays**. An unfunded pension liability
isn't billed to anyone — it's a claim on future tax capacity, and the portion collected
today arrives through the appropriation funded by the income and property taxes Layer 1
already counts. Counting it again in Layer 5 double-counts.

It also cannot be sourced symmetrically across the border, in two opposite directions:

| | Massachusetts | New Hampshire |
|---|---|---|
| OPEB (retiree health) | **included** in the $55.8B — $13.7B, only 15.6% funded | **not sourced** |
| Municipal systems | **mostly excluded** — the $42.1B is MTRS + SERS + Boston Teachers; PERAC tracks ~104 | **included** — NHRS is one statewide system |

Use **$42.1B MA vs $5.58B NH** for any pension-to-pension read, and carry the caveat.
The stocks are disclosed beside Layer 5 on both dashboards; the full story lives in
`pension-dashboard.html`.

**Removing it improved the analysis.** Layer 5 is now entirely federal and therefore
genuinely identical on both sides of the border, and the compression finding now holds at
$75k — the old asymmetric placeholders (MA $2,000 vs NH $1,600) had been manufacturing a
$400 NH advantage out of pure guesswork.

### ⚡ The Layer 4 inclusion rule

> A charge is a **policy cost** if it exists because of a legislative or regulatory
> mandate, rather than because of the physical cost of generating and delivering energy.

Excluded on both sides as infrastructure or mechanism: distribution, transmission,
revenue decoupling, regulatory reconciliation, stranded cost, customer charge.

Electricity is genuinely like-for-like — both figures are **Eversource**, the same
company on both sides of the border. Gas is not: Eversource doesn't serve NH gas, so
that side is Liberty EnergyNorth.

**Both figures are conservative in the same direction.** MA's is a **floor** — its own
tariff footnote places the Long Term Renewable Contract Adjustment (83C/83D offshore
wind), Solar Program Cost Adjustment and Grid Modernization *inside* the Distribution
charge, unbroken out, and RPS/CES sits inside supply. NH's gas figure is a **ceiling** —
the LDAC bundles mechanisms MA excludes. So the true gap is wider than stated.

**Headline finding: Massachusetts gas policy charges (59.08¢/therm) cost more than the
gas itself (38.42¢/therm).** The prior 18¢ placeholder understated it by over 3×.

Worth watching separately: **NH electricity rose 13.8% year over year while MA fell
3.6%.** Whatever advantage NH holds on the meter is closing fast.

### ⚠️ NH median property tax bill — sources disagree, carry all three

| Value | Effective rate | Source |
|---|---|---|
| $6,530 | 1.82% | Ownwell |
| $6,707 | 1.46% | SmartAsset |
| $5,680 | — | World Population Review (median across counties) |

The dashboard uses 1.71%, derived from the ~$17.10 per $1,000 statewide average total
rate, which is the cleanest of the four. **Note this is a rate on *assessed* value** —
NH DRA publishes equalization ratios precisely because assessed and market values
diverge, so applying it to a market price overstates the bill.

### The constants-consistency rule

`households × meanHouseholdIncome ÷ incomeShare` **must return the same national
aggregate for every state.** Before this was enforced, MA implied a $14.91T national
total and NH implied $17.50T — a 17.3% disagreement that made the "federal borrowing is
identical across the border" claim false by $2,674 on a line captioned *"Identical
basis"*. `update-burden-constants.py` now fails the build if this breaks.

---

## ⚡ Energy

Figures on `energy-dashboard.html`. Refreshed by `update-energy-dashboard.py` and `update-fuel-prices.py` on the 2nd and 26th, so the rate series carries the feed mark; the legislative analysis beside it does not and is dated to the document it reads.

| Figure | Source | Updated |
|--------|--------|---------|
| Residential Electricity Rates — MA vs. Selected States (¢/kWh) | EIA Electric Power Monthly Table 5.6.A, May 2026 | 🔄 May 2026 |
| MA Rate Premium Over National Average — Historical | EIA, annual residential average rates | 🔄 |
| MA Electricity Bill Breakdown (Typical Residential) | Eversource/National Grid rate schedules; DPU filings | — |
| MA vs. National Rate Gap Over Time | EIA Electric Power Monthly | 🔄 |
| Annual Impact Per Household | EIA May 2026, bill text analysis | May 2026 |
| Where the "Savings" Actually Come From | Bill sections analyzed against verified Eversource rate breakdown | — |
| State Comparison — Monthly Bill at 600 kWh | EIA May 2026 rates × 600 kWh/month | 🔄 May 2026 |
| The $14.3B Claim — Credibility Breakdown | S.3143 fact sheet (June 24, 2026); @DuncanBurnsMA analysis | June 2026 |
| Savings Claims by Category — $M Over 10 Years | S.3143 Senate fact sheet | — |
| Annual Per-Household Reality Check | EIA | 🔄 |
| What S.3143 Doesn't Touch — The Structural Cost Drivers | EIA; RGGI Inc.; DPU rate orders; ISO-NE. These policy-driven costs persist regardless of S.3143 passage | — |
| RGGI Carbon Tax — MA Auction Proceeds by Year ($M) | RGGI Inc | — |
| How RGGI Proceeds Are Spent (All RGGI States) | RGGI Proceeds Report 2023 | 2023 |
| What BCCE Actually Covers vs. Your Full Bill | Eversource rate schedules; BCCE program data; DPU filings | — |
| BCCE "Savings" vs. Mandate Premium — Annual $ | BCCE program ($200/yr avg); EIA rate data ($747/yr overpayment vs US avg at 600 kWh/mo) | — |
| Boston's Emissions by Sector (2023 Inventory) | Boston GHG Inventory 2023; 2030 Climate Action Plan, p.33 | 2023 |
| What $200/yr in BCCE Savings Looks Like Against the Full Mandate Stack | EIA rates; DPU filings; RGGI Inc.; Eversource/NGrid rate schedules; BCCE program data | — |

---

## 🏛️ Pensions

Figures on `pension-dashboard.html`. Maintained by hand against the actuarial reports and the Commonwealth’s own accounts; there is no feed behind it.

| Figure | Source | Updated |
|--------|--------|---------|
| Unfunded Liabilities by Category | Commonwealth ACFR FY2024; MBTA Audited Financials FY2024 | FY2024 |
| Funded Ratio by System | PERAC 2024 Actuarial Valuations; ACFR FY2024 | FY2024 |
| Employer Pension Cost as % of Payroll (SERS), 2001–2024 | Public Plans Database (publicplansdata.org), PPD ID 50 | — |
| Net State Deficit Trend (FY2015–2024) | Commonwealth ACFR FY2015–FY2024 | FY2015–FY2024 |
| SERS Funded Ratio vs. National Average, 2001–2024 | Public Plans Database (PPD ID 50) | — |
| SERS Net Assets Growth ($B), 2001–2024 | Public Plans Database | — |
| Actual Returns vs. Assumed Rate (SERS) | Public Plans Database; PRIT ACFR | — |
| Assumption Sensitivity: What If Returns Miss? | ACFR FY2024 sensitivity disclosures (illustrative) | FY2024 |
| PRIT Asset Allocation (FY2024) | Public Plans Database; PRIT ACFR FY2024 | FY2024 |
| Allocation Shift: 2001 → 2024 | PPD — note PE tripled from 5.6% to 17.0% | — |
| Annual Returns vs. 7% Target, 2001–2024 | Public Plans Database (PPD ID 50) | — |
| FY2024 Returns by Asset Class (Net) | PRIT ACFR FY2024/2025 | 2025 |
| Active Workers per Retiree (SERS vs. National), 2001–2024 | Public Plans Database — national averages weighted by plan size | — |
| Annual Net Cash Flow (SERS, $M) — Benefits Paid Minus Contributions | Public Plans Database — negative = paying out more than taking in | — |
| Municipal Systems by Funded Ratio Category | PERAC January 1, 2025 Funded Ratio List | January 2025 |
| Assumed Rate of Return Distribution | PERAC Jan 2025 — median ARR is 7.0% | 2025 |
| Statewide OPEB Summary | PERAC OPEB Summary (May 2024); ACFR FY2024 | FY2024 |
| State Retiree Benefits Trust Fund — Annual Deposit ($M) | enacted General Appropriations Acts FY2024–FY2027, line 1595-6152, via the official mass.gov GAA export ( | FY2024–FY2027 |
| Net Deficit Trajectory (FY2015–2024) | Commonwealth ACFR FY2015–FY2024 | FY2015–FY2024 |
| Pension Funded Ratios — MA vs. Selected States | Public Plans Database; individual state ACFRs | — |
| MA SERS vs. National Avg, 2001–2024 | Public Plans Database | — |

---

## 💵 Lobbying & Political Spending

Figures on `pay-to-play-dashboard.html`. Two authorities: OpenSecrets for sector and firm totals, and the state’s own OCPF database for individual donations. Maintained by hand.

| Figure | Source | Updated |
|--------|--------|---------|
| Lobbying Spending by Sector — $457M Total (2015–2025) | OpenSecrets, Massachusetts State Lobbying Ranked Sectors (2015–2025) | 2015–2025 |
| Top 10 Industries by Lobbying Spend (2015–2025) | OpenSecrets, Massachusetts State Lobbying by Industry (2015–2025) | 2015–2025 |
| 2024 Top Lobbying Spenders — Single Year | Secretary of the Commonwealth, MA Lobbying Reports (2024) | 2024 |
| Healthcare vs. All Other Sectors (2015–2025) | OpenSecrets, Ranked Sectors Massachusetts (2015–2025) | 2015–2025 |
| Firm Lobbying Income (2015–2025) — Top 10 | OpenSecrets, Top 20 Lobbying Firms, Massachusetts (2015–2025) | 2015–2025 |
| The $200 Pattern — Donation Amount Distribution (OCPF) | OCPF Campaign Finance Database — ML Strategies, Smith Costello, Bay State Strategies donations | — |
| Donations by Firm — OCPF Analysis | OCPF — 4,298 total donations analyzed | — |
| Top 10 Individual Lobbyist Donors | OCPF Campaign Finance Database | — |
| Top 15 Recipients of Lobbyist Firm Donations (OCPF) | OCPF — combined donations from ML Strategies, Smith Costello, Bay State Strategies employees | — |
| Donations by Source Firm — Top Recipients | OCPF Campaign Finance Database | — |
| Healthcare Case Study: MGB VP Christopher Philbin | OCPF — Philbin donation records (2024) | 2024 |
| Healthcare Industry — Political Giving from Employees (2024) | OCPF Campaign Finance Database, employer field analysis (2024) | 2024 |

---

## 🏙️ Boston

Figures on `all-things-boston.html`. The page states its sources in prose rather than under each chart, so the authorities are listed here and the page itself carries the detail. Maintained by hand.

| Figure | Source | Updated |
|--------|--------|---------|
| Department expenditure, budgeted vs actual | City of Boston ACFR, Schedule of Expenditures Compared to Budget (budgetary basis) | FY2020–FY2025 |
| Employee payroll | City of Boston Employee Earnings Reports, data.boston.gov | CY2019–CY2025 |
| Crime | FBI and Boston Police Department figures | — |
| Schools | Massachusetts DESE School & District Profiles | — |
| Immigration enforcement | ICE ERO Boston, with UC Berkeley, the Globe and GBH reporting | — |
| 311 service requests | data.boston.gov | — |
| Assessed property values | City of Boston Assessing Department | — |

---
## 🔗 Dashboard Registry

All dashboards live at `https://massachusettsdatahub.com/<file>`.
Cadences below are the cron lines in `.github/workflows`, and the refresh column
names the script that actually writes each page.

| Dashboard | File | Auto-refreshed by | Cadence |
|-----------|------|-------------------|---------|
| Immigration (National + MA) | `immigration-dashboard.html` | `update-cbp-encounters.py`, `update-census-data.py` | 25th, 20th |
| MA Housing Market | `ma-housing-dashboard.html` | `update-mls-figures.py` | daily, 07:00 UTC |
| NH Housing Market | `nh-housing-dashboard.html` | `update-nh-figures.py` &rarr; `data/nh-figures.json` | daily, 07:20 UTC |
| Haverhill Market Report | `haverhill-market-report.html` | `update-mls-figures.py` | daily, 07:00 UTC |
| Master Affordability | `affordability-dashboard.html` | `update-cost-of-living.py`, `update-census-data.py` | 20th |
| Employment | `employment-dashboard.html` | `scripts/fetch-bls-data.js` | the Friday in the 1st&ndash;7th and 15th&ndash;21st windows |
| Energy | `energy-dashboard.html` | `update-energy-dashboard.py`, `update-fuel-prices.py` | 2nd and 26th |
| Tax & Budget | `tax-budget-dashboard.html` | `update-irs-soi-migration.py`, `update-tax-budget-dashboard.py` | 1st, 26th |
| The Five Layers (MA & NH) | `tax-burden-dashboard.html` | `update-burden-constants.py` | run by hand |
| All Things Boston | `all-things-boston.html` | &mdash; | manual |
| MA Education (Statewide) | `education-statewide.html` | &mdash; | manual |
| Merrimack Valley Education | `education-merrimack-valley.html` | &mdash; | manual |
| Healthcare Insurance | `healthcare-dashboard.html` | &mdash; | manual |
| Commercial RE | `commercial-re-dashboard.html` | &mdash; | manual |
| Pension | `pension-dashboard.html` | &mdash; | manual |
| Pay to Play | `pay-to-play-dashboard.html` | &mdash; | manual |

Consumer-price figures refresh on the 10th&ndash;16th (`update-cpi.yml`) and feed the
affordability and energy pages rather than a page of their own. The site itself
redeploys every three hours, and after every one of these runs.

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
| 2026-08-11 | **FY2027 enacted-budget review against the official mass.gov GAA exports.** Diffed all 860 `LINE_ITEMS` in `tax-budget-dashboard.html` against `gaa1.xlsx`: **zero amount mismatches** — the H.5555 conference data the dashboard was built on *is* the enacted law, because Healey signed with no vetoes. Fixed one account-code typo (`8910-0702` → `8910-8702`). Relabelled the tab, headings, sources and the `FY27_H5555` constant (now `FY27_GAA = 63.416`) from "conference report" to enacted GAA, and replaced the stale "heads to Gov. Healey's desk" line. Added the **scope reconciliation table** above — the headline total excludes Intragovernmental Service Spending — plus FY2027 key figures, the enacted-vs-actual supplemental gap (new `h5Outturn` chart), and the local-aid CSV footer-row gotcha. Added the OPEB finding to `pension-dashboard.html`: the SRBT deposit (line 1595-6152) is down 27% since FY24 while the budget creates a pension COLA reserve. Cleared both long-standing defects — CPS/ACS mislabel and the unlabelled $7,732 property tax figure (now $8,113, FY2026). | Claude + Duncan |
| 2026-02-05 | Initial creation — all data compiled from prior chats | Claude + Duncan |
| 2026-08-01 | Refreshed the manual dashboards. Commercial RE → Q2 2026 (C&W Boston 19.0%, US 20.1%; Colliers 23.7%; CBRE 18.7%; Trepp office delinquency 11.57%). Tax & Budget verified already current (FY2027 H.5555 enacted $63.4B, signed 2026-07-09, parsed July 2026). Healthcare held at the 2024 MA/US pair with KFF's 2025 national figure ($26,993) noted, since no MA 2025 comparator is published. Made the CPI badge and immigration hero self-stamping so they can't go stale again. | Claude + Duncan |
| 2026-08-01 | Repo audit. Reconciled this file against the live API feeds it had drifted from: ACS figures → vintage 2024, MA median income $104,800 → $103,960, MLS 5-yr table → `mls-history.json` values, NH → PrimeMLS 2026-08-01, IRS cumulative 86,382/$12.1B → 184,719/$24.7B (matching the live dashboard). Split the trailing-12-month window out from calendar 2025, recorded the CBP FY2025 methodology break and the BLS state-JOLTS discontinuation, corrected the dashboard registry. Marked API-fed rows 🔄. | Claude + Duncan |

---

*To update: Edit this file directly on GitHub, or tell Claude "update MASTER_DATA.md with [new figures]"*
