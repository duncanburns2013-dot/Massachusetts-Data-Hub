# Massachusetts Data Hub

Interactive dashboards and data analysis covering housing, immigration, education, healthcare, and affordability across the Commonwealth.

**Live Site:** https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/

---

## 📊 Dashboards

| Dashboard | Topic | Status | Sources |
|-----------|-------|--------|---------|
| [**Worst Policies**](worst-policies-dashboard.html) | Ranked inventory of the 25 costliest MA policies, cross-referenced across 29 repos | ✅ Live | All repos below + statutes, roll calls |
| [Immigration](immigration-dashboard.html) | Border encounters, NIM, fiscal impact, MA shelter crisis | ✅ Live | CBP, Census, ICE, CBO, Cato/NASEM |
| [MA Housing](ma-housing-dashboard.html) | Statewide, Boston, Essex County, Newburyport | ✅ Live | Warren Group, MLS PIN |
| [NH Housing](nh-housing-dashboard.html) | NH statewide with regional breakdowns | ✅ Live | Paragon MLS |
| [Haverhill Report](haverhill-market-report.html) | SF/Condo affordability deep dive | ✅ Live | MLS, Census QuickFacts |
| [Affordability](affordability-dashboard.html) | CPI, wages, housing, exodus data | ✅ Live | BLS, IRS SOI, BU Study |
| [Education (State)](education-statewide.html) | Enrollment shifts, spending, MCAS | ✅ Live | DESE, MCAS |
| [Education (Boston)](education-boston.html) | BPS absenteeism, gaps, demographics | ✅ Live | DESE, BPS |
| [Education (MV)](education-merrimack-valley.html) | Haverhill/Methuen/Lawrence comparison | ✅ Live | DESE, MassINC |
| [Healthcare](healthcare-dashboard.html) | Insurance rates, premiums, MA vs national | 🟡 Planned | DOI, KFF, CHIA |
| [Employment](employment-dashboard.html) | JOLTS, NFP revisions, hiring recession | 🟡 Planned | BLS JOLTS, CES |
| [Commercial RE](commercial-re-dashboard.html) | Boston office vacancy, CMBS, property tax | 🟡 Planned | Trepp, C&W, Colliers |

## 📁 Repository Structure

```
Massachusetts-Data-Hub/
├── index.html                          ← Landing page
├── template.html                       ← Reusable dashboard shell
├── MASTER_DATA.md                      ← All verified data points
├── README.md
├── worst-policies-dashboard.html       ← Ranked policy inventory (cross-repo synthesis)
├── immigration-dashboard.html          ← National + MA immigration
├── ma-housing-dashboard.html           ← MA housing market
├── nh-housing-dashboard.html           ← NH housing market
├── haverhill-market-report.html        ← Haverhill deep dive
├── affordability-dashboard.html        ← Master affordability & employment
├── education-statewide.html            ← MA education statewide
├── education-boston.html                ← Boston Public Schools
├── education-merrimack-valley.html     ← Haverhill/Methuen/Lawrence
├── healthcare-dashboard.html           ← Insurance & premiums (planned)
├── employment-dashboard.html           ← JOLTS & labor market (planned)
└── commercial-re-dashboard.html        ← Boston office/CMBS (planned)
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

## 🔗 Research Repository Network

The [Worst Policies dashboard](worst-policies-dashboard.html) is a synthesis across the wider research network. Repos that feed ranked entries:

| Repo | Feeds |
|------|-------|
| [Mass-Fiscal-Energy-Legislation](https://github.com/duncanburns2013-dot/Mass-Fiscal-Energy-Legislation) | H.5151 section-by-section, $9B claim vs. ~$150/yr reality |
| [ma-electricity-analysis](https://github.com/duncanburns2013-dot/ma-electricity-analysis) | Rate trajectory 2014–2025, policy charge itemization, third-party supplier $525M |
| [MBTA-Communities-Act](https://github.com/duncanburns2013-dot/MBTA-Communities-Act) | § 3A: 273,080 units, $4.49B DCAMM fees vs. $15M appropriated |
| [MBTA-Scam](https://github.com/duncanburns2013-dot/MBTA-Scam) | Big Dig debt transfer, 52.6% pension funding, 10-point reform |
| [The-Peoples-Audit](https://github.com/duncanburns2013-dot/The-Peoples-Audit) | Question 1 (71.8%), SJC complaint, 29,729 SFI filings |
| [The-25K-Problem](https://github.com/duncanburns2013-dot/The-25K-Problem) | Subsidy incidence by Zillow price tier, day-one negative equity |
| [Housing-Affordability-Crisis](https://github.com/duncanburns2013-dot/Housing-Affordability-Crisis) | CTHRU: demand-side spending 46× vs. flat supply-side |
| [MA-Housing-Affordability-Issues](https://github.com/duncanburns2013-dot/MA-Housing-Affordability-Issues) | 222,000-unit deficit, Chapter 40B's 70K in 50 years |
| [MA-2027-Budget-Analysis](https://github.com/duncanburns2013-dot/MA-2027-Budget-Analysis) | FY25/26/27 line-item parse, per-household burden |
| [Massachusetts-Disaster](https://github.com/duncanburns2013-dot/Massachusetts-Disaster) | $107.6B liability inventory, 10-year net position series |
| [The-Invasion](https://github.com/duncanburns2013-dot/The-Invasion) | $1.88B FY25 immigrant services audit, vendor detail |
| [fraud-detection](https://github.com/duncanburns2013-dot/fraud-detection) | BSI detection rates, 0.07% coverage, verification gaps |
| [HHS-MA-DOGE](https://github.com/duncanburns2013-dot/HHS-MA-DOGE) | Medicaid money circuit, union PACs, no-bid contracts |
| [Pay-To-Play-Massachusetts-Non-Profits](https://github.com/duncanburns2013-dot/Pay-To-Play-Massachusetts-Non-Profits) | $39M hospital lobbying, CEO-as-lobbyist registrations |
| [MA-Health-Insurance](https://github.com/duncanburns2013-dot/MA-Health-Insurance) | THCE growth 8.6% vs. 3.6% benchmark |
| [All-Things-Boston](https://github.com/duncanburns2013-dot/All-Things-Boston) | Boston DEI vs. Veterans/BPD, 311 equity gap, Boston OPEB |
| [H1B](https://github.com/duncanburns2013-dot/H1B) | 844,054 USCIS filings, MA Level-I wage share |
| [MA-v-NH](https://github.com/duncanburns2013-dot/MA-v-NH) | Federal-data-only comparison, MCAS repeal, BEA RPP correction |
| [CoH](https://github.com/duncanburns2013-dot/CoH) | Haverhill property tax +31% vs. +17.2% cost of living |

Context repos that inform the analysis without feeding a ranked entry: [Maura-Healey-Year-3-](https://github.com/duncanburns2013-dot/Maura-Healey-Year-3-), [wealth-inequality](https://github.com/duncanburns2013-dot/wealth-inequality), [Boston-ICE](https://github.com/duncanburns2013-dot/Boston-ICE).

## 📄 Migration from Old Repos

Dashboards are being migrated from these repos:
- `duncanburns2013-dot/Immigration`
- `duncanburns2013-dot/Housing-Market-Data`
- `duncanburns2013-dot/Master-Massachusetts-Affordability-Employment-`
- `duncanburns2013-dot/Merrimac-Valley-Education-`

Old repos will remain active until migration is complete.

---

*Data compiled February 2026 · All data from official government sources*
