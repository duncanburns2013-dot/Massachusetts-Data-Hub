# Massachusetts Data Hub

Interactive dashboards and data analysis covering housing, immigration, education, healthcare, and affordability across the Commonwealth.

**Live Site:** https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/

---

## 📊 Dashboards

"Auto" means a GitHub Actions workflow refreshes the figures on a schedule; "manual" means
the numbers are hand-maintained and only change when someone edits the page.

| Dashboard | Topic | Status | Refresh | Sources |
|-----------|-------|--------|---------|---------|
| [Immigration](immigration-dashboard.html) | Border encounters, NIM, fiscal impact, MA shelter crisis | ✅ Live | Auto — monthly | CBP, Census, ICE, CBO, Cato/NASEM |
| [MA Housing](ma-housing-dashboard.html) | Statewide, Boston, Essex County, Newburyport | ✅ Live | Auto — daily | Warren Group, MLS PIN |
| [NH Housing](nh-housing-dashboard.html) | NH statewide with regional breakdowns | ✅ Live | Auto — daily | PrimeMLS |
| [Haverhill Report](haverhill-market-report.html) | SF/Condo affordability deep dive | ✅ Live | Auto — daily | MLS PIN, Census |
| [Affordability](affordability-dashboard.html) | CPI, wages, housing, exodus data | ✅ Live | Auto — monthly | BLS, IRS SOI, BU Study |
| [Education (State)](education-statewide.html) | Enrollment shifts, spending, MCAS | ✅ Live | Manual | DESE, MCAS |
| [Education (Boston)](education-boston.html) | BPS absenteeism, gaps, demographics | ✅ Live | Manual | DESE, BPS |
| [Education (MV)](education-merrimack-valley.html) | Haverhill/Methuen/Lawrence comparison | ✅ Live | Manual | DESE, MassINC |
| [Healthcare](healthcare-dashboard.html) | Insurance rates, premiums, MA vs national | ✅ Live | Manual | DOI, KFF, CHIA |
| [Employment](employment-dashboard.html) | JOLTS, NFP revisions, hiring recession | ✅ Live | Auto — monthly | BLS JOLTS, CES |
| [Commercial RE](commercial-re-dashboard.html) | Boston office vacancy, CMBS, property tax | ✅ Live | Manual | Trepp, C&W, Colliers |
| [Energy](energy-dashboard.html) | Electricity rates, utility costs | ✅ Live | Auto — monthly | EIA, DPU |
| [Tax & Budget](tax-budget-dashboard.html) | State budget, IRS SOI migration, tax burden | ✅ Live | Auto — monthly | IRS SOI, MA Comptroller |
| [Pension](pension-dashboard.html) | Public pension liabilities and funding | ✅ Live | Manual | PERAC |
| [Pay to Play](pay-to-play-dashboard.html) | MA non-profit contracting and contributions | ✅ Live | Manual | OCPF, state contracts |

## 📁 Repository Structure

```
Massachusetts-Data-Hub/
├── index.html                          ← Landing page
├── template.html                       ← Reusable dashboard shell (placeholder figures — not live data)
├── MASTER_DATA.md                      ← Hand-verified reference; API feeds live in data/
├── README.md
│
├── immigration-dashboard.html          ← National + MA immigration
├── ma-housing-dashboard.html           ← MA housing market
├── nh-housing-dashboard.html           ← NH housing market
├── haverhill-market-report.html        ← Haverhill deep dive
├── affordability-dashboard.html        ← Master affordability & employment
├── education-statewide.html            ← MA education statewide
├── education-boston.html               ← Boston Public Schools
├── education-merrimack-valley.html     ← Haverhill/Methuen/Lawrence
├── healthcare-dashboard.html           ← Insurance & premiums
├── employment-dashboard.html           ← JOLTS & labor market
├── commercial-re-dashboard.html        ← Boston office/CMBS
├── energy-dashboard.html               ← Electricity & utility rates
├── tax-budget-dashboard.html           ← State budget & IRS SOI migration
├── pension-dashboard.html              ← Public pension liabilities
├── pay-to-play-dashboard.html          ← Non-profit contracting
│
├── data/                               ← Fetched API snapshots (source of truth)
│   ├── mls-history.json                ← MLS PIN closed sales by calendar year
│   ├── nh-figures.json                 ← PrimeMLS NH markets
│   ├── census-latest.json              ← ACS 5-year estimates
│   ├── employment-latest.json          ← BLS LAUS/CES/JOLTS
│   ├── cbp-encounters-latest.json      ← CBP southwest border
│   ├── irs-soi-migration-latest.json   ← IRS state-to-state migration
│   └── ...
│
└── .github/workflows/                  ← One workflow per feed + Pages deploy
```

### Which numbers update themselves

Most dashboards do **not** fetch JSON at runtime — the updater scripts rewrite the figures
into the HTML and commit. Only `nh-housing-dashboard.html`, `ma-housing-dashboard.html` and
`haverhill-market-report.html` read from `data/` in the browser. So a stale dashboard means
a workflow stopped committing, not a broken fetch — check the Actions tab first.

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

Dashboards were migrated from these repos, which still serve older standalone copies:
- `duncanburns2013-dot/Immigration`
- `duncanburns2013-dot/Housing-Market-Data`
- `duncanburns2013-dot/Master-Massachusetts-Affordability-Employment-`
- `duncanburns2013-dot/Merrimac-Valley-Education-`

This repo is the current one. The old copies are not refreshed and will drift.

---

*Automated feeds refresh on the schedules above · All data from official government sources*
