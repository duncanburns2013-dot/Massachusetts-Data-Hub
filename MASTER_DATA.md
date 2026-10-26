# Massachusetts Data Hub — Master Data Reference

> **Last Reviewed:** September 26, 2026
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
| FY2017 | 415,517 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2018 | 521,090 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2019 | 977,509 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2020 | 458,088 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2021 | 1,734,686 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2022 | 2,378,944 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2023 | 2,475,669 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
| FY2024 | 2,136,800 | CBP | 🔒 closed federal fiscal year. These are OHSS total encounters (Border Patrol plus ports of entry); OHSS stopped publishing the ports-of-entry component after FY2024, so this series is complete and cannot be extended or revised. The Border Patrol-only series that does continue is written by update-cbp-encounters.py. |
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
| 2020 | 19,892 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| 2021 | 376,026 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| 2022 | 1,672,112 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| 2023 | 2,264,137 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| 2024 | 2,734,468 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| 2025 | 1,262,202 | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |

Read from `NST-EST2025-ALLDATA.csv`, United States row, `INTERNATIONALMIG2020`
through `INTERNATIONALMIG2025`, retrieved 2026-10-04 — the same file and URL
template `update-domestic-migration.py` already uses.

**Every row of this table used to disagree with the vintage it named.** It read
818,000 / 1,041,000 / 2,020,000 / 2,358,000 / 2,384,000 / 321,000 for 2020–25,
plus a 2019 row that Vintage 2025 cannot supply at all, since the series begins
at 2020. The issues audit of 2026-10-04 flagged two of those rows; checking the
file showed all of them were wrong.

Those figures were not invented — they look like an earlier vintage, and 321,000
appears elsewhere in this project as a Federal Reserve Bank of San Francisco
estimate on a different basis. That is what made it survive: a real number under
the wrong source label reads as plausible on every line, which is harder to
catch than a typo. **Do not mix vintages in one table.** Census revises this
series heavily — 2024 moved from 2,384,000 to 2,734,468, a 15% revision, in one
vintage step.

- **Census methodology revision (Dec 2024):** 69–102% undercount in prior estimates
- **2022-24 revised total:** +6.8M (revised upward)
- **Source URL:** https://www.census.gov/programs-surveys/popest.html

### National — Deportation Math

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Entered (FY2021-24) | ~8M | CBP + Census | ⏳ re-read by 2027-01-31 — CBP plus Census, re-derive |
| Interior removals (Biden admin) | ~600K (~150K/yr) | ICE ERO | ⏳ re-read by 2027-01-31 — ICE ERO annual report |
| Net remaining | ~7.4M | Calculated | ⏳ re-read by 2027-01-31 — derived from the two rows above |

### National — Fiscal Impact

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Cato/NASEM cumulative surplus (1994-2023) | $14.5T | Cato White Paper 2025 | 🔒 a published study's finding. Cato White Paper 2025, fixed text. |
| College grad share of surplus | $11.7T (81%) | Cato/NASEM | 🔒 same study, fixed text. |
| Non-college grad share | $2.8T (19%) | Cato/NASEM | 🔒 same study, fixed text. |
| Noncitizen share of surplus | $6.3T | Cato/NASEM | 🔒 same study, fixed text. |
| CBO state/local net cost (2023) | $9.2B | CBO June 2025 | 🔒 CBO June 2025 report, a published document. |
| Undocumented tax contributions (national) | $96.7B | ITEP 2024 | 🔒 ITEP 2024 report, a published document. |
| Incarceration rate vs natives | 44% less likely | Cato/NASEM | 🔒 same study, fixed text. |

- **Key finding:** Legal immigrants net positive at all levels; undocumented net negative at state/local
- **Cato caveat:** Paper does NOT separate legal from illegal; counts US-born children as "US-born"

### Massachusetts — Immigration Costs

| Category | Annual Cost | Source | Verified |
|----------|------------|--------|----------|
| Total annual immigration cost | ~$2.35B | Multiple state sources | ⏳ re-read by 2027-01-31 — a compilation of several state sources; re-derive from each |
| Illegal-only cost estimate | $800M–$1.5B | CIS/FAIR/state data | ⏳ re-read by 2027-01-31 — an estimate range from advocacy sources on both sides; re-derive |
| Undocumented tax contributions (MA) | ~$1.4B total ($446M state/local) | ITEP | 🔒 ITEP, a published document. |
| Immigrant-vendor payments file (28 vendors, 8,883 payments) | $228.6M total; **$46.8M (20.5%)** identifiable immigrant/refugee or shelter programs | Computed from `data/payments.json` (tiers 0+1) | ⏳ re-read by 2027-01-31 — superseded in substance by shelter-immigrant-spending.html, which classifies by appropriation; this row describes the older vendor-name file and should be retired or restated |

### Massachusetts — Shelter Crisis

> **Two definitions, one source. Label every figure with the one it uses.**
> **Shelter system** = CTHRU (Comptroller budget-vs-actual, Socrata `kv7m-35wn`, field
> `total_expenses`) summed over EA shelter 7004-0101, HomeBASE 7004-0108, shelter workforce
> 7004-0109, family shelter diversion 7004-0110 (new FY27), and the shelter and immigrant
> reserves 1599-0514, 1599-1213, 1599-2625, 1599-0122, 1599-0925. **EA line** = 7004-0101 alone.
> Neither includes trust fund 7004-4778, which CTHRU budget-vs-actual does not carry.
> Query: https://cthru.data.socrata.com/resource/kv7m-35wn.json (rows updated 2026-09-30).

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Shelter system, FY2022 actual | $228.53M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY2023 actual | $343.55M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY2024 actual | $803.74M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY2025 actual | $1,042.45M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY2026 actual | $360.92M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY2027 to date | $93.40M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY24 + FY25 | $1.85B ($1,846.18M, derived) | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY22–FY25 | $2.42B ($2,418.26M, derived) | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| Shelter system, FY22–FY26 | $2.78B ($2,779.18M, derived) | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| EA line 7004-0101, actual | FY22 $202.56M · FY23 $274.38M · FY24 $643.25M · FY25 $326.07M · FY26 $259.54M · FY27 YTD $49.44M | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| HomeBASE 7004-0108, actual | FY22 $25.97M · FY23 $49.41M · FY24 $37.22M · FY25 $57.32M · FY26 $57.29M · FY27 YTD $43.47M — CTHRU transfer_in into 7004-0108 is $2,575 in FY2026, not a material top-up | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| HomeBASE growth, FY22 → FY26 | +121% (derived, $25.97M → $57.29M) | CTHRU kv7m-35wn | 🔄 written by `update-immigrant-spending.py` |
| EOHLC all-in FY2026 (shelter $286.8M + exits incl. HomeBASE $153.7M) | $440.5M, incl. $83.0M from trust fund 7004-4778 not in CTHRU | A&F/EOHLC biweekly EA report, 8 Sep 2026 (SD.4220) | ⏳ re-read by 2027-01-31 — the next EOHLC all-in report |
| FY2026 **projected** — budget documents, NOT a CTHRU actual | EA 7004-0101 $276,421,903 · HomeBASE $91,386,678. **Do not publish either as spending.** CTHRU actuals for FY2026 are EA $259.54M and HomeBASE $57.29M; see the rows above, which a script writes. The HomeBASE projection exceeds its $57,322,001 appropriation by $34,064,677, and that difference was once published as a transfer into the account. CTHRU's `transfer_in` for 7004-0108 in FY2026 is $2,575. | budget.digital.mass.gov FY27 line-item data | 🔒 the FY27 budget documents' FY2026 projected column. A published document for a year that has since closed. Kept, clearly labelled, because mistaking this projection for a CTHRU actual is exactly what produced the wrong HomeBASE figure. |
| FY2027 GAA | EA 7004-0101 $259,900,648 · HomeBASE 7004-0108 $82,322,001 · 7004-0110 $5,000,000 | budget.digital.mass.gov FY27 line-item data | ⏳ re-read by 2027-07-31 — the FY2028 budget documents, when the FY2027 column becomes final |
| EA caseload, 1 Oct 2026 | 1,536 families in shelter + 47 in clinical safety sites | Biweekly EA report to House and Senate Ways and Means, 5 Oct 2026 (SD.4288), malegislature.gov/Bills/194/SD4288.pdf | ⏳ re-read by 2026-12-31 — the newest biweekly EA report |
| EA caseload, 25 Jul 2024 | 7,367 families in shelters, hotels or motels (Appendix A total) + 340 in overflow | Biweekly EA report, 29 Jul 2024 (SD.3359), malegislature.gov/Bills/193/SD3359.pdf | 🔒 a dated snapshot from the biweekly EA report SD.3359. The report for that date will not be reissued. |
| Caseload change, Jul 2024 to Oct 2026 | -79% (7,367 to 1,536, derived) | SD.3359, SD.4288 | ⏳ re-read by 2026-12-31 — derived from the two caseload rows |
| Cost per family per week, current | $1,241 (average shelter provider rates, FY27 contracts) | EA report SD.4288 | ⏳ re-read by 2026-12-31 — the next biweekly EA report |
| Cost per family per week | $3,496 | State Auditor | ⏳ re-read by 2027-02-28 — the State Auditor's next shelter review |
| $100K fee per shelter family | Proposed | Legislature | 🔒 a filed legislative proposal, not a measurement. |

- **HomeBASE spending is reported.** The 8 Sep 2026 EA report carries FY26 "exits" spending ($153.7M), a category that includes HomeBASE; CTHRU carries 7004-0108.
- **No official migrant share of EA families is published** (checked Sep 2026). Do not apply one.
- **The immigration dashboard's $1.88B FY25 estimate** = emergency shelter $1.06B + wraparound $150M + modelled CIS K-12 $575M + healthcare $95M. Its shelter part covers every family in emergency shelter, so it is not a count of people here unlawfully. CTHRU's FY25 shelter-system actual is $1.04B, not $1.06B.

### Massachusetts — H-1B Workers

| Year | H-1B Workers (MA) | Source | Verified |
|------|--------------------|--------|----------|
| Peak | 21,834 | USCIS | ⏳ re-read by 2027-01-31 — USCIS parole and humanitarian data |
| Current | ~7,550 | USCIS | ⏳ re-read by 2027-01-31 — USCIS parole and humanitarian data |

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
| Net outflow, latest year (2022-23) | 16,921 returns — **includes moves abroad** | IRS SOI | 🔄 Aug 2026 |

The 16,921 is outflow 102,076 against inflow 85,155 (returns, 2022-23; data/irs-soi-migration-latest.json), and both totals include the foreign category. It is therefore NOT comparable with a domestic-only net migration count, which is a smaller number. Say which one a card means before putting the two near each other.

| Metric | Figure | Source | Verified |
|--------|--------|--------|----------|
| Net domestic out-migration, 2020-2025 | 182,145 people | US Census Bureau, Population Estimates (NST-EST2025 components of change) | 🔄 Sep 2026 |
| Net international migration, 2020-2025 | +286,765 people (2024-25: +40,240; 2023-24: +77,957) | US Census Bureau, Population Estimates (NST-EST2025 components of change) | 🔄 Oct 2026 |
| Net migration, domestic plus international, 2020-2025 | +104,620 people | US Census Bureau, Population Estimates (NST-EST2025 components of change) | 🔄 Oct 2026 |
| Natural change (births less deaths), 2020-2025 | +26,617 people | US Census Bureau, Population Estimates (NST-EST2025 components of change) | 🔄 Oct 2026 |
| Population change, 2020-2025 | +120,972 people (2024-25: +15,524; July 2025 population 7,154,084) | US Census Bureau, Population Estimates (NST-EST2025 components of change) | 🔄 Oct 2026 |
| Net AGI loss, latest year (2022-23) | $4.18B | IRS SOI | 🔄 Aug 2026 |
| Average AGI per return, leaving vs arriving (2022-23) | $116,360 leaving (11,877,573K / 102,076) vs $90,442 arriving (7,701,622K / 85,155) | IRS SOI State-to-State Migration Data, data/irs-soi-migration-latest.json | 🔄 Oct 2026 |
| 2024 US growth from immigration | 84% | Census | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |
| MA NIM "nosedive" (2025 proj) | Historic decline | Census Vintage 2025 | ⏳ re-read by 2026-12-31 — Census Vintage 2026, due December |

---

## 🏠 Housing & Real Estate

### Massachusetts — Median Prices (Warren Group)

| Region | Median Price | YoY Change | Source | Verified |
|--------|-------------|------------|--------|----------|
| Massachusetts | $638,000 | +3.7% | Warren Group | ⏳ re-read by 2027-06-30 — the publisher's next release |
| Greater Boston | $800,000 | +4.2% | Warren Group | ⏳ re-read by 2027-06-30 — the publisher's next release |
| Essex County | $699,000 | +5.1% | Warren Group | ⏳ re-read by 2027-06-30 — the publisher's next release |

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
| 2026 | $865,395 | $903,325 | $1,352,271 | $1,280,829 |

- **5-Year Growth (2021→2025):** MA +28.8%, Newburyport +40.8%, Essex +25.6%, Boston +19.6%
- **Note:** These are AVERAGES (skewed by luxury); Warren Group MEDIANS used for affordability analysis

#### Live trailing-12-month window (changes daily — do not transcribe)

The dashboards' last column is **not calendar 2026** — it is a rolling trailing-12-month
window rewritten every day. As of **October 26, 2026**: MA $865,395 · Essex $903,325 ·
Boston $1,352,271. Quote it with its as-of date or not at all.

### Massachusetts — Market Indicators

| Metric | Calendar 2025 | Trailing 12mo (as of 2026-10-26) | Source |
|--------|--------------|----------------------------------|--------|
| Avg DOM | 35.6 days | 38 days | MLS PIN 🔄 |
| SP/LP Ratio | 101.18% | 100.9% | MLS PIN 🔄 |
| Units Sold | 38,870 | 41,021 | MLS PIN 🔄 |
| Median Price | $670,000 | $679,000 | MLS PIN 🔄 |

> Earlier revisions listed the trailing-12-month figures under a "2025" heading —
> most recently "Units Sold 39,323 ✅ Feb 2026", which is the live window, not the
> calendar year, and not a February figure. They are separated above.

### Haverhill Specific

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Median household income | $88,326 | Census QuickFacts ACS 2020-2024 | ⏳ re-read by 2026-12-31 — Census ACS 5-year, next release |
| MA median household income | $103,960 | ACS 2024 (5-yr), `data/census-latest.json` | 🔄 Jul 2026 |
| Condo median (Haverhill) | $395,000 | MLS | ⏳ re-read by 2026-12-31 — MLS PIN, quarterly pull |
| SF median (Haverhill) | $600,000 | MLS | ⏳ re-read by 2026-12-31 — MLS PIN, quarterly pull |
| Income needed for condo | ~$86K | Calc: 6.5%, 20% down, 28% DTI | ⏳ re-read by 2026-12-31 — derived from the condo median above and the stated rate assumptions; re-derive when either moves |
| Income needed for SF | ~$124K | Calc: 6.5%, 20% down, 28% DTI | ⏳ re-read by 2026-12-31 — derived from the SF median above and the stated rate assumptions; re-derive when either moves |

### New Hampshire — Market Data (PrimeMLS)

🔄 Source of truth: `data/nh-figures.json`, refreshed daily by `update-nh-figures.py`.
Values below are that file as of **2026-10-26**. (Feed is PrimeMLS, not Paragon.)

| Region | Median Price | Avg Sale | Avg DOM | SP/LP |
|--------|-------------|----------|---------|-------|
| NH Statewide | $446,361 | $534,557 | 29 days | 100.33% |

- **Active inventory:** 3,061 listings · median list $599,000 · avg list $851,494
- Also tracked per-market: Portsmouth, Salem, Derry, Windham

### Boston — Commercial Real Estate (CMBS)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Office vacancy (C&W) | 19.0% | Cushman & Wakefield Q2 2026 | ⏳ re-read by 2027-01-31 — Cushman & Wakefield Q4 2026 |
| Office vacancy (Colliers) | 23.7% | Colliers Q2 2026 | ⏳ re-read by 2027-01-31 — Colliers Q4 2026 |
| Office vacancy (CBRE) | 18.7% | CBRE Q2 2026 | ⏳ re-read by 2027-01-31 — CBRE Q4 2026 |
| National office vacancy | 20.1% | Cushman & Wakefield Q2 2026 | ⏳ re-read by 2027-01-31 — Cushman & Wakefield Q4 2026 |
| CMBS office delinquency | 11.57% | Trepp, June 2026 | ⏳ re-read by 2026-12-31 — Trepp monthly delinquency report |
| CMBS all-property delinquency | 7.35% | Trepp, June 2026 | ⏳ re-read by 2026-12-31 — Trepp monthly delinquency report |
| Pre-COVID vacancy | ~7.5% | Multiple sources | ⏳ re-read by 2027-06-30 — a baseline drawn from several sources; re-read when any of them restates it |

> **Vacancy definitions differ by brokerage — these are not competing estimates of one
> number.** C&W 19.0%, CBRE 18.7% and Colliers 23.7% all describe Greater Boston Q2 2026
> on different footprints (submarket set, building class, sublease treatment). Quote the
> brokerage with the figure, and don't mix them in a single time series.
| Major sale discounts (2025) | 31–62% losses | Boston Globe / CommercialEdge | ⏳ re-read by 2027-03-31 — press coverage of individual sales; re-read against the land records |
| Boston property tax dependence | ~73% of $4.8B budget | Boston.gov | ⏳ re-read by 2027-01-31 — Boston's FY2027 adopted budget |
| National avg office value decline | ~37% | Green Street | ⏳ re-read by 2027-01-31 — Green Street CPPI |

---

## 💼 Employment & Labor

### Massachusetts — Current Labor Market

🔄 Source of truth: `data/employment-latest.json`, refreshed monthly from the BLS API.
Values below are that file as of **2026-10-20** (reference month September 2026).

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| MA unemployment rate | 4.3% | September 2026 | BLS LAUS 🔄 |
| MA unemployment level | 166,882 | September 2026 | BLS LAUS 🔄 |
| MA labor force | 3,880,158 | September 2026 | BLS LAUS 🔄 |
| MA total nonfarm | 3,711,000 | September 2026 | BLS CES 🔄 |
| US unemployment rate | 4.2% | September 2026 | BLS 🔄 |
| US job openings | 7.079M | August 2026 | BLS JOLTS 🔄 |

> **⚠️ BLS discontinued monthly state-level JOLTS in 2026.** National JOLTS is still monthly;
> state figures are annual now, first annual release July 2026. Any "MA job openings rate"
> quoted monthly is a pre-2026 series and cannot be extended.

### Massachusetts — JOLTS (historical, pre-discontinuation)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Job openings rate (peak) | ~5.5% | BLS JOLTS | ⏳ re-read by 2026-12-31 — BLS JOLTS via FRED |
| Job openings rate (2025) | ~4.2% | BLS JOLTS | ⏳ re-read by 2026-12-31 — BLS JOLTS via FRED |
| MA premium over national rate | Nearly gone | BLS JOLTS | ⏳ re-read by 2026-12-31 — BLS JOLTS state tables |

### National — Labor Market (2025)

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| NFP downward revision (Apr 2024–Mar 2025) | -911,000 jobs | BLS benchmark | 🔒 the BLS annual benchmark revision for a closed period. Final. |
| Healthcare jobs added (2025) | +713,000 | BLS CES | ⏳ re-read by 2026-12-31 — BLS CES via FRED |
| Business/professional services lost | -97,000 | BLS CES | ⏳ re-read by 2026-12-31 — BLS CES via FRED |
| Manufacturing lost | -68,000 | BLS CES | ⏳ re-read by 2026-12-31 — BLS CES via FRED |
| Federal government jobs lost since peak | -277,000 (-9.2%) | BLS CES | ⏳ re-read by 2026-12-31 — BLS CES via FRED |
| Perceived job-finding probability | 43.1% (record low) | NY Fed SCE Dec 2025 | ⏳ re-read by 2026-12-31 — NY Fed Survey of Consumer Expectations, monthly |
| Private sector hiring plans | Lowest since 2009 | Challenger/BLS | ⏳ re-read by 2026-12-31 — Challenger Gray monthly report |

- **Key finding:** "Hiring recession" — low-hire/low-fire environment, worst since 2009 by multiple measures
- **Healthcare masks weakness:** 713K healthcare jobs > total net gains, meaning all other sectors flat/negative

### National — Employment Situation Release Dates

Machine-readable copy lives in [`data/bls-release-schedule.json`](data/bls-release-schedule.json); the employment updater reads it to stamp "Released &lt;date&gt;" on the national block.

| Reference Month | Released | Source | Verified |
|-----------------|----------|--------|----------|
| November 2025 | Dec 16, 2025 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| December 2025 | Jan 09, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| January 2026 | Feb 11, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| February 2026 | Mar 06, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| March 2026 | Apr 03, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| April 2026 | May 08, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| May 2026 | Jun 05, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| June 2026 | Jul 02, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| July 2026 | Aug 07, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| August 2026 | Sep 04, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| September 2026 | Oct 02, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| October 2026 | Nov 06, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| November 2026 | Dec 04, 2026 | BLS Employment Situation schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |

- **Not a first-Friday rule.** April 2026 went out on the *second* Friday (May 8) and June 2026 on a *Thursday* (Jul 2, moved for July 4). These dates cannot be computed — they must be read from the published schedule.
- **Source URL:** https://www.bls.gov/schedule/news_release/empsit.htm

### Massachusetts — State Employment & Unemployment Release Dates

The MA vintage. Lands ~3 weeks after the national release, which is why the MA blocks on the employment dashboard legitimately sit a month behind the national block. Same JSON file, `state_employment` key.

| Reference Month | Released | Source | Verified |
|-----------------|----------|--------|----------|
| November 2025 | Jan 07, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| December 2025 | Jan 27, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| January 2026 | Apr 08, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| February 2026 | Apr 22, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| March 2026 | May 06, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| April 2026 | May 22, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| May 2026 | Jun 23, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| June 2026 | Jul 21, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| July 2026 | Aug 21, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| August 2026 | Sep 18, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| September 2026 | Oct 20, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| October 2026 | Nov 20, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |
| November 2026 | Dec 18, 2026 | BLS State Employment and Unemployment schedule | 🔄 written by `scripts/stamp-bls-schedule.py` |

- **Even less regular than the national schedule.** The January 2026 reference month did not appear until **April 8, 2026**.
- **Source URL:** https://www.bls.gov/schedule/news_release/laus.htm
- **Maintenance:** BLS publishes ~13 months ahead. When the newest reference month is missing, the updater logs a `::warning::` in the Actions run and renders an em dash instead of inventing a date — that warning is the cue to top up the table above and the JSON.
- **Note:** bls.gov HTML 403s non-browser clients, so this cannot be scraped from CI (the same block that stalled the CBP feed). `api.bls.gov` serves the figures but carries no release dates.

---

## 🎓 Education

### Statewide Enrollment Shifts (2019–2025)

| Sector | Change | Source | Verified |
|--------|--------|--------|----------|
| K-12 overall | -3.5% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |
| Local public schools | -6.4% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |
| Private schools | -1% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |
| Vocational/technical | +18% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |
| Charter schools | +11% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |
| Homeschooling | +56% | DESE | ⏳ re-read by 2026-11-30 — DESE enrollment, SY2026 now published. NOTE: the stated figure could not be reproduced from DESE t8td-gens on 2026-10-21 -- that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% excluding pre-K) against the -3.5% published here. Re-derive on a stated basis before republishing. |

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

## 🏗️ Zoning — MBTA Communities Act § 3A

**Feed status:** live. `update-mbta-3a.py` reads three EOHLC tables weekly and
rewrites `mbta-3a-dashboard.html` plus `data/mbta-3a-latest.json`. Do not hand-edit
the figures below or on the page — change the source or the updater.

### What the law requires

| Field | Value | Source | Verified |
|-------|-------|--------|----------|
| Communities subject to § 3A | 177 | EOHLC capacity table | 🔄 written by `update-mbta-3a.py` |
| 2020 housing units across them | 1,941,671 | EOHLC capacity table | 🔄 written by `update-mbta-3a.py` |
| Minimum multi-family unit capacity | 297,190 | EOHLC capacity table | 🔄 written by `update-mbta-3a.py` |
| Minimum gross density | 15 units/acre | MGL c. 40A § 3A | 🔒 set by MGL c. 40A s 3A. Statute. |
| Distance from a station | 0.5 miles | MGL c. 40A § 3A | 🔒 set by MGL c. 40A s 3A. Statute. |
| Affordability required | none | MGL c. 40A § 3A | 🔒 set by MGL c. 40A s 3A. Statute. |
| Boston | exempt from the Zoning Act | EOHLC | 🔒 Boston is exempt from the Zoning Act by statute. |

Category shares of 2020 stock: rapid transit 25%, commuter rail 15%, adjacent
community 10%, adjacent small town 5%. Counts: 12 / 72 / 58 / 35.

- **Capacity is not construction.** The required figure is zoned capacity under
  EOHLC's compliance model. EOHLC states the model gives "reasonable estimates"
  and does "not provide absolute measures of development potential."
- **For 44 of 177 communities the percentage is not what binds.** Minimum land
  area is 50 acres, and at 15 units/acre that is a floor of about 750 units
  regardless of town size, which lands above the category share in a small town.
  Georgetown is nominally a 10% community and is required to zone for 24%.

### Compliance and what has been built

| Field | Value | Source | Verified |
|-------|-------|--------|----------|
| Compliant | 158 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Interim compliance | 9 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Noncompliant | 8 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Conditional compliance | 2 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Developments tracked in 3A districts | 104 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Total units in those developments | 10,065 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Deed-restricted units | 1,822 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |
| Communities with any tracked activity | 43 | EOHLC Compliance Status Sheet (2026-10-20) and 3A Development Tracker (2026-09-11) | 🔄 written by `update-mbta-3a.py` |

- **Tracked is not built.** The tracker mixes completed, permitted and proposed
  developments, and EOHLC says it is compiled from third-party information and
  may not be comprehensive.
- Tracked units are 3.4% of required capacity. Deed-restricted units are 18.1%
  of tracked units — and they come from local inclusionary zoning, 40B and
  deal-level subsidy, **not** from § 3A, which requires no affordability.

### Sources and transport

- Page: <https://www.mass.gov/info-details/multi-family-zoning-requirement-for-mbta-communities>
- Three CSVs are linked from that page and the updater **scrapes the links each
  run**. Two filenames carry the edition date ("as of 8-31-26"), so a hardcoded
  URL would 404 silently the moment EOHLC published the next edition.
- mass.gov returns 403 to a bare request. The filter is **header-based**, not the
  client fingerprinting that defeats cbp.gov — curl with a full browser header
  set (including the `Sec-Fetch-*` trio) gets 200, verified from a GitHub-hosted
  runner. If that ever changes the updater exits 75 and the page keeps its edition.

### ⚠️ The $4.49B cost figure — attributed, and it does not reconcile

The Brensley Cost Impact Report (Dec 2025, prepared for the State Auditor) is
quoted widely at **$4.49B** in designer base fees. The dashboard reproduces it as
her attributed estimate **with the arithmetic shown**, because the published
method does not produce it:

```
273,080 units x 900 sf x $250/sf = $61.44B construction cost
$61.44B x 5.9% DCAMM designer fee =  $3.63B   <- not $4.49B
reaching $4.49B from that base needs a rate of about 7.3%
```

It also uses 273,080 units, which is no longer EOHLC's published total (297,190).
Neither point makes the estimate worthless; both mean it is an order of magnitude
from a stated method, not a precise liability. **Do not restate $4.49B without
the caveat**, and do not recompute it against 297,190 and present the result as
Brensley's — that would be this site's arithmetic wearing her attribution.

### ⚠️ The campaign-finance section is fixed, not live

"Follow the Money" on that page is a carried-over investigation current as of
**February 2026** and is labelled as such on the page. It aggregates roughly
107,900 OCPF contribution records for the four officials who authored,
implemented or enforce § 3A (Sen. Brendan Crighton, Gov. Maura Healey, AG
Andrea Campbell, Rep. Kevin Honan), plus Secretary of the Commonwealth lobbyist
registrations and IRS Form 990 filings via ProPublica. It has **not** been re-run
against OCPF since. Donation patterns establish association, not agreement.

---

## 🏥 Healthcare & Insurance

### 2026 MA Rate Increases (Division of Insurance)

| Carrier | Approved Increase | Verified |
|---------|------------------|----------|
| Harvard Pilgrim | 12.2% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| Blue Cross Blue Shield | 11.9% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| Tufts Health | 11.1% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| Health New England | 9.4% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| UnitedHealthcare | 9.3% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| MGB Health Plan | 7.2% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |
| Fallon Health | 7.1% | 🔒 an approved 2026 plan-year rate increase. Once the Division of Insurance approves the plan year's rates they are set for it; the 2027 filings are a new row, not a revision of this one. |

- **Average increase:** 9.9% (3x inflation rate of ~3%)
- **State benchmark:** 3.6%
- **Consumers affected:** 711,563
- **Saved via negotiations:** $54M

### Premium Comparisons

| Year | MA Family Premium | US Average | MA Premium Gap |
|------|-------------------|------------|----------------|
| 2024 | $28,151 (1st of 50) | $24,540 | +14.7% |
| 2025 | $29,619 (4th of 50; AK $30,132, NY $29,752, NJ $29,666 higher) | $26,281 | +12.7% |

Family premiums: AHRQ MEPS-IC private-sector state estimates, as published in KFF State Health
Facts (kff.org/private-insurance/state-indicator/family-coverage). The state figures are MEPS-IC,
not the KFF Employer Health Benefits Survey, which is national. The $26,993 previously listed as
the 2025 US average is not the MEPS-IC figure. ✅ Oct 2026.

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Personal health care spending per capita, 2020 | MA $13,319, 3rd of 50 states (NY $14,007, AK $13,642; DC $14,381); US $10,191 | CMS Health Expenditures by State of Residence, US_PER_CAPITA20.CSV (newest state edition, 1991-2020) | ⏳ re-read by 2027-06-30 — CMS Health Expenditures by State of Residence |
| Employer family premium, 2025 | MA $29,619, 4th of 50; US $26,281 | AHRQ MEPS-IC 2025 via KFF | ⏳ re-read by 2027-06-30 — AHRQ MEPS-IC, annual |

### Family premium series (healthcare dashboard trend, contribution and cost-vs-income charts)

AHRQ MEPS-IC state tables, Table II (private sector), downloaded from
meps.ahrq.gov/mepsweb/data_stats/state_tables.jsp (Massachusetts{year}.xlsx, UnitedStates{year}.xlsx).
KFF State Health Facts republishes the same values. ✅ Oct 2026.

| Year | MA family premium (II.D.1) | US family premium | MA employee contribution (II.D.2) | US employee contribution |
|------|---:|---:|---:|---:|
| 2020 | $21,965 | $20,758 | $5,741 | $5,978 |
| 2021 | $22,163 | $21,381 | $5,976 | $6,174 |
| 2022 | $23,348 | $21,931 | $5,875 | $6,492 |
| 2023 | $26,355 | $23,938 | $7,597 | $6,889 |
| 2024 | $28,151 | $24,540 | $7,811 | $7,216 |
| 2025 | $29,619 | $26,281 | $7,501 | $7,314 |

- **MA family premium growth:** +28.2% 2020-2024; +34.8% 2020-2025; +5.2% 2024-2025 (derived).
- **Comparators on the cost-vs-income tab, 2020-2024:** MA median household income +23.2% (ACS
  5-year B19013: $84,385, $89,026, $96,505, $101,341, $103,960); Boston CPI-U +18.3% (BLS
  CUURS11ASA0 annual averages: 284.266, 293.521, 314.356, 326.016, 336.376). ✅ Oct 2026.
- **Premium as a share of median income, 2024:** MA 27.1% ($28,151 / $103,960); US 30.4%
  ($24,540 / $80,734, ACS 2024 5-year). Both on the same income basis. ✅ Oct 2026.

The series these replaced (MA $23,541, $24,805, $25,262, $27,240 for 2020-2023, labelled "KFF
EHBS") matched no MEPS-IC year but 2024. With them the page said premiums "roughly track
inflation" (+19.6%); on MEPS-IC they outran both inflation and income. The old affordability
card put the US premium at 24.2% of income against its own figures' 30.4%, and mixed an ACS
2023 1-year US income ($80,610) with MA 5-year income.

- **Sources:** AHRQ MEPS-IC state tables (premiums); KFF State Health Facts (state rankings, republishing MEPS-IC)

---

## 📊 Cost of Living

### SNAP vs. Poverty

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| MA SNAP persons participating | 889,327 (June 2026, initial) | USDA-FNS SNAP Data Tables, `snap-persons-9.xlsx`, data as of 11 Sep 2026 | ⏳ re-read by 2026-12-31 — USDA-FNS SNAP data tables |
| MA SNAP persons, a year earlier | 1,079,234 (June 2025) | same file | ⏳ re-read by 2026-12-31 — USDA-FNS SNAP data tables |
| Change over the year | −17.6% (about −190,000 people) | same file | ⏳ re-read by 2026-12-31 — derived from the two SNAP rows above |
| MA poverty rate | 9.7% | Census ACS 1-year 2024, table S1701 (API, retrieved 4 Oct 2026) | ⏳ re-read by 2027-09-30 — Census ACS 1-year, table S1701 |
| MA residents receiving SNAP | 15.6% of the state population | USDA-FNS FY2024 persons over 2024 population (derived) | ⏳ re-read by 2026-12-31 — USDA-FNS over Census population |

- **The headcount fell hard.** MA SNAP enrolment is down 17.6% year over year on
  USDA's own monthly series. The figure this table carried until 4 Oct 2026 was
  1.11M, which overstated it by roughly 190,000 people.
- **That 15.6% was mislabelled, and this is the correction.** It is the share of
  Massachusetts *residents* on SNAP, derived as FY2024 persons over 2024
  population. USDA's own "participation rate" is a different measure entirely —
  the share of *eligible* people who enrol — and for Massachusetts it is reported
  at the 100% cap. The two are not interchangeable and must never be swapped for
  one another. See `E:\Research\MA-SNAP-vs-poverty-2026.md` section 5 for the
  working; the 100% figure is carried from there and has not been re-derived here.
- On the current headcount the share of residents would be about 12.5% (889,327
  over roughly 7.1M), but that pairs a June 2026 count with an older population
  denominator, so it is not published as a figure.
- **The old "gap (SNAP − poverty) 5.2 pp" row is dropped**, because it
  subtracted a participation rate from a poverty rate — two different
  denominators over two different years. It was arithmetic, not a finding.
- ACS 1-year 2025 was not yet on the Census API on 4 Oct 2026; 2024 is the
  newest published year.
- **SNAP covering more people than are in poverty is what the rules produce, not
  a red flag.** Massachusetts uses broad-based categorical eligibility, which
  sets the gross income limit at 200% of the federal poverty line with no asset
  test. In 2024 there were 671,003 people below 100% FPL and 1,395,144 below
  200%; SNAP covered about 1.12M. The caseload sits between those two bounds,
  which is where the eligibility rule puts it. The gap is not, on its face,
  evidence of fraud, and nothing on this site says otherwise — but the fraud
  table directly below invites the inference, so the rule is stated here.
- **The fall has a cause.** The decline from mid-2025 follows P.L. 119-21, whose
  SNAP provisions states had to implement by 1 Nov 2025. The national drop over
  the same period was 12.8% against Massachusetts' 17.6%.
- Fuller workings, including the 2020–2026 series, ACS margins of error and the
  EBT-skimming figures, are in `E:\Research\MA-SNAP-vs-poverty-2026.md`
  (retrieved 2026-09-30). Its June-2026 headcount and year-over-year change were
  derived independently of the 4 Oct 2026 pull above and match it exactly.

### SNAP Fraud Detection

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Expected fraud (national model) | ~$50M | USDA-FNS Trafficking Studies | ⏳ re-read by 2027-06-30 — USDA-FNS trafficking studies |
| Detected fraud (MA), BSI Q1 FY2025 | $2,549,325 all programs, of which SNAP $1,528,615 | BSI Q1 FY2025 report, malegislature.gov/Bills/194/SD2676.pdf | ⏳ re-read by 2027-01-31 — the next BSI quarterly |
| Detection rate (SNAP, one quarter) | ~3.1% ($1,528,615 ÷ ~$50M) | Calculated | ⏳ re-read by 2027-01-31 — derived from the two rows above |
| Leading fraud type | Identity fraud (31%) | LexisNexis True Cost of Fraud | 🔒 a published LexisNexis study finding, fixed text. |

- This row previously read $0.69M, which matches no line of the Q1 FY2025 report. It equals the SNAP figure ($690K) in the FY2025 Q4 program breakdown (inference). The detection rate compares one quarter with a model figure, so treat it as a floor.

### BSI — fraud identified, all programs (State Auditor, Bureau of Special Investigations)

Administrative findings, not convictions. BSI cannot collect settlements; the benefit programs do.

| Period | Fraud identified | Source | Verified |
|--------|------------------|--------|----------|
| FY2022 | $13,519,349.55 | BSI FY2022 Annual Report (Wayback of mass.gov) | 🔒 a published BSI annual report for a closed fiscal year. |
| FY2023 | $12,322,688.13 | BSI FY2023 Annual Report | 🔒 a published BSI annual report for a closed fiscal year. |
| FY2024 | $10,265,265 | BSI FY2024 Annual Report | 🔒 a published BSI annual report for a closed fiscal year. |
| FY2025 | $11,952,288 ($11.95M), 4,179 investigations | OSA release, 30 Jan 2026 | 🔒 the State Auditor's release of 30 Jan 2026, a published document for a closed fiscal year. |
| FY2026 first half (Q1 + Q2, Jul–Dec 2025) | $4,486,102; civil recoveries $392,713 | malegislature.gov/Bills/194/SD3769.pdf | 🔒 a filed report, SD.3769. Not reissued. |
| FY2025 Q1 | $2,549,325 (SNAP $1,528,615) | malegislature.gov/Bills/194/SD2676.pdf | 🔒 a filed quarterly report, SD.2676. Not reissued. |
| Annual range FY22–FY25 (tax-budget card) | $10.3–13.5M | Derived from the rows above | ⏳ re-read by 2027-01-31 — derived from the BSI annual rows above |
| Detection rate (tax-budget card) | 0.26% = FY25 $11.95M ÷ $4,550M benefit base in the page's own table | Calculated | ⏳ re-read by 2027-01-31 — derived from BSI FY25 over the benefit base |
| Program breakdown on tax-budget-dashboard | MassHealth $3.8M, SNAP $690K, PCA $146K, Childcare $135K, TAFDC $23K, EAEDC $9K — **FY2025 Q4 quarterly (Apr–Jun 2025), not annual**; the table's Detected column sums to $4.66M | BSI FY2025 Q4 report | ⏳ re-read by 2027-01-31 — the next BSI annual |

FY2026 full year not yet published (checked 30 Sep 2026).

---

## 🏦 Gold & Treasury

### US Treasury Gold Holdings

| Metric | Value | Source | Verified |
|--------|-------|--------|----------|
| Total holdings | 261.5M fine troy oz | Treasury Status Report of U.S. Government Gold Reserve, 2026-09-30, via the Fiscal Data API | 🔄 written by `update-gold-reserve.py` |
| Holdings change since the earliest report | Flat — +27 oz (+0.000%) since 2012-01-31 | Treasury Status Report of U.S. Government Gold Reserve, 2026-09-30, via the Fiscal Data API | 🔄 written by `update-gold-reserve.py` |
| Fort Knox | 147.3M oz | Treasury Status Report of U.S. Government Gold Reserve, 2026-09-30, via the Fiscal Data API | 🔄 written by `update-gold-reserve.py` |
| West Point | 54.1M oz | Treasury Status Report of U.S. Government Gold Reserve, 2026-09-30, via the Fiscal Data API | 🔄 written by `update-gold-reserve.py` |
| Denver | 43.9M oz | Treasury Status Report of U.S. Government Gold Reserve, 2026-09-30, via the Fiscal Data API | 🔄 written by `update-gold-reserve.py` |

### Global Central Bank Buying

| Year | Annual Purchases (tonnes) | Source | Verified |
|------|--------------------------|--------|----------|
| 2010-2021 avg | ~473t | World Gold Council | ⏳ re-read by 2027-02-28 — World Gold Council annual demand trends |
| 2022 | 1,082t (record) | World Gold Council | ⏳ re-read by 2027-02-28 — World Gold Council annual demand trends |
| 2023 | 1,037t | World Gold Council | ⏳ re-read by 2027-02-28 — World Gold Council annual demand trends |
| 2024 | 1,045t | World Gold Council | ⏳ re-read by 2027-02-28 — World Gold Council annual demand trends |
| H1 2025 | 415t (~830t pace) | World Gold Council | ⏳ re-read by 2027-02-28 — World Gold Council annual demand trends |

- **Unreported purchases (2022):** 741 tonnes (likely China, Russia)
- **Gold price (2026):** Hit $4,889/oz

---

## 🧾 Tax Burden — Federal & Massachusetts

Machine-readable source of truth: [`data/burden-constants.json`](data/burden-constants.json).
`tax-burden-dashboard.html` is generated from it by `update-burden-constants.py` --
that script's TARGETS list holds that page and no other. Change the JSON, not the HTML.
`tax-burden-nh-comparison.html` is NOT generated: it is maintained by hand and carries
its own `data-checked` stamp, which the freshness watchdog ages.

| Figure | Value | Source | URL | Verified |
|---|---|---|---|---|
| Federal standard deduction TY2026 | $16,100 single / $32,200 MFJ | IRS Rev. Proc. 2025-32 | irs.gov/pub/irs-drop/rp-25-32.pdf | ⏳ re-read by 2026-12-31 — the IRS revenue procedure for the next tax year, issued each autumn |
| Social Security wage base 2026 | $184,500 | SSA contribution & benefit base | ssa.gov/oact/cola/cbb.html | ⏳ re-read by 2026-12-31 — the SSA contribution and benefit base, announced each October |
| MA income tax rate | 5.0% flat | M.G.L. c. 62 §4 | malegislature.gov | 🔒 statutory rate or citation; changes only when the law does |
| MA 4% surtax threshold TY2026 | $1,107,750 | M.G.L. c. 62 §§4(d), 5A; DOR | mass.gov/info-details/massachusetts-4-surtax-on-taxable-income | 🔒 statutory rate or citation; changes only when the law does |
| MA interest, dividends & long-term gains | 5% | M.G.L. c. 62 §4(a),(c) | mass.gov/info-details/massachusetts-income-tax-rates | 🔒 statutory rate or citation; changes only when the law does |
| MA short-term capital gains | 8.5% (cut from 12%, St. 2023 c. 50) | M.G.L. c. 62 §4(c) | same | 🔒 statutory rate or citation; changes only when the law does |
| MA motor fuel excise | **26.5¢/gal** (24¢ + 2.5¢ UST) | M.G.L. c. 64A §1; c. 21J §3 | mass.gov/info-details/motor-fuel-excise-tax | 🔒 statutory rate or citation; changes only when the law does |
| MA avg single-family tax bill FY2026 | $8,113 | DLS *City & Town*, Feb 2026 | mass.gov/info-details/fy2026-statewide-average-single-family-tax-bill | ⏳ re-read by 2027-03-31 — DLS City & Town, which publishes the average bill each February |
| MA avg single-family assessed value FY2026 | $742,986 → 1.092% effective | DLS *City & Town*, Feb 2026 | same | ⏳ re-read by 2027-03-31 — DLS City & Town, which publishes the average bill each February |
| MA corporate & business excise FY2025 | $4.662B | DOR FY2025 close, Aug 2025 | mass.gov/news/fiscal-year-2025-revenue-collections-totaled-43708-billion | ⏳ re-read by 2027-09-30 — the DOR fiscal-year revenue close, published each August |
| MA households | 2,829,804 | Census ACS 2024 1-yr, B11001 | censusreporter.org/profiles/04000US25-massachusetts/ | ⏳ re-read by 2027-06-30 — the publisher's next release |
| MA aggregate household income | $408.376B | Census ACS 2024 1-yr, B19025 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| **MA mean household income** | **$144,312** (B19025 ÷ B11001) | Derived — the allocation divisor | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| MA population | 7,044,056 | Census ACS 2024 5-yr, B01003 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| MA share of national household income | 2.6918% (derived) | ACS B19025 ÷ national B19025 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| MA share of national population | 2.1032% (derived) | ACS B01003 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| US households | 132,737,144 | Census ACS 2024 1-yr, B11001 | censusreporter.org/tables/B11001/ | ⏳ re-read by 2027-06-30 — the publisher's next release |
| US aggregate household income | $15.171T | Census ACS 2024 1-yr, B19025 | censusreporter.org/tables/B19025/ | ⏳ re-read by 2027-06-30 — the publisher's next release |
| Federal deficit FY2025 | $1.8T (5.8–5.9% of GDP) | CBO Monthly Budget Review, Oct 2025 | cbo.gov/publication/61307 | ⏳ re-read by 2026-12-31 — the CBO Monthly Budget Review |
| **Federal corporate income tax receipts FY2025** | **$452,089,303,420** (net) | U.S. Treasury, Final Monthly Treasury Statement Sept 2025, Table 4 | api.fiscaldata.treasury.gov — mts_table_4 | ⏳ re-read by 2026-12-31 — the Final Monthly Treasury Statement for the fiscal year |
| Federal corporate receipts FY2024 | $529,866,802,638 — FY25 is −14.7% | same | same | 🔒 a closed federal fiscal year's final Treasury figure. |
| MA unfunded pension + OPEB (stock) | $55.8B total · $42.1B pension-only · $19,719/household | Commonwealth ACFR FY2024; PERAC | See pension-dashboard.html | ⏳ re-read by 2027-03-31 — the annual comprehensive financial report |
| MA annual pension appropriation FY2026 | $4.9B — ~8% of the state budget, **already in Layer 1** | Commonwealth budget FY2026 | same | 🔒 an enacted appropriation for a closed fiscal year. |
| **MA residential electricity, all-in** | **30.49¢/kWh** (Jul 2026) | EIA Electric Power Monthly Table 5.6.A via API v2 | api.eia.gov/v2/electricity/retail-sales/data/ | ⏳ re-read by 2026-12-31 — EIA Electric Power Monthly Table 5.6.A. NOTE: update-energy-dashboard.py already fetches this series -- these rows should be wired to it rather than re-read by hand |
| **NH residential electricity, all-in** | **27.01¢/kWh** (Jun 2026) | same | same | ⏳ re-read by 2026-12-31 — EIA Electric Power Monthly Table 5.6.A |
| US / New England residential electricity | 18.31¢ (Jul 2026) / 28.14¢ (May 2026 — the newest New England figure in this repo. The MA and US cells are stamped from the EIA fetch by update-energy-dashboard.py; this one is not fetched, so it stays put until a newer New England figure is actually published here) | same | same | ⏳ re-read by 2026-12-31 — EIA Electric Power Monthly Table 5.6.A. NOTE: update-energy-dashboard.py already fetches this series -- these rows should be wired to it rather than re-read by hand |
| **MA annual overpayment vs US average** | **$877/household** (Jul 2026) | Derived: (MA rate − US rate) × 7,200 kWh/yr | same | ⏳ re-read by 2026-12-31 — derived from the MA and US EIA rates above; re-derive when either moves |
| FL residential electricity — the dashboard’s low-rate comparison | 15.03¢/kWh (Jul 2026) | EIA Electric Power Monthly Table 5.6.A via API v2 | api.eia.gov/v2/electricity/retail-sales/data/ | ⏳ re-read by 2026-12-31 — EIA Electric Power Monthly Table 5.6.A. NOTE: update-energy-dashboard.py already fetches this series -- these rows should be wired to it rather than re-read by hand |
| **MA electric policy charges** | **3.663¢/kWh** — EE 2.292 + NMRS 0.625 + SMART 0.583 + EV 0.104 + RE 0.050 + PSPF 0.008 + ESMP 0.001 (was 3.789 for 1 Jul - 31 Aug 2026) | Eversource MA filed rates, Rate R1, Greater Boston, eff. 1 Sep 2026 | eversource.com/docs/default-source/rates-tariffs/ema-greater-boston-rates.pdf | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| **Eversource R-1 bill at 600 kWh/month** | $225.75: supply 46.0%, distribution 26.1%, transmission 12.4%, **policy line items 9.7%**, customer charge 4.4%, decoupling and transition 1.2% (derived; policy items inside distribution and supply not counted) | Same rate summary; Basic Service fixed 17.323¢ from 1 Aug 2026 (NSTAR summary M.D.P.U. No. 1-26-E) | eversource.com/docs/default-source/rates-tariffs/ma-electric-supply-rate-archive/july-2026-summary-rate-table.pdf | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| **MA gas policy charges** | **59.08¢/therm** — EE 41.70 + GSEP 17.38 | Eversource MA Summary of Gas Rates | eversource.com/docs/default-source/rates-tariffs/summary-rates-gas.pdf | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| MA gas commodity cost | 38.42¢/therm (eff. 1 May 2026) — **less than the policy riders above** | Eversource MA Cost of Gas | eversource.com/…/ma-cost-of-gas | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| MA electric distribution / transmission | 9.443¢ / 4.673¢ per kWh — excluded as infrastructure | same tariff | same | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| MA pension-only unfunded (stock) | $42.1B · $14,877/household | Commonwealth ACFR FY2024; PERAC | See pension-dashboard.html | ⏳ re-read by 2027-03-31 — the annual comprehensive financial report |
| MA state/local accrual in the burden model | **$0 — excluded by design**, see note below | Scope decision | — | 🔒 a scope decision this project made and records, not a measurement. It changes only if the model's boundary changes. |

### ⚠️ The two MA median-income figures — do not merge them

| Vintage | Value | Concept | Use |
|---|---|---|---|
| Census **CPS ASEC** via FRED `MEHOINUSMAA646N` | **$118,500** | Median household income **2025** | Context / presets |
| Census **CPS ASEC**, same series | $112,300 | Median household income 2024 | superseded |
| Census **ACS 1-year** B19013 | **$104,828** | Median household income 2024 | Context / presets |
| Census **ACS 5-year** B19013 | $103,960 | Median household income 2024 | `data/census-latest.json`, checked by check-consistency |
| Census **ACS 1-year** B19025 ÷ B11001 | **$144,312** | *Mean* household income | **Allocation divisor** |

CPS and ACS disagree by roughly $14K on the same concept. Carry both and cite which one
any given chart uses — this is exactly the kind of thing a hostile reader finds first.

**Updated 2026-10-18.** CPS ASEC 2025 is published, so the dashboard moved to $118,500
(US $87,460, +35.5%). Two things were wrong before that and are worth recording: the
$113,900 this table carried was not the CPS 2024 value either — FRED gives $112,300 —
and the dashboard's US comparator read $83,730 against an actual $83,160.

**This section earned its keep on 2026-10-18.** An audit of the cost-burden table flagged
the income row as contradicting `census-latest.json`, and the first fix swapped it to ACS
5-year. That would have re-broken the defect closed on 2026-08-11. Reading this section is
what caught it. Keep it; it is doing work.

**~~Known defect to fix~~ — FIXED 2026-08-11.** `tax-budget-dashboard.html` labelled
$113,900 as "Census 2024 ACS"; it is the **CPS** figure and is now labelled "Census CPS
ASEC (2024)" in both places, with the $104,828 ACS comparator named inline. The same file
carried an unlabelled "$7,732/year" property tax figure; the hero stat, the prose and the
stat card now read **$8,113 (FY2026)**. The FY2025 county table keeps its own FY2025
source line — it was already labelled correctly and its county figures are FY2025.

The `chartIncomeReal` cross-state bar series still uses 113,900 for MA, now a year
and a revision out of date while the table beside it reads 118,500. Left alone
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

### Enacted budgets FY2018–FY2027, headline scope (`GAA_SIGNED` + `FY27_GAA`)

| Fiscal year | Enacted, headline scope ($B) | Source | Verified |
|---|---:|---|---|
| FY2018 | 40.197 | `gaabudgets` FY21 workbook; statewide summary TOTAL $40,196,899K (budget.digital.mass.gov/bb/gaa/fy2018) | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2019 | 41.883 | `gaabudgets` FY21 workbook; statewide summary TOTAL $41,883,308K (bb/gaa/fy2019) | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2020 | 43.590 | `gaabudgets` FY21 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2021 | 46.459 | `gaabudgets` FY24 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2022 | 48.085 | `gaabudgets` FY25 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2023 | 52.444 | `gaabudgets` FY26 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2024 | 56.063 | `gaabudgets` FY27 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2025 | 57.718 | `gaabudgets` FY27 workbook | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2026 | 60.974 | `gaabudgets` FY27 workbook (after overrides; the FY26 workbook read 60.904 at signing) | 🔒 an enacted General Appropriation Act total. The year is closed and the enacted figure is final. |
| FY2027 | 63.416 | `gaabudgets` FY27 workbook | ⏳ re-read by 2027-07-31 — the enacted FY2027 total can still move on a supplemental; final after the year closes |
| Growth, FY2018 to FY2026 | +51.7% (derived) | above | ⏳ re-read by 2027-07-31 — derived from the GAA rows above |
| Growth, FY2018 to FY2027 | +57.8% (derived) | above | ⏳ re-read by 2027-07-31 — derived from the GAA rows above |

Each year is taken from the newest workbook that carries it (budget.digital.mass.gov,
summary/fyNN/downloads), because a later workbook restates the year after overrides. Every
workbook that carries a year agrees on it to the nearest $1M, except FY26 as noted. The series
this replaced on the dashboard (39.4, 42.7, 44.6, 45.9, 49.7, 52.7, 56.2, 57.8, 60.9) mixed
scopes and was off by up to $1.6B in both directions; it had put FY2018-to-FY2026 growth at
+54.6%.

### FY2027 enacted — key figures

| Figure | Value | Source | Verified |
|---|---|---|---|
| FY2027 GAA, headline scope | **$63.416B** (+4.01% over FY26) | H.5555, signed 9 Jul 2026 | 🔒 H.5555, signed 9 July 2026. A signed act. |
| **Governor's vetoes** | **$0 — none.** Signed the conference report untouched | Globe / CommonWealth Beacon, 9 Jul 2026 | 🔒 a matter of record on a signed act: none were cast. |
| Votes | Senate 39–1, House 142–6 | State House News | 🔒 recorded roll calls. A vote is not re-taken. |
| Chapter 70 | **$7,658,399,506** (+$793.5M, +11.6%) — *final year of the SOA ramp* | `sect3.xlsx` | 🔒 an enacted line in a signed act. |
| — municipal / regional split | $6,695,466,289 / $962,933,217 | same | 🔒 an enacted split in a signed act. |
| Unrestricted General Government Aid | **$1,363,109,516** (+$40M, +3.0%) | same | 🔒 an enacted line in a signed act. |
| SpEd Circuit Breaker | $654.6M (+35.0%); $806.6M incl. Fair Share supp. | `gaabudgets.xlsx` | 🔒 an enacted line in a signed act. |
| Fair Share surtax deployed | ~$2.7B (~64% education / ~36% transportation) | MTF | ⏳ re-read by 2027-01-31 — Mass Taxpayers Foundation analysis |
| Emergency Assistance family shelter | $259.9M (−6.0%; was $325.3M in FY24) | `gaabudgets.xlsx` | 🔒 the FY2027 enacted line. Actual spending against it is written by update-immigrant-spending.py and is a different measure. |
| State Retiree Benefits Trust (OPEB) deposit | **$400M**, down from $550M in FY24 (−27%) | line 1595-6152 | 🔒 an enacted line (1595-6152) in a signed act. |
| Line items in `tax-budget-dashboard.html` | 860, **all 860 verified against the official GAA** | `gaa1.xlsx` diff | ⏳ re-read by 2027-07-31 — re-diff the dashboard against gaa1.xlsx for FY2028 |

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

**FY25 gap = $5.736B** (63.303 − 57.567), used everywhere on `tax-budget-dashboard.html`
(constants `GAA_FY25_ACTUAL` / `GAA_FY25_ENACTED_LFL`). Label it **supplemental spending above
the enacted budget, not waste**. It replaced a $6.2B figure computed as a House Ways & Means
outturn ($64.0B) minus the signed headline ($57.8B), two different scopes.

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
| NH individual income tax | **0%** — I&D repealed 1 Jan 2025 | NH DRA; HB 2 (2023) ch. 79 §§86-88 | revenue.nh.gov/news-and-media/repeal-nh-interest-and-dividends-tax-now-effect | 🔒 statutory rate or citation; changes only when the law does |
| NH I&D rate history | 5% → 4% (2023) → 3% (2024) → 0% (2025) | NH DRA | revenue.nh.gov/taxes-glance/interest-dividends-tax | 🔒 statutory rate or citation; changes only when the law does |
| NH capital gains tax | **None — never levied** (not a 2025 change) | NH DRA | revenue.nh.gov/taxes-glance | 🔒 statutory rate or citation; changes only when the law does |
| NH general sales tax | None | NH DRA | revenue.nh.gov | 🔒 statutory rate or citation; changes only when the law does |
| NH Meals & Rooms tax | 8.5% | RSA 78-A | revenue.nh.gov/taxes-glance/meals-rentals-tax | 🔒 statutory rate or citation; changes only when the law does |
| NH Business Profits Tax | 7.5% | RSA 77-A | revenue.nh.gov/taxes-glance/business-taxes | 🔒 statutory rate or citation; changes only when the law does |
| NH Business Enterprise Tax | 0.55% on compensation + interest + dividends paid | RSA 77-E | same | 🔒 statutory rate or citation; changes only when the law does |
| NH Real Estate Transfer Tax | $0.75 per $100, **each side** | RSA 78-B | revenue.nh.gov | 🔒 statutory rate or citation; changes only when the law does |
| NH households | 570,689 | Census ACS 2024 1-yr, B11001 | censusreporter.org/profiles/04000US33-new-hampshire/ | ⏳ re-read by 2027-06-30 — the publisher's next release |
| NH aggregate household income | $73.393B | Census ACS 2024 1-yr, B19025 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| **NH mean household income** | **$128,604** (B19025 ÷ B11001) | Derived — allocation divisor | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| NH median household income 2024 | $99,782 | Census ACS 2024 1-yr, B19013 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| NH population | 1,394,868 | Census ACS 2024 5-yr, B01003 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| NH share of national household income | **0.4838%** (derived) | ACS B19025 ÷ national B19025 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| NH share of national population | 0.4165% (derived) | ACS B01003 | same | ⏳ re-read by 2027-06-30 — the publisher's next release |
| **NH average municipal property rate 2025** | **$15.83 per $1,000 → 1.583%** (was $20.96 in 2019) | NH Fiscal Policy Institute | nhfpi.org/resource/property-taxes-in-new-hampshire-how-they-work-and-how-they-compare/ | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| NH per-capita property tax FY2022 | $3,388 — **2nd highest state**, behind NJ $3,617 | NHFPI | same | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| NH property tax reliance | 60% (NHFPI) vs 63–64% (InDepthNH) — **carry both** | NHFPI / InDepthNH | same | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| **NHRS unfunded liability** | **$5.58B**, 68.6% funded (30 Jun 2024) · $9,778/household | NHRS ACFR + GASB 67/74, FY2025 release | nhrs.org/docs/default-source/gasb/ | ⏳ re-read by 2027-03-31 — the annual comprehensive financial report |
| NH municipal rate range | $2.62 – $36.54 per $1,000 | InDepthNH, Apr 2026 | indepthnh.org | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| NH property tax share of state+local revenue | 63–64% | InDepthNH / NHFPI, Apr 2026 | same | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| **NH business taxes FY2025 (BPT+BET)** | **$1,102.6M** — Gen $670.5M + Ed $432.1M | NH DAS Monthly Revenue Focus, June FY2025 accrual | das.nh.gov/accounting/FY%2025/FY2025_Monthly_Revenue_June_Preliminary_Accrual.pdf | ⏳ re-read by 2026-12-31 — the NH DAS monthly revenue focus |
| NH business taxes FY2024 | $1,217.9M (FY25 is −9.5%, and −12.4% vs the $1,259.0M plan) | same | same | 🔒 a closed New Hampshire fiscal year's final revenue figure. |
| NH BPT / BET split | 75% / 25% — **assumed** | DAS publishes them combined; split needs NH DRA | revenue.nh.gov/taxes-glance/business-taxes | ⚠️ Split unverified |
| NH Interest & Dividends revenue FY2025 | $90.8M, down 50.7% from FY2024's $184.3M | NH DAS, June FY2025 accrual | same | ⏳ re-read by 2026-12-31 — the NH DAS monthly revenue focus |
| NH General + Education Fund revenue FY2025 | $3,122.7M, 1.3% below plan | NH DAS, June FY2025 accrual | same | ⏳ re-read by 2026-12-31 — the NH DAS monthly revenue focus |
| NH road toll (gas) | **23.75¢** = 22.2¢ toll + ~1.55¢ oil discharge surcharge | RSA 260:32 (base $0.18, +4.2¢ per 2014 SB 367); RSA 146-A | gc.nh.gov/rsa/html/XXI/260/260-32.htm | 🔒 statutory rate or citation; changes only when the law does |
| NH BET share of business taxes | 25.7% (5-yr TY2019–23 avg); TY2023 BET = $253M | NHFPI | nhfpi.org/resource/business-enterprise-tax-rate-decreases-have-lowered-revenue-with-limited-economic-benefit/ | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| NH BET rate history | 0.75% → 0.72% (2016) → 0.675% (2018) → 0.6% (2019) → 0.55% (2022–) | NHFPI | same | ⏳ re-read by 2027-06-30 — the NHFPI/InDepthNH analysis it rests on |
| **NH electric policy charges** | **0.618¢/kWh** — System Benefits Charge, the only mandated rider | Eversource NH filed tariff, Rate R | eversource.com/…/electric-delivery-rates/nh | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| **NH gas policy charges** | **16.30¢/therm** — Liberty EnergyNorth LDAC (a *ceiling*, bundles mechanisms MA excludes) | NHPUC DG 24-098; see also DE 25-071 | new-hampshire.libertyutilities.com | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| NH electric distribution / transmission | 6.727¢ / 4.445¢ per kWh — excluded as infrastructure | Eversource NH Rate R | same | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| NH stranded cost recovery | **−0.148¢/kWh — a credit, not a charge** | Eversource NH Rate R | same | ⏳ re-read by 2027-01-31 — the filed tariff, when the next rate change takes effect |
| NH state/local accrual in the burden model | **$0 — excluded by design**, same rule as MA | Scope decision | — | 🔒 a scope decision this project made and records, not a measurement. It changes only if the model's boundary changes. |

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
| Residential Electricity Rates — MA vs. Selected States (¢/kWh) | EIA Electric Power Monthly Table 5.6.A, Jul 2026 | 🔄 Jul 2026 |
| MA Rate Premium Over National Average — Historical | EIA, annual residential average rates | 🔄 |
| MA Electricity Bill Breakdown (Typical Residential) | Eversource/National Grid rate schedules; DPU filings | — |
| MA vs. National Rate Gap Over Time | EIA Electric Power Monthly | 🔄 |
| Annual Impact Per Household | EIA Jun 2026, bill text analysis | Jun 2026 |
| Where the "Savings" Actually Come From | Bill sections analyzed against verified Eversource rate breakdown | — |
| State Comparison — Monthly Bill at 600 kWh | EIA Jun 2026 rates × 600 kWh/month | 🔄 Jun 2026 |
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

### Headline figures

The rows above document the charts. These are the summary cards, which the page
displays without a source line of their own.

Attribution here is to the **publisher**, not to a file. The specific documents
these were read from are not retained, and the page’s own `Source:` lines belong
to its charts rather than to these cards — borrowing one by proximity credited
Massachusetts SERS headcounts to a national average, so it was not used. Naming
the body that publishes each series is what can be stood behind: the FY2024 ACFR,
the PERAC valuation and the PRIT report are all reachable from the links below,
and a precise citation that might be wrong is worse here than an honest general one.

- Commonwealth ACFR — <https://www.macomptroller.org/annual-comprehensive-financial-reports/>
- PERAC — <https://www.mass.gov/orgs/public-employee-retirement-administration-commission>
- PRIM / PRIT Fund — <https://www.mapension.com/>
- State Retiree Benefits Trust Fund — <https://www.mass.gov/orgs/state-retiree-benefits-trust-fund>

| Figure | Value | Publisher | Vintage |
|--------|-------|-----------|---------|
| SERS (State Employees) — 72.5% funded · $37B assets | $14.1B | PERAC — Public Employee Retirement Administration Commission (mass.gov); Office of the Comptroller, Commonwealth ACFR (macomptroller.org) | FY2024 |
| MTRS (Teachers) — 60.4% funded · $39B assets | $25.5B | PERAC — Public Employee Retirement Administration Commission (mass.gov); Office of the Comptroller, Commonwealth ACFR (macomptroller.org) | FY2024 |
| FY2024 — Pension appropriation | $4.10B | Enacted General Appropriations Acts, mass.gov GAA export | FY2024 |
| FY2025 — +9.6% | $4.50B | Enacted General Appropriations Acts, mass.gov GAA export | FY2025 |
| FY2026 — +9.6% | $4.93B | Enacted General Appropriations Acts, mass.gov GAA export | FY2026 |
| Normal Cost (SERS) — Annual benefit accrual | $463M | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| ARC % of Payroll — Up from 7.4% in 2001 | 18.3% | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Total PRIT Assets — FY2024 (June 30, 2024) | $105.3B | PRIM / PRIT Fund (mapension.com) | FY2024 |
| Net Income — 5 of 7 asset classes beat benchmarks | $9.1B | PRIM / PRIT Fund (mapension.com) | FY2024 |
| 5-Year Return — vs. 7.0% assumed | 9.17% | PRIM / PRIT Fund (mapension.com) | FY2024 |
| 10-Year Return — Beating 7% target | 8.33% | PRIM / PRIT Fund (mapension.com) | FY2024 |
| Since Inception — 40-year annualized (1985–2024) | 9.36% | PRIM / PRIT Fund (mapension.com) | 1985–2024 |
| FY2025 Budget — 52.6 bps of AUM | $559M | PRIM / PRIT Fund (mapension.com) | FY2025 |
| FY2026 Budget — 52.2 bps of projected $116B | $604M | PRIM / PRIT Fund (mapension.com) | FY2026 |
| External Managers — Private firms managing public money | 175+ | PRIM / PRIT Fund (mapension.com) | FY2024 |
| Active Workers (SERS) — Contributing members | 90,988 | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Retirees & Beneficiaries — Collecting benefits | 69,750 | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Total Membership — Including inactive vested | 197,928 | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| FY2024 Cash Flow — More paid out than taken in | -$764M | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Municipal Unfunded — 99 systems (FY2023) | $15.2B | PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2023 |
| All 105 Systems — State + municipal | $43.4B | PERAC — Public Employee Retirement Administration Commission (mass.gov) | January 2025 |
| Median Funded Ratio — Up from 73.6% | 75.3% | PERAC — Public Employee Retirement Administration Commission (mass.gov) | January 2025 |
| Legal Deadline — G.L. c. 32, §22F | FY2040 | G.L. c. 32, §22F | statute |
| State OPEB Liability — Total promised | $16.2B | State Retiree Benefits Trust Fund (mass.gov); PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Statewide Total — All entities combined | $56.1B | State Retiree Benefits Trust Fund (mass.gov); PERAC — Public Employee Retirement Administration Commission (mass.gov) | FY2024 |
| Bonded Debt — GO + special obligation | $48.0B | Office of the Comptroller, Commonwealth ACFR (macomptroller.org) | FY2024 |
| Net Deficit — Liabilities − assets | -$60.2B | Office of the Comptroller, Commonwealth ACFR (macomptroller.org) | FY2024 |
| Unfunded liability per household | $40,599 | Office of the Comptroller, Commonwealth ACFR (macomptroller.org) | FY2024 |

---

## 💵 Lobbying & Political Spending

Figures on `pay-to-play-dashboard.html`. Three authorities: OpenSecrets for sector and multi-year firm totals, the Secretary of the Commonwealth’s Lobbyist Public Search for single-year firm filings, and the state’s own OCPF database for individual donations.

The SOS figures are the only ones here backed by a file in `data/`. They cannot be fetched by a workflow — the SOS blocks server-side requests — so they are collected from a browser session with `The-Peoples-Audit/userscripts/sos-lobbyist-detail-scraper.user.js` and land in `data/ma-lobbying-firms-latest.json`. `scripts/check-consistency.py` holds the dashboard to that file, and `scripts/check-freshness.py` ages it at 400 days. Everything else in this section is maintained by hand.

**Registration year 2026 — first-half filings.** MA lobbying disclosure is semi-annual (due Jul 15 and
Jan 15), so these cover roughly January to June and are **not** comparable to the full-year totals for
2016–2025. Collected 2026-09-27.

| Channel | Reported |
|---|---|
| Clients → lobbying firms | $45,864,365 |
| Clients → their own in-house lobbyists | $10,798,366 |
| Client expenses | $5,891,460 |
| **Total client outlay** | **$62,554,191** |

Both flows reconcile to the cent against the other side of the ledger: the client→firm total equals what
the 169 firms reported receiving, and the client→lobbyist total equals what the 1,528 individual
lobbyists reported receiving. 1,733 clients filed. For reference, registration year 2025 — a full year —
had 175 entities receiving $88,409,949.

### Joining these files

**Within a registration year, join on `sysvalue`.** Names drift even inside one year — the SOS
renormalised “Smith, Costello & Crawford” (2025) to “Smith Costello & Crawford” (2026), and some
client names carry double spaces in the industry results but not on their own pages.

**Across years, `sysvalue` does not work at all.** It is year-scoped: every 2025 key begins
`hvS0w46oEfUey9UWwnkaG…` and every 2026 key `j980aMf4IpOwXPZWPGG1x…`. The overlap between the two
years is **zero** — for clients and for firms. An earlier version of this file said “join on sysvalue,
not on name” without that qualification, which would lead anyone comparing years to conclude that all
1,697 clients left and 1,733 different ones arrived.

Year-over-year therefore has to match on **normalised names** (lowercase, punctuation and corporate
suffixes stripped, whitespace collapsed), which resolves 1,454 of 1,733 clients. The remainder are a
mix of genuine entries and exits and of names that moved too far to match, so treat churn counts as
approximate and spend comparisons on matched names as sound.

**Industry labels are the state’s, not ours.** The SOS’s Industry Type register assigns every client one
of 36 labels at registration; 35 are in use (“Other” is empty). Joined on `sysvalue` it covers
**1,733 of 1,733 clients**. A name-keyword classifier managed 46.4%, which is why nothing inferred is
published here.

The single “Healthcare” line understates health, because the SOS splits it four ways:

| Label | 2026 H1 spend |
|---|---|
| Healthcare | $9,080,168 |
| Pharmaceutical Industry | $2,830,428 |
| Insurance: Medical, Dental, Mental Health | $2,142,124 |
| Hospitals: Healthcare Systems, Medical Orgs | $1,685,757 |
| **Health, rolled up** | **$15,738,477 — 25.2%** |

That 25.2% independently matches OpenSecrets’ 25% for the health sector over 2015–2025 — a different
source, method and window — and it holds across a second full scrape:

| | 2025 (full year) | 2026 (first half) |
|---|---|---|
| Clients filing | 1,697 | 1,733 |
| Matched to an SOS label | 100% | 100% |
| Total client outlay | $119,177,253 | $62,554,191 |
| Health share | **24.48%** | **25.16%** |

The totals are not comparable — one is a year, the other half of one. The shares are.

### A scrape is a snapshot, not a final figure

The 2025 firm file, scraped 2026-05-28, says firms received $88,409,948.93. The client file scraped
2026-09-27 says clients paid them $88,602,703.93 — **$192,755.00 more, 0.218%**. It decomposes exactly:

| | pairs | value |
|---|---|---|
| Amended amounts | 5 | $130,500.00 |
| Relationships the May scrape never saw | 3 | $62,255.00 |
| **Net** | **8** | **$192,755.00** |

**Four of the five amendments are exactly double** the earlier figure — first-half filings that later
gained their second half. The series above uses the amended $88.6M for 2025 and keeps the scrape-time
figure alongside it as `received_at_scrape`.

This matters for the 2026 numbers too. They reconcile to the cent because both sides were scraped the
same day. That is a same-day property, not a permanent one; expect 2026 to drift upward as amendments
land, exactly as 2025 did.

| Figure | Source | Updated |
|--------|--------|---------|
| Lobbying Spending by Sector — $457M Total (2015–2025) | OpenSecrets, Massachusetts State Lobbying Ranked Sectors (2015–2025) | 2015–2025 |
| Top 10 Industries by Lobbying Spend (2015–2025) | OpenSecrets, Massachusetts State Lobbying by Industry (2015–2025) | 2015–2025 |
| Spending by Industry — 2026, State’s Own Labels ✅ | Secretary of the Commonwealth, Lobbyist Public Search — Industry Type; `data/ma-lobbying-firms-latest.json` | 2026 H1 |
| Health share, 2025 full year — 24.48% of $119,177,253 ✅ | Secretary of the Commonwealth, Lobbyist Public Search — Industry Type | 2025 |
| Health rolled up across 4 SOS labels — $15,738,477, 25.2% ✅ | Secretary of the Commonwealth, Lobbyist Public Search — Industry Type | 2026 H1 |
| **Hero: total lobbying spend, 2025** — $119.2M ✅ | Secretary of the Commonwealth, Lobbyist Public Search — client filings: $88,602,704 to firms + $20,888,628 to in-house lobbyists + $9,685,922 expenses = $119,177,253 | 2025 |
| **Hero: lobbyists per lawmaker** — 8:1 ✅ | Secretary of the Commonwealth registrant index: 1,555 registered lobbyists ÷ 200 legislators (160 House + 40 Senate) = 7.78 | 2025 |
| Top Spenders — 2026 First-Half Filings ✅ | Secretary of the Commonwealth, Lobbyist Public Search — `data/ma-lobbying-firms-latest.json`; client-reported fees, in-house salaries and expenses | 2026 H1 |
| Top 10 Firms by 2026 Fees — State Filings ✅ | Secretary of the Commonwealth, Lobbyist Public Search — `data/ma-lobbying-firms-latest.json` | 2025 |
| A Decade of Lobbying Fees (2016–2026) ✅ | Secretary of the Commonwealth, Lobbyist Public Search — annual entity totals | 2016–2025 |
| Smith Costello & Crawford Public Policy Group, LLC — 2026 H1 fees $4.4M, 143 clients ✅ | Secretary of the Commonwealth, Lobbyist Public Search | 2026 H1 |
| Tremont Strategies Group LLC — 2026 H1 fees $3.4M, 112 clients ✅ | Secretary of the Commonwealth, Lobbyist Public Search | 2026 H1 |
| O'Neill and Partners LLC. — 2026 H1 fees $2.7M, 88 clients ✅ | Secretary of the Commonwealth, Lobbyist Public Search | 2026 H1 |
| Dempsey Associates LLC — 2026 H1 fees $2.3M, 62 clients ✅ | Secretary of the Commonwealth, Lobbyist Public Search | 2026 H1 |
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
## ⚖️ Corporate Penalties & Political Money

Figures on `corporate-ledger.html` and `corporate-ledger-method.html`. The page lists companies with at least $1 million in government penalties dated July 2009 (fiscal 2010) or later and a Massachusetts tie, and sets each beside what the state paid it, what its employees gave to Massachusetts candidates, what it paid to lobby and what officials disclosed about it. Every row links to the document it came from. The data files in `data/corporate-ledger/` are built in a separate research project and copied here; no workflow refreshes them. Counting rules (cash actually paid; a payment listed twice counts once; a total shared with people outside the company counts for no company) and everything left out are stated on the page and in the method notes.

| Figure | Source | Updated |
|--------|--------|---------|
| Penalty amounts, dates and agencies | The issuing agency's own release or order, linked on each row: Massachusetts Attorney General, U.S. Attorneys and the Justice Department, SEC, EPA ECHO, Department of Labor and others. Criminal rows from the Corporate Prosecution Registry are checked against Justice Department releases and corrected where they differ | 🔒 a methodology statement describing a rule, not a quantity. |
| Which companies are included | At least $1 million in penalties since July 2009 and conduct in Massachusetts or a headquarters here at the time; each headquarters is sourced in the research project's company list | 🔒 a methodology statement describing a rule, not a quantity. |
| State payments to each company | CTHRU (the Comptroller's spending records), plus the MBTA, Massport and the School Building Authority from their own payment records. Net payments by fiscal year, FY2010 to date; only vendor names confirmed as the company count | 2026-10-12 |
| Employee donations | OCPF state bulk files and FEC individual-contribution files, matched by the donor's reported employer. Only confirmed matches count; memo entries, pass-throughs, refunds and in-kind gifts are left out. Street and ZIP are not shown | 2026-10-10 |
| Lobbying | Secretary of the Commonwealth lobbyist disclosures: firm fees from 2010, in-house costs for 2025 and 2026 only | 2026-10-11 |
| Officials' disclosed ties | Statements of Financial Interest, filings for 2019 to 2025. A tie carries no amount and is not a payment | 2026-10-10 |
| Amounts not counted | The register on the page's Amounts not counted tab: each headline figure that was not cash paid, with the document it comes from | 🔒 a methodology statement describing a rule, not a quantity. |

---
## 📌 Headline figures no workflow owns

Every figure here is printed in a headline card on a dashboard, carries a source
on the page, and is **maintained by hand** — no updater writes it, and none can
without new plumbing. They are recorded here so `check-stats-documented.py` can
account for them and so a reader can follow each one to its publisher.

**Read the date column as "when the page says it was checked", not "verified
today".** These were transcribed from the published pages on 2026-10-20 with the
sources those pages cite; they were **not** independently re-fetched from IRS,
DLS, OCPF, RGGI or CBP in the process. That is why none of them carries the ✅
hand-verified mark. The pages' own `data-checked` stamps are what age them, and
`check-freshness.py` already registers those stamps.

Anything in this table that acquires a feed should move out of it into the
section for that feed, and lose its row here.

### Tax & budget — `tax-budget-dashboard.html` (page checked 2026-07-01)

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| Income tax competitiveness rank | #42 (9th worst) | 2026 index | Tax Foundation State Tax Competitiveness Index — their index, cited as theirs |
| Debt service, annual | $2.24B | FY2026 | mass.gov GAA export, appropriation line 0699-0015 |
| Total statewide property levy | $24.0B | FY2026 | MA DLS, FY2026 Tax Levies Report |
| Estimated SNAP fraud, actual | $135–225M | FY2023–FY2025 | MA State Auditor BSI reports + USDA-FNS national trafficking rates — an estimate, and a range |
| Net AGI outflow | −$8.2B | CY2020–22 | IRS SOI state-to-state migration ($4.3B + $3.9B) |
| Top 1% share of federal income tax paid by MA filers | 38.2% | TY2022 | IRS SOI In-State AGI Shares |
| Top 5% share of federal income tax paid by MA filers | 58.8% | TY2022 | IRS SOI In-State AGI Shares |
| Bottom 50% share of federal income tax paid by MA filers | 3.9% | TY2022 | IRS SOI In-State AGI Shares |
| Top 1% share of all capital gains | 76.0% | TY2022 | IRS SOI In-State AGI Shares |

The four IRS SOI shares are one release and move together. If one is updated and
the others are not, the page will contradict itself — update the set or none of
it. IRS SOI publishes state AGI-share data annually and well behind the tax year,
so TY2022 being the newest is the source's cadence, not neglect.

### Energy — `energy-dashboard.html`

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| RGGI carbon-auction cost to MA ratepayers, cumulative | $1.36B | since 2008 | RGGI Inc. auction results |

Cumulative, so it grows with every quarterly auction — the one figure in this
table that goes stale on a known schedule rather than annually.

### Pay to play — `pay-to-play-dashboard.html` (page checked 2026-02-01)

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| Donations at exactly the $200 reporting threshold | 82.3% | — | OCPF filings |
| Donations from three firms alone | $822K | — | OCPF filings |
| Health sector lobbying, #1 | $112.7M | — | Secretary of the Commonwealth lobbying disclosure |
| Finance / insurance / real estate lobbying, #2 | $74.4M | — | Secretary of the Commonwealth lobbying disclosure |
| Energy / natural resources lobbying, #4 | $39.3M | — | Secretary of the Commonwealth lobbying disclosure |

This page has no updater by design: the Secretary of the Commonwealth blocks
server-side fetches, which is the same reason `data/ma-lobbying-firms-latest.json`
is refreshed from a browser session rather than a workflow. The three sector
totals sit beside a `ma-lobbying-firms-latest.json` feed that holds firm-level
figures, not sector rollups, so they are not the same numbers and must not be
cross-checked against each other.

### Immigration — `immigration-dashboard.html`

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| CBP encounters recorded in Massachusetts | 2,836 | FY2026, Oct–Jul | CBP Nationwide Encounters, state breakdown (`nationwide-encounters-fy23-fy26-jul-state.csv`) |
| Single adults as a share of those encounters | 93% | FY2026, Oct–Jul | same file (2,629 of 2,836) |

The Oct–Jul window is deliberate and the page explains why: comparing three full
years against a 10-month FY2026 measured the calendar as much as the trend, and
on equal windows the shape reverses. Keep the window when this updates.

These are the one group here that a workflow could plausibly own. The blocker is
transport, not sourcing: cbp.gov fingerprints the client, so only the self-hosted
runner (`duncanburns2013-dot/ma-data-hub-runner`, which fetches via curl) can
retrieve the file — the same constraint `update-cbp.yml` already lives with.

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
| Corporate Ledger | `corporate-ledger.html` | &mdash; | manual |

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
| 2026-09-30 | **Contradiction fixes, immigration + tax-budget dashboards.** Shelter spending replaced with one CTHRU series (kv7m-35wn) under two stated definitions, shelter system and EA line; two-year and cumulative totals re-derived ($1.85B, $2.42B, $2.78B). HomeBASE $101M → CTHRU $57.3M (FY25) / $91.4M (FY26); HomeBASE-reporting-lapsed claim corrected (SD.4220 carries exits incl. HomeBASE). Caseload 4,800 → 1,533 + 55 (3 Sep 2026). $1.88B estimate relabelled: all shelter families plus modelled CIS costs. BSI program chart relabelled FY25 Q4; BSI trend and cards → annual totals FY22–FY25; Detected column total → $4.66M. SNAP BSI row $0.69M → Q1 FY25 $2,549,325. FY25 gap $6.2B → $5.736B, labelled supplemental spending. Vendor card $142.2M → $46.8M computed from `data/payments.json`. Sources: CTHRU kv7m-35wn, EA report SD.4220, BSI reports SD.2676 / SD.3769 and the FY22–FY25 annual totals, budget.digital.mass.gov FY27 data; retrieved 2026-09-30. | Claude |
| 2026-08-11 | **FY2027 enacted-budget review against the official mass.gov GAA exports.** Diffed all 860 `LINE_ITEMS` in `tax-budget-dashboard.html` against `gaa1.xlsx`: **zero amount mismatches** — the H.5555 conference data the dashboard was built on *is* the enacted law, because Healey signed with no vetoes. Fixed one account-code typo (`8910-0702` → `8910-8702`). Relabelled the tab, headings, sources and the `FY27_H5555` constant (now `FY27_GAA = 63.416`) from "conference report" to enacted GAA, and replaced the stale "heads to Gov. Healey's desk" line. Added the **scope reconciliation table** above — the headline total excludes Intragovernmental Service Spending — plus FY2027 key figures, the enacted-vs-actual supplemental gap (new `h5Outturn` chart), and the local-aid CSV footer-row gotcha. Added the OPEB finding to `pension-dashboard.html`: the SRBT deposit (line 1595-6152) is down 27% since FY24 while the budget creates a pension COLA reserve. Cleared both long-standing defects — CPS/ACS mislabel and the unlabelled $7,732 property tax figure (now $8,113, FY2026). | Claude + Duncan |
| 2026-02-05 | Initial creation — all data compiled from prior chats | Claude + Duncan |
| 2026-08-01 | Refreshed the manual dashboards. Commercial RE → Q2 2026 (C&W Boston 19.0%, US 20.1%; Colliers 23.7%; CBRE 18.7%; Trepp office delinquency 11.57%). Tax & Budget verified already current (FY2027 H.5555 enacted $63.4B, signed 2026-07-09, parsed July 2026). Healthcare held at the 2024 MA/US pair with KFF's 2025 national figure ($26,993) noted, since no MA 2025 comparator is published. Made the CPI badge and immigration hero self-stamping so they can't go stale again. | Claude + Duncan |
| 2026-08-01 | Repo audit. Reconciled this file against the live API feeds it had drifted from: ACS figures → vintage 2024, MA median income $104,800 → $103,960, MLS 5-yr table → `mls-history.json` values, NH → PrimeMLS 2026-08-01, IRS cumulative 86,382/$12.1B → 184,719/$24.7B (matching the live dashboard). Split the trailing-12-month window out from calendar 2025, recorded the CBP FY2025 methodology break and the BLS state-JOLTS discontinuation, corrected the dashboard registry. Marked API-fed rows 🔄. | Claude + Duncan |

---

*To update: Edit this file directly on GitHub, or tell Claude "update MASTER_DATA.md with [new figures]"*
