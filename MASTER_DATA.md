# Massachusetts Data Hub — Master Data Reference

> **Last Updated:** August 08, 2026
> **Maintainer:** Duncan Burns
> **Purpose:** Single source of truth for all verified data points used across dashboards

---

## 📋 How to Use This File

When starting a new Claude chat, say:
> "See MASTER_DATA.md in my Massachusetts-Data-Hub repo for all verified figures."

Every entry includes: **figure → source → source URL → date verified → which dashboard uses it**

When a figure is updated, change it here FIRST, then update the relevant dashboard.

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
| FY2025 (thru Jan) | 237,538 | CBP | ✅ Feb 2026 |

- **FY2025 pace:** Lowest since 1970
- **FY2021-24 total:** ~10.8M nationwide encounters
- **Source URL:** https://www.cbp.gov/newsroom/stats/southwest-land-border-encounters

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

| City | Foreign-Born % | Source | Verified |
|------|---------------|--------|----------|
| Chelsea | 44% | ACS | ✅ Feb 2026 |
| Lawrence | ~40% | ACS | ✅ Feb 2026 |
| Revere | ~38% | ACS | ✅ Feb 2026 |
| Methuen | 23% | ACS | ✅ Feb 2026 |

- **60-mile radius of Beacon Hill** — inner-ring cities bearing disproportionate burden
- **Lawrence multilingual population:** 78.5%
- **Chelsea multilingual population:** 70.4%

### Massachusetts — Population & Migration

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| IRS returns lost (cumulative) | 86,382 | IRS SOI | ✅ Jan 2026 |
| AGI lost (cumulative) | $12.1B | IRS SOI | ✅ Jan 2026 |
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

| Year | MA Statewide | Essex County | Boston | Newburyport |
|------|-------------|--------------|--------|-------------|
| 2021 | $664,120 | $715,539 | $1,080,332 | $940,514 |
| 2022 | $723,395 | $771,458 | $1,068,618 | $1,075,891 |
| 2023 | $758,182 | $819,125 | $1,081,007 | $1,122,737 |
| 2024 | $812,972 | $874,817 | $1,140,443 | $1,218,706 |
| 2025 | $858,122 | $899,712 | $1,324,123 | $1,327,602 |
| 2026 | $864,918 | $905,278 | $1,307,971 | $1,246,719 |

- **5-Year Growth:** MA +29.2%, Newburyport +41.1%, Boston +22.6%
- **Note:** These are AVERAGES (skewed by luxury); Warren Group MEDIANS used for affordability analysis

### Massachusetts — Market Indicators (2025)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Avg DOM | 38 days | MLS PIN | ✅ Feb 2026 |
| SP/LP Ratio | 100.92% | MLS PIN | ✅ Feb 2026 |
| Units Sold | 39,225 | MLS PIN | ✅ Feb 2026 |
| Units Sold YoY | +1.5% | MLS PIN | ✅ Feb 2026 |

### Haverhill Specific

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Median household income | $88,326 | Census QuickFacts ACS 2020-2024 | ✅ Feb 2026 |
| MA median household income | $104,800 | ACS 2020-2024 | ✅ Feb 2026 |
| Condo median (Haverhill) | $390,000 | MLS | ✅ Feb 2026 |
| SF median (Haverhill) | $605,250 | MLS | ✅ Feb 2026 |
| Income needed for condo | ~$86K | Calc: 6.5%, 20% down, 28% DTI | ✅ Feb 2026 |
| Income needed for SF | ~$124K | Calc: 6.5%, 20% down, 28% DTI | ✅ Feb 2026 |

### New Hampshire — Market Data (Paragon MLS, Jan 2026)

| Region | Median Price | Avg Sale | Avg DOM | SP/LP |
|--------|-------------|----------|---------|-------|
| NH Statewide | $438,000 | $530,781 | 29 days | 100.24% |

### Boston — Commercial Real Estate (CMBS)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Office vacancy (C&W) | 18.2% | Cushman & Wakefield Q4 2025 | ✅ Feb 2026 |
| Office vacancy (Colliers) | 23.9% | Colliers Q4 2025 | ✅ Feb 2026 |
| Pre-COVID vacancy | ~7.5% | Multiple sources | ✅ Feb 2026 |
| Major sale discounts (2025) | 31–62% losses | Boston Globe / CommercialEdge | ✅ Feb 2026 |
| Boston property tax dependence | ~73% of $4.8B budget | Boston.gov | ✅ Feb 2026 |
| National avg office value decline | ~37% | Green Street | ✅ Feb 2026 |

---

## 💼 Employment & Labor

### Massachusetts — JOLTS

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Job openings rate (peak) | ~5.5% | BLS JOLTS | ✅ Feb 2026 |
| Job openings rate (current) | ~4.2% | BLS JOLTS | ✅ Feb 2026 |
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
| MA electric policy charges | 4.0¢/kWh — **placeholder** | DPU tariffs (EE, RE, NMRS, SMART, 83C/83D) | mass.gov/orgs/department-of-public-utilities | ⚠️ Unverified |
| MA gas policy charges | 18¢/therm — **placeholder** | DPU tariff (EE surcharge, GSEP) | same | ⚠️ Unverified |
| MA state/local unfunded annual accrual | $2,000/household — **placeholder** | PERAC; ACFRs | See pension-dashboard.html | ⚠️ Unverified |

### ⚠️ The two MA median-income figures — do not merge them

| Vintage | Value | Concept | Use |
|---|---|---|---|
| Census **CPS ASEC** via FRED `MEHOINUSMAA646N` | **$113,900** | Median household income 2024 | Context / presets |
| Census **ACS 1-year** B19013 | **$104,828** | Median household income 2024 | Context / presets |
| Census **ACS 1-year** B19025 ÷ B11001 | **$144,312** | *Mean* household income | **Allocation divisor** |

CPS and ACS disagree by ~$9K on the same concept. Carry both and cite which one any
given chart uses — this is exactly the kind of thing a hostile reader finds first.

**Known defect to fix:** `tax-budget-dashboard.html` (lines ~517 and ~564) labels
$113,900 as "Census 2024 ACS". That is wrong — $113,900 is the **CPS** figure; ACS says
$104,828. Also line ~184 of that file states property taxes average "$7,732/year" with
no fiscal year label, against the FY2026 DLS figure of $8,113.

**Never use a median as an allocation divisor.** Per-household shares must sum back to
the statewide pool, which only works with the mean. The reconciliation panel on the
burden dashboard checks this.

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
| NH electric policy charges | 1.0¢/kWh — **placeholder** | NH PUC tariffs (SBC, stranded cost) | puc.nh.gov/regulatory/tariffs.html | ⚠️ Unverified |
| NH gas policy charges | 4¢/therm — **placeholder** | NH PUC gas tariffs | same | ⚠️ Unverified |
| NHRS unfunded annual accrual | $1,600/household — **placeholder** | NHRS actuarial valuation | nhrs.org/about-nhrs/financial-reports | ⚠️ Unverified |

### ⚠️ The Layer 4 sanity bound — a component can't exceed the whole

The MA and NH **policy-charge** placeholders (4.0¢ vs 1.0¢/kWh) imply a 3.0¢ gap. EIA
puts the **all-in** residential price gap at just **1.49¢** (28.82¢ vs 27.33¢). For both
to hold, New Hampshire would have to be dearer than Massachusetts on generation,
transmission and distribution *combined* by 1.51¢. Possible, but it's a strong claim to
arrive at by accident — the placeholders almost certainly overstate NH's Layer 4
advantage. `update-burden-constants.py` now warns on this automatically.

Worth watching regardless: **NH electricity rose 13.8% year over year while MA fell
3.6%.** Whatever advantage NH has on the meter is closing fast.

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

## 🔗 Dashboard Registry

| Dashboard | Repo / Path | Live URL | Status |
|-----------|------------|----------|--------|
| Immigration (National + MA) | `/immigration/index.html` | TBD (migrate) | Active |
| MA Housing Market | `/housing/ma-dashboard.html` | TBD (migrate) | Active |
| NH Housing Market | `/housing/nh-dashboard.html` | TBD (migrate) | Active |
| Haverhill Market Report | `/housing/haverhill-report.html` | TBD (migrate) | Active |
| Master Affordability | `/affordability/dashboard.html` | TBD (migrate) | Active |
| MA Education (Statewide) | `/education/index.html` | TBD (migrate) | Active |
| Boston Education | `/education/boston-dashboard.html` | TBD (migrate) | Active |
| Merrimack Valley Education | `/education/merrimack-valley.html` | TBD (migrate) | Active |
| Healthcare Insurance | `/healthcare/index.html` | TBD (migrate) | Planned |

### Current Live URLs (old repos — migrate over time)

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

---

*To update: Edit this file directly on GitHub, or tell Claude "update MASTER_DATA.md with [new figures]"*
