# Massachusetts Data Hub

Interactive dashboards and data analysis covering housing, immigration, education, healthcare, and affordability across the Commonwealth.

**Live Site:** https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/

---

## 📊 Dashboards

| Dashboard | Topic | Status | Sources |
|-----------|-------|--------|---------|
| [Immigration](immigration/index.html) | Border encounters, NIM, fiscal impact, MA shelter crisis | ✅ Live | CBP, Census, ICE, CBO, Cato/NASEM |
| [MA Housing](housing/ma-dashboard.html) | Statewide, Boston, Essex County, Newburyport | ✅ Live | Warren Group, MLS PIN |
| [NH Housing](housing/nh-dashboard.html) | NH statewide with regional breakdowns | ✅ Live | Paragon MLS |
| [Haverhill Report](housing/haverhill-report.html) | SF/Condo affordability deep dive | ✅ Live | MLS, Census QuickFacts |
| [Affordability](affordability/dashboard.html) | CPI, wages, housing, exodus data | ✅ Live | BLS, IRS SOI, BU Study |
| [Education (State)](education/index.html) | Enrollment shifts, spending, MCAS | ✅ Live | DESE, MCAS |
| [Education (Boston)](education/boston-dashboard.html) | BPS absenteeism, gaps, demographics | ✅ Live | DESE, BPS |
| [Education (MV)](education/merrimack-valley.html) | Haverhill/Methuen/Lawrence comparison | ✅ Live | DESE, MassINC |
| [Healthcare](healthcare/index.html) | Insurance rates, premiums, MA vs national | 🟡 Planned | DOI, KFF, CHIA |
| [Employment](employment/index.html) | JOLTS, NFP revisions, hiring recession | 🟡 Planned | BLS JOLTS, CES |
| [Commercial RE](commercial/index.html) | Boston office vacancy, CMBS, property tax | 🟡 Planned | Trepp, C&W, Colliers |

## 📁 Repository Structure

```
Massachusetts-Data-Hub/
├── index.html              ← Landing page (links to all dashboards)
├── template.html           ← Reusable dashboard shell
├── MASTER_DATA.md          ← All verified data points
├── README.md               ← This file
├── immigration/
│   └── index.html
├── housing/
│   ├── ma-dashboard.html
│   ├── nh-dashboard.html
│   └── haverhill-report.html
├── education/
│   ├── index.html
│   ├── boston-dashboard.html
│   └── merrimack-valley.html
├── affordability/
│   └── dashboard.html
├── healthcare/
│   └── index.html          (planned)
├── employment/
│   └── index.html          (planned)
└── commercial/
    └── index.html          (planned)
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
