# Massachusetts Data Hub — Master Data Reference

> **Last Updated:** July 31, 2026
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
| 2026 | $865,771 | $903,059 | $1,312,961 | $1,255,442 |

- **5-Year Growth:** MA +29.2%, Newburyport +41.1%, Boston +22.6%
- **Note:** These are AVERAGES (skewed by luxury); Warren Group MEDIANS used for affordability analysis

### Massachusetts — Market Indicators (2025)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Avg DOM | 37 days | MLS PIN | ✅ Feb 2026 |
| SP/LP Ratio | 101.01% | MLS PIN | ✅ Feb 2026 |
| Units Sold | 42,273 | MLS PIN | ✅ Feb 2026 |
| Units Sold YoY | +1.5% | MLS PIN | ✅ Feb 2026 |

### Haverhill Specific

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Median household income | $88,326 | Census QuickFacts ACS 2020-2024 | ✅ Feb 2026 |
| MA median household income | $104,800 | ACS 2020-2024 | ✅ Feb 2026 |
| Condo median (Haverhill) | $392,500 | MLS | ✅ Feb 2026 |
| SF median (Haverhill) | $605,000 | MLS | ✅ Feb 2026 |
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

## ⚠️ Policy Registry — Ranked Inventory

Full detail and charts: [`worst-policies-dashboard.html`](worst-policies-dashboard.html). Ranked by documented cost to residents and taxpayers.

| # | Policy | Citation | Documented cost | Source repo |
|---|--------|----------|-----------------|-------------|
| 1 | Net-zero mandate stack (GWSA + Climate Roadmap) | Ch. 298/2008 (c. 21N); St. 2021 c. 8 | $130B–$400B+ economy-wide; ~$377/yr per household | Data Hub · Mass-Fiscal-Energy-Legislation |
| 2 | Offshore wind "full cost recovery" | Ch. 169/2008 §83C, amd. St. 2016 c. 188 §12 | ~4% of every bill, uncapped; 2.75% utility remuneration | Data Hub · ma-electricity-analysis |
| 3 | Pension + OPEB underfunding | PERAC 2024; ACFR FY2024 | $107.6B liabilities; $4.9B/yr (~8% of budget) | Data Hub · Massachusetts-Disaster |
| 4 | Emergency Assistance shelter administration | Right-to-shelter as administered pre-2025 | $856M–$978M FY24; $1.06B FY25; $3,496–$3,870/family/wk | Data Hub · The-Invasion · fraud-detection |
| 5 | Records exemption + refused audit | Ballot Q1 2024 (71.8% yes) | Not dollar-denominated | Data Hub · The-Peoples-Audit |
| 6 | MBTA Communities Act § 3A | M.G.L. c. 40A §3A | ~$4.49B fees vs. $15M appropriated (99.7% unfunded) | MBTA-Communities-Act |
| 7 | RGGI cap-and-trade | M.G.L. c. 21N §§1–9 | $1.36B since 2008; $200.4M in 2025; ~15% returned | Data Hub |
| 8 | Fair Share surtax + Ch. 70 supplanting | Art. XLIV (2022, 51%) | ~$3.0B/yr; $496M Ch. 70 shifted | Data Hub · MA-2027-Budget-Analysis |
| 9 | MBTA structural finance / Big Dig debt | Forward Funding, 2000 | ~$1.1B/yr = $412 per household | MBTA-Scam |
| 10 | Lawmaker-nonprofit loophole | MGL Ch. 55 §7A | $104M/yr lobbying; $457M 2015–2025 | Data Hub · HHS-MA-DOGE |
| 11 | MCAS graduation requirement repeal | Ballot Q2, Nov 2024 | Universal Grade 10 decline, 2025 | Data Hub · MA-v-NH |
| 12 | "Protecting Ratepayers" storage mandate | St. 2024 c. 239 §83E | 5,000 MW with guaranteed pass-through | Data Hub |
| 13 | H.5151 / H.5175 | 194th Session, 2026 | "$9B" = $310/yr claimed; ~$150/yr realistic | Mass-Fiscal-Energy-Legislation |
| 14 | Pipeline capacity opposition | Executive policy, no statute | Supply is ~40% of the bill | Data Hub |
| 15 | $25,000 homebuyer subsidy | MassHousing DPA (deferred 2nd mortgage) | Gateway bottom tier +74% vs. top +57% | The-25K-Problem |
| 16 | Property tax growth under Prop 2½ | M.G.L. c. 59 §21C | $24.0B levy FY2026, +$1.2B YoY; MA #48 | Data Hub · CoH |
| 17 | Third-party competitive supply protected | Ban bills blocked in committee | $525M excess consumer cost 2015–2021 (MA AG) | ma-electricity-analysis |
| 18 | UI tax + separate non-UI payroll tax | M.G.L. c. 151A + PFML | MA #45 on UI tax — *ranking only, no underlying analysis* | Data Hub |
| 19 | Estate tax at $1M threshold | M.G.L. c. 65C | 86,382 returns / $12.1B AGI cumulative outflow | Data Hub |
| 20 | Benefits fraud detection capacity | State Auditor BSI | ~$11–13M detected vs. ~$50M modeled (SNAP) | fraud-detection |
| 21 | Health rate approvals vs. own benchmark | MA DOI rate review | 7.1%–12.2% approved vs. 3.6% benchmark | Data Hub · MA-Health-Insurance |
| 22 | Chapter 40B as primary supply tool | M.G.L. c. 40B §§20–23 | ~70K units in 50+ yrs vs. 222,000-unit deficit | MA-Housing-Affordability-Issues |
| 23 | H-1B wage levels as applied in MA | Federal prevailing-wage tiers | 18.9% of MA positions at 36% below median | H1B |
| 24 | Boston equity apparatus vs. service delivery | City of Boston ACFR | $548K → $28.5M (52×); BPD −177 officers | All-Things-Boston |
| 25 | Healthcare regulatory capture | SOC lobbyist registrations | $39M hospital lobbying 2020–2025 | Pay-To-Play-MA-Non-Profits |

### ⚠️ Known Cross-Repo Conflicts — Unreconciled

Treat these as ranges, not point estimates. Resolve here first, then propagate to dashboards.

| Figure | Competing values | Where |
|--------|-----------------|-------|
| FY2024 shelter spending | $856M / $894M / $932M / $978M | The-Invasion / immigration-dashboard / MA-v-NH / this file |
| Cost per shelter family per week | $3,496 / $3,870 / ~$10,000/mo | this file / fraud-detection / Massachusetts-Disaster |
| MA electricity premium over US avg | +56% (Apr 2026) / +74% (Nov 2024) / +79% (Dec 2025) / +57% | energy-dashboard / ma-electricity-analysis / Mass-Fiscal-Energy-Legislation / Maura-Healey-Year-3- |
| Industrial rate premium | +112% (EIA Oct 2025) / +134% | energy-dashboard / affordability-dashboard |
| Unfunded OPEB | $13.7B (Commonwealth) / $15.77B (+MBTA) / $52.8B (all entities) | All correct for different scopes — labels don't always say which |
| Total state liabilities | $107.6B (ACFR FY2024) / $122.5B | pension-dashboard / Maura-Healey-Year-3- (Dec 2025 vintage) |
| Unfunded pension total | $42.07B / $42.1B / $42.76B (incl. Boston + MBTA) | Massachusetts-Disaster / pension-dashboard |

### 📭 Coverage Gaps

No repository in the network currently analyzes: **rent control** (neither the 1994 statewide ban nor current proposals to lift it), **permitting timelines**, **Article 80** in Boston, or the **UI trust fund structure**. Given the 222,000-unit deficit identified as the core housing problem, rent control sits directly on the critical path and is unexamined.

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
| **Worst Policies (ranked)** | `worst-policies-dashboard.html` | Live | Active |

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
| 2026-07-31 | Added Policy Registry (25 ranked entries), cross-repo conflict table, and coverage gaps; synthesized from 29 research repositories | Claude + Duncan |

---

*To update: Edit this file directly on GitHub, or tell Claude "update MASTER_DATA.md with [new figures]"*
