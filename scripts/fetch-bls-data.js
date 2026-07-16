import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_PATH    = path.join(__dirname, '..', 'employment-dashboard.html');
const DATA_OUTPUT_PATH  = path.join(__dirname, '..', 'data', 'employment-latest.json');
const DATA_PREV_PATH    = path.join(__dirname, '..', 'data', 'employment-previous.json');

// ── Series IDs ────────────────────────────────────────────────────────────────
const EMPLOYMENT_SERIES = {
  MA_UNEMPLOYMENT_RATE:  'LASST250000000000003',
  MA_UNEMPLOYMENT_LEVEL: 'LASST250000000000004',
  MA_LABOR_FORCE:        'LASST250000000000006',
  MA_TOTAL_NONFARM:      'SMS25000000000000001',
  US_UNEMPLOYMENT_RATE:  'LNS14000000',
  // National (Employment Situation) — releases ~3 weeks before the MA state data,
  // so these carry the newest month and drive the "National" block + table.
  US_NONFARM:            'CES0000000001',  // total nonfarm, SA, level (thousands)
  US_HH_EMP:             'LNS12000000',    // household-survey employed, level (thousands)
  US_LABOR_FORCE:        'LNS11000000',    // civilian labor force, level (thousands)
  US_U6:                 'LNS13327709',    // U-6 underemployment rate
  US_UNEMPLOYMENT_LEVEL: 'LNS13000000',    // unemployed, level (thousands) — denominator
                                           // for the JOLTS openings-per-unemployed ratio.
                                           // Must be national and in thousands to match
                                           // JTS...JOL, which is also national thousands.
};

// National JOLTS only — BLS discontinued monthly state JOLTS (last: Dec 2025).
// First annual state JOLTS release: July 2026.
const JOLTS_SERIES = {
  US_JOB_OPENINGS: 'JTS000000000000000JOL',
};

// Foreign-born / native-born (CPS Table A-7). NOT seasonally adjusted — these
// drive the Foreign-Born vs Native tab. Series verified vs the published A-7.
const NATIVITY_SERIES = {
  FB_EMP:    'LNU02073395',  // foreign-born employed (thousands)
  NB_EMP:    'LNU02073413',  // native-born employed (thousands)
  FB_LFPR_T: 'LNU01373395', FB_LFPR_M: 'LNU01373396', FB_LFPR_W: 'LNU01373397',
  NB_LFPR_T: 'LNU01373413', NB_LFPR_M: 'LNU01373414', NB_LFPR_W: 'LNU01373415',
};

// Gender / race / education (CPS, seasonally adjusted). Drives the
// "Men, Women & White-Collar" tab. Race×sex is national-only (state CPS
// samples can't split it monthly). "White" per BLS includes Hispanic-white.
const GENDER_RACE_SERIES = {
  UR_ALL:         'LNS14000000',  // unemployment rate, 16+ (national benchmark)
  UR_MEN:         'LNS14000001',  // men 16+
  UR_WOMEN:       'LNS14000002',  // women 16+
  UR_WHITEMEN:    'LNS14000028',  // White men 20+
  UR_WHITEWOMEN:  'LNS14000029',  // White women 20+
  UR_BLACK:       'LNS14000006',  // Black or African American 16+
  UR_HISP:        'LNS14000009',  // Hispanic or Latino 16+
  LFPR_MEN2554:   'LNS11300061',  // prime-age men participation
  LFPR_WOMEN2554: 'LNS11300062',  // prime-age women participation
  UR_COLLEGE:     'LNS14027662',  // bachelor's degree & higher, 25+
  UR_SOMECOLL:    'LNS14027689',  // some college / associate, 25+
  UR_HS:          'LNS14027659',  // high school, no college, 25+
};

// Massachusetts industry employment (BLS CES, state, SA, level in thousands).
// Full supersector spectrum — drives both the white-collar/tech block and the
// full By-Sector breakdown. Fetched from 2019 so charts can index to Jan-2022
// and compare to the Feb-2020 pre-pandemic baseline.
const MA_SECTOR_SERIES = {
  TOTAL:        'SMS25000000000000001', // Total Nonfarm
  CONSTRUCTION: 'SMS25000002000000001', // Construction
  MANUFACTURING:'SMS25000003000000001', // Manufacturing
  TRADE:        'SMS25000004000000001', // Trade, Transportation & Utilities
  INFO:         'SMS25000005000000001', // Information (tech / media)
  FINANCIAL:    'SMS25000005500000001', // Financial Activities
  PROF_BUS:     'SMS25000006000000001', // Professional & Business Services (white-collar)
  EDUC_HEALTH:  'SMS25000006500000001', // Education & Health Services
  LEISURE:      'SMS25000007000000001', // Leisure & Hospitality
  OTHER_SVC:    'SMS25000008000000001', // Other Services
  GOVERNMENT:   'SMS25000009000000001', // Government
};

// Display names + fixed order (largest-to-smallest-ish) for the By-Sector views.
const MA_SECTOR_META = [
  ['EDUC_HEALTH',  'Education & Health'],
  ['TRADE',        'Trade/Transport/Util'],
  ['GOVERNMENT',   'Government'],
  ['PROF_BUS',     'Prof & Business'],
  ['LEISURE',      'Leisure & Hospitality'],
  ['MANUFACTURING','Manufacturing'],
  ['FINANCIAL',    'Financial Activities'],
  ['CONSTRUCTION', 'Construction'],
  ['OTHER_SVC',    'Other Services'],
  ['INFO',         'Information (tech)'],
];

const BLS_API_BASE = 'https://api.bls.gov/publicAPI/v2/timeseries/data/';
const API_KEY      = process.env.BLS_API_KEY || '';
const TIMEOUT_MS   = 20000;
const MAX_RETRIES  = 3;
const RETRY_DELAY  = 5000; // 5s base — doubles each attempt

// ── Retry fetch ───────────────────────────────────────────────────────────────
async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchBLSData(seriesIds, startYear, endYear, attempt = 1) {
  const payload = {
    seriesid: seriesIds,
    startyear: String(startYear),
    endyear:   String(endYear),
    calculations: true,
  };
  if (API_KEY) payload.registrationkey = API_KEY;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    console.log(`   Attempt ${attempt}/${MAX_RETRIES} — ${seriesIds.length} series...`);
    const response = await fetch(BLS_API_BASE, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent':   'Massachusetts-Data-Hub/1.0 (https://github.com/duncanburns2013-dot/Massachusetts-Data-Hub; public civic data project)',
      },
      body:    JSON.stringify(payload),
      signal:  controller.signal,
    });
    clearTimeout(timer);

    const data = await response.json();
    if (data.status !== 'REQUEST_SUCCEEDED') {
      throw new Error(`BLS API error: ${data.message?.join(', ')}`);
    }
    return data.Results.series;

  } catch (err) {
    clearTimeout(timer);
    const reason = err.name === 'AbortError'
      ? `timed out after ${TIMEOUT_MS / 1000}s`
      : err.message;

    if (attempt < MAX_RETRIES) {
      const delay = RETRY_DELAY * attempt;
      console.warn(`   ⚠️  Attempt ${attempt} failed (${reason}) — retrying in ${delay / 1000}s...`);
      await sleep(delay);
      return fetchBLSData(seriesIds, startYear, endYear, attempt + 1);
    }
    throw new Error(`BLS API unreachable after ${MAX_RETRIES} attempts: ${reason}`);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getLatestValue(series) {
  if (!series?.data?.length) return null;
  const latest = series.data[0];
  return {
    value:      parseFloat(latest.value),
    year:       latest.year,
    period:     latest.period,
    periodName: latest.periodName,
    date:       `${latest.periodName} ${latest.year}`,
  };
}

async function loadPreviousData() {
  try {
    const raw = await fs.readFile(DATA_PREV_PATH, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// ── Chart-array helpers ─────────────────────────────────────────────────────────
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

// Series → oldest-first list of monthly points. Drops the M13 annual average and
// any month BLS marks unavailable (value "-", e.g. the 2025 appropriations lapse),
// so chart lines stay continuous instead of breaking on a fabricated NaN.
// Map a series to { "2026-M05": 7307, ... } so a value can be pulled for a specific
// month rather than just the newest one. Needed wherever two series are combined:
// they publish on different schedules, so "latest of each" can silently straddle
// two different months.
function periodMap(series) {
  const out = {};
  (series?.data || []).forEach(d => {
    const v = parseFloat(d.value);
    if (!Number.isNaN(v)) out[`${d.year}-${d.period}`] = v;
  });
  return out;
}

function monthsOf(series) {
  if (!series?.data?.length) return [];
  return series.data
    .filter(d => /^M(0[1-9]|1[0-2])$/.test(d.period))
    .map(d => ({
      year:  parseInt(d.year, 10),
      mon:   parseInt(d.period.slice(1), 10) - 1,
      value: parseFloat(d.value),
    }))
    .filter(p => Number.isFinite(p.value))
    .reverse();
}

const mkey = p => p.year * 100 + p.mon;

// Chart.js label literal: "'Mon YY'" at year-starts/endpoints, "'Mon'" otherwise.
function axisLabels(axis) {
  return axis
    .map((p, i) =>
      (p.mon === 0 || i === 0 || i === axis.length - 1)
        ? `'${MON[p.mon]} ${String(p.year).slice(2)}'`
        : `'${MON[p.mon]}'`)
    .join(',');
}

// Replace the contents between /*@tag*/ … /*@*/ markers; no-op (with a warning) if absent.
function inject(html, tag, literal) {
  const re = new RegExp(`(/\\*@${tag}\\*/)[\\s\\S]*?(/\\*@\\*/)`);
  if (!re.test(html)) {
    console.warn(`   ⚠️  chart marker @${tag} not found — skipping`);
    return html;
  }
  return html.replace(re, `$1${literal}$2`);
}

// Build every auto-chart literal from the fetched series, then inject into the HTML.
function updateCharts(html, find) {
  const maUR  = monthsOf(find(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_RATE));
  const natUR = monthsOf(find(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_RATE));
  const maLF  = monthsOf(find(EMPLOYMENT_SERIES.MA_LABOR_FORCE));
  const maNF  = monthsOf(find(EMPLOYMENT_SERIES.MA_TOTAL_NONFARM));

  // c-trend — MA unemployment rate, trailing 16 months
  if (maUR.length) {
    const w = maUR.slice(-16);
    html = inject(html, 'trend-lab', axisLabels(w));
    html = inject(html, 'trend-ma',  w.map(p => p.value).join(','));
  }

  // c-laborforce — MA labor force level, trailing 16 months (last point is highlighted)
  if (maLF.length) {
    const w = maLF.slice(-16);
    html = inject(html, 'lf-lab',  axisLabels(w));
    html = inject(html, 'lf-data', w.map(p => p.value).join(','));
  }

  // c-monthly — MA nonfarm month-over-month job change (levels are in thousands)
  if (maNF.length > 1) {
    const diffs = [];
    for (let i = 1; i < maNF.length; i++) {
      diffs.push({
        year: maNF[i].year, mon: maNF[i].mon,
        value: Math.round((maNF[i].value - maNF[i - 1].value) * 1000),
      });
    }
    const w = diffs.slice(-16);
    html = inject(html, 'mom-lab',  axisLabels(w));
    html = inject(html, 'mom-data', w.map(p => p.value).join(','));
  }

  // c-unemp2 — MA vs National UR on a unified axis (trailing 13 months).
  // National leads MA by a month, so the newest point shows National with MA null.
  if (maUR.length && natUR.length) {
    const keys = [...new Set([...maUR, ...natUR].map(mkey))].sort((a, b) => a - b).slice(-13);
    const axis = keys.map(k => ({ year: Math.floor(k / 100), mon: k % 100 }));
    const maMap  = new Map(maUR.map(p => [mkey(p), p.value]));
    const natMap = new Map(natUR.map(p => [mkey(p), p.value]));
    const col = (map) => keys.map(k => (map.has(k) ? map.get(k) : 'null')).join(',');
    html = inject(html, 'ur2-lab', axisLabels(axis));
    html = inject(html, 'ur2-ma',  col(maMap));
    html = inject(html, 'ur2-nat', col(natMap));
  }

  return html;
}

// Foreign-Born vs Native tab — monthly NSA charts (CPS Table A-7).
function updateNativity(html, find) {
  const fbEmp = monthsOf(find(NATIVITY_SERIES.FB_EMP));
  const nbEmp = monthsOf(find(NATIVITY_SERIES.NB_EMP));

  // c-fb-monthly — foreign-born employed (thousands), trailing 16 months
  if (fbEmp.length) {
    const w = fbEmp.slice(-16);
    html = inject(html, 'fbm-lab',  axisLabels(w));
    html = inject(html, 'fbm-data', w.map(p => Math.round(p.value)).join(','));
  }

  // c-nat-emp — FB vs NB employment indexed to Jan 2024 = 100, sampled quarterly
  if (fbEmp.length && nbEmp.length) {
    const fbBase = fbEmp.find(p => p.year === 2024 && p.mon === 0)?.value;
    const nbBase = nbEmp.find(p => p.year === 2024 && p.mon === 0)?.value;
    if (fbBase && nbBase) {
      const axis = fbEmp.filter(p => p.mon % 3 === 0);            // Jan/Apr/Jul/Oct
      const last = fbEmp[fbEmp.length - 1];
      if (!axis.length || mkey(axis[axis.length - 1]) !== mkey(last)) axis.push(last);
      const fbMap = new Map(fbEmp.map(p => [mkey(p), p.value]));
      const nbMap = new Map(nbEmp.map(p => [mkey(p), p.value]));
      const idx = (map, base, k) => map.has(k) ? (map.get(k) / base * 100).toFixed(1) : 'null';
      html = inject(html, 'natemp-lab', axisLabels(axis));
      html = inject(html, 'natemp-fb',  axis.map(p => idx(fbMap, fbBase, mkey(p))).join(','));
      html = inject(html, 'natemp-nb',  axis.map(p => idx(nbMap, nbBase, mkey(p))).join(','));
    }
  }

  // c-nat-lfpr — participation rate by nativity & sex, latest month vs year-ago
  const order = [
    NATIVITY_SERIES.FB_LFPR_T, NATIVITY_SERIES.FB_LFPR_M, NATIVITY_SERIES.FB_LFPR_W,
    NATIVITY_SERIES.NB_LFPR_T, NATIVITY_SERIES.NB_LFPR_M, NATIVITY_SERIES.NB_LFPR_W,
  ].map(id => monthsOf(find(id)));
  if (order[0].length) {
    const cur = order[0][order[0].length - 1];
    const at = (arr, yr, mo) => { const p = arr.find(x => x.year === yr && x.mon === mo); return p ? p.value.toFixed(1) : 'null'; };
    const label = (yr) => `'${MON[cur.mon]} ${yr}'`;
    html = inject(html, 'lfpr-curlab',  label(cur.year));
    html = inject(html, 'lfpr-cur',     order.map(a => at(a, cur.year, cur.mon)).join(','));
    html = inject(html, 'lfpr-prevlab', label(cur.year - 1));
    html = inject(html, 'lfpr-prev',    order.map(a => at(a, cur.year - 1, cur.mon)).join(','));
  }

  return html;
}

// Men, Women & White-Collar tab — monthly SA charts (CPS race×sex + education).
function updateGenderRace(html, find) {
  const G = GENDER_RACE_SERIES;

  // Shared: overlay N series on a unified trailing-`n`-month axis, filling gaps with null.
  const overlay = (ids, tags, n = 18) => {
    const arrs = ids.map(id => monthsOf(find(id)));
    if (!arrs[0].length) return;
    const keys = [...new Set(arrs.flat().map(mkey))].sort((a, b) => a - b).slice(-n);
    const axis = keys.map(k => ({ year: Math.floor(k / 100), mon: k % 100 }));
    html = inject(html, tags[0], axisLabels(axis));
    arrs.forEach((arr, i) => {
      const m = new Map(arr.map(p => [mkey(p), p.value]));
      html = inject(html, tags[i + 1], keys.map(k => (m.has(k) ? m.get(k) : 'null')).join(','));
    });
  };

  // c-gr-ur — unemployment rate: men vs women vs White men (trailing 18 mo)
  overlay([G.UR_MEN, G.UR_WOMEN, G.UR_WHITEMEN], ['gr-ur-lab', 'gr-ur-men', 'gr-ur-women', 'gr-ur-wm']);

  // c-gr-edu — unemployment rate by education (trailing 18 mo)
  overlay([G.UR_COLLEGE, G.UR_SOMECOLL, G.UR_HS], ['gr-edu-lab', 'gr-edu-col', 'gr-edu-sc', 'gr-edu-hs']);

  // c-gr-bar — UR by race & sex, latest month vs year-ago
  const order = [G.UR_WHITEMEN, G.UR_WHITEWOMEN, G.UR_ALL, G.UR_BLACK, G.UR_HISP].map(id => monthsOf(find(id)));
  if (order[0].length) {
    const cur = order[0][order[0].length - 1];
    const at = (arr, yr, mo) => { const p = arr.find(x => x.year === yr && x.mon === mo); return p ? p.value.toFixed(1) : 'null'; };
    const label = (yr) => `'${MON[cur.mon]} ${yr}'`;
    html = inject(html, 'gr-bar-curlab',  label(cur.year));
    html = inject(html, 'gr-bar-cur',     order.map(a => at(a, cur.year, cur.mon)).join(','));
    html = inject(html, 'gr-bar-prevlab', label(cur.year - 1));
    html = inject(html, 'gr-bar-prev',    order.map(a => at(a, cur.year - 1, cur.mon)).join(','));
  }

  return html;
}

// Massachusetts white-collar & tech tab block — sector employment indexed to
// Jan 2022 = 100, sampled quarterly (BLS CES state, SA). Shows the professional /
// tech / finance cooldown against still-growing education & health.
function updateMASectors(html, find) {
  const S = MA_SECTOR_SERIES;
  const series = [S.PROF_BUS, S.INFO, S.FINANCIAL, S.EDUC_HEALTH].map(id => monthsOf(find(id)));
  if (!series[0].length) return html;
  const bases = series.map(arr => arr.find(p => p.year === 2022 && p.mon === 0)?.value);
  if (bases.some(b => !b)) return html;

  // Quarterly axis (Jan/Apr/Jul/Oct), plus the latest month if it isn't a quarter-start.
  const axis = series[0].filter(p => p.mon % 3 === 0);
  const last = series[0][series[0].length - 1];
  if (!axis.length || mkey(axis[axis.length - 1]) !== mkey(last)) axis.push(last);

  const idx = (arr, base) => {
    const m = new Map(arr.map(p => [mkey(p), p.value]));
    return axis.map(p => (m.has(mkey(p)) ? (m.get(mkey(p)) / base * 100).toFixed(1) : 'null')).join(',');
  };
  html = inject(html, 'ma-sec-lab',  axisLabels(axis));
  html = inject(html, 'ma-sec-pb',   idx(series[0], bases[0]));
  html = inject(html, 'ma-sec-info', idx(series[1], bases[1]));
  html = inject(html, 'ma-sec-fin',  idx(series[2], bases[2]));
  html = inject(html, 'ma-sec-eh',   idx(series[3], bases[3]));
  return html;
}

// Latest value + drop-from-peak for one MA sector series.
function maSectorStat(find, id) {
  const a = monthsOf(find(id));
  if (!a.length) return null;
  const last = a[a.length - 1];
  let peak = a[0];
  for (const p of a) if (p.value > peak.value) peak = p;
  return { last, peak, delta: last.value - peak.value };
}

// Replace raw HTML between <!--@tag--> … <!--@--> markers (for generated table rows).
function injectHTMLBlock(html, tag, raw) {
  const re = new RegExp(`(<!--@${tag}-->)[\\s\\S]*?(<!--@-->)`);
  if (!re.test(html)) { console.warn(`   ⚠️  html marker @${tag} not found — skipping`); return html; }
  return html.replace(re, `$1${raw}$2`);
}

// Full MA sector spectrum (By-Sector tab): YoY % + vs-Feb-2020 % sorted bars + a
// complete table (level, MoM, 1-yr, since-2020, share). All BLS CES state, SA.
function updateMASectorSpectrum(html, find) {
  const S = MA_SECTOR_SERIES;
  const total = monthsOf(find(S.TOTAL));
  if (!total.length) return html;
  const at = (arr, yr, mo) => { const p = arr.find(x => x.year === yr && x.mon === mo); return p ? p.value : null; };

  const rows = MA_SECTOR_META.map(([key, name]) => {
    const arr = monthsOf(find(S[key]));
    if (arr.length < 2) return null;
    const last = arr[arr.length - 1], prev = arr[arr.length - 2];
    const yearAgo = at(arr, last.year - 1, last.mon);
    const feb20   = at(arr, 2020, 1);
    return {
      name,
      level:  last.value,
      mom:    last.value - prev.value,
      yoyN:   yearAgo != null ? last.value - yearAgo : null,
      yoyPct: yearAgo ? (last.value - yearAgo) / yearAgo * 100 : null,
      panPct: feb20   ? (last.value - feb20)   / feb20   * 100 : null,
    };
  }).filter(Boolean);
  if (!rows.length) return html;
  const totLevel = total[total.length - 1].value;

  // Sorted bars — YoY % and vs-Feb-2020 %
  const byYoy = rows.filter(r => r.yoyPct != null).sort((a, b) => b.yoyPct - a.yoyPct);
  html = inject(html, 'msp-yoy-lab',  byYoy.map(r => `'${r.name}'`).join(','));
  html = inject(html, 'msp-yoy-data', byYoy.map(r => r.yoyPct.toFixed(1)).join(','));
  const byPan = rows.filter(r => r.panPct != null).sort((a, b) => b.panPct - a.panPct);
  html = inject(html, 'msp-pan-lab',  byPan.map(r => `'${r.name}'`).join(','));
  html = inject(html, 'msp-pan-data', byPan.map(r => r.panPct.toFixed(1)).join(','));

  // Full table body
  const jobs = (k) => (k == null ? '—' : (k < 0 ? '−' : '+') + Math.abs(Math.round(k * 1000)).toLocaleString('en-US'));
  const pctS = (n) => (n == null ? '—' : (n < 0 ? '−' : '+') + Math.abs(n).toFixed(1) + '%');
  const cls  = (n) => (n == null ? '' : n < 0 ? ' class="td-red"' : ' class="td-green"');
  const tr = (r) => `<tr><td>${r.name}</td><td>${r.level.toFixed(1)}K</td>`
    + `<td${cls(r.mom)}>${jobs(r.mom)}</td><td${cls(r.yoyN)}>${jobs(r.yoyN)}</td>`
    + `<td${cls(r.yoyPct)}>${pctS(r.yoyPct)}</td><td${cls(r.panPct)}>${pctS(r.panPct)}</td>`
    + `<td>${(r.level / totLevel * 100).toFixed(1)}%</td></tr>`;
  const body = rows.map(tr).join('')
    + `<tr><td><strong>Total Nonfarm</strong></td><td><strong>${totLevel.toFixed(1)}K</strong></td>`
    + `<td></td><td></td><td></td><td></td><td>100%</td></tr>`;
  html = injectHTMLBlock(html, 'msp-table', body);
  return html;
}

// ── Dashboard updater ─────────────────────────────────────────────────────────
async function updateDashboard(data, empSeries) {
  let html = await fs.readFile(DASHBOARD_PATH, 'utf-8');
  const find = (id) => empSeries?.find(s => s.seriesID === id);

  function setField(fieldName, value) {
    html = html.replace(
      new RegExp(`(data-field="${fieldName}">)[^<]*(<)`, 'g'),
      `$1${value}$2`
    );
  }

  // Hero: MA unemployment rate + label date
  if (data.ma_unemployment_rate?.latest) {
    const rate = data.ma_unemployment_rate.latest.value.toFixed(1);
    const date = data.ma_unemployment_rate.latest.date;
    html = html.replace(
      /(<div class="hero-stat"><div class="val[^"]*">)[\d.]+%(<\/div><div class="lbl">MA Unemployment[^<]*<\/div><\/div>)/,
      `$1${rate}%</div><div class="lbl">MA Unemployment (${date})</div></div>`
    );
  }

  // JOLTS national openings
  if (data.us_job_openings?.latest) {
    const v        = data.us_job_openings.latest.value;
    const openingsM = (v / 1000).toFixed(1) + 'M';
    const date      = data.us_job_openings.latest.date;
    // Openings (JTS...JOL) are national, in thousands — so the denominator must be too.
    // This previously used MA unemployment *level*, which is national-vs-state AND
    // thousands-vs-persons, understating the ratio ~24x (rendered 0.04 against a card
    // subtitle reading "Healthy: 1.0-1.2"). LNS13000000 is national unemployed in
    // thousands, so the ratio comes out unitless and comparable to that subtitle.
    //
    // Pull the SAME month rather than each series' newest: JOLTS lags the Employment
    // Situation by a month, so "latest of each" pairs May openings with June
    // unemployment and quietly reports a ratio for a month that never existed.
    const period     = `${data.us_job_openings.latest.year}-${data.us_job_openings.latest.period}`;
    const unemployed = data.us_unemployment_level?.byPeriod?.[period];
    const ratio      = unemployed ? (v / unemployed).toFixed(2) : null;
    setField('jolts-openings',       openingsM);
    setField('jolts-openings-date',  `${date} · auto-updated`);
    setField('jolts-openings-table', openingsM);
    setField('jolts-col-current',    date);
    if (ratio) {
      setField('jolts-ratio', ratio);
    } else {
      console.warn(`   ⚠️  JOLTS ratio skipped: no US unemployment level for ${period}`);
    }
    console.log(`   ✅ JOLTS fields updated: ${openingsM} (${date}), ratio ${ratio ?? 'n/a'} (both ${period})`);
  }

  // ── National Employment Situation block + table ───────────────────────────
  // National data leads MA state data by ~3 weeks, so this carries the newest
  // month. Figures are computed from the same SA series BLS headlines (payrolls,
  // U-3, U-6, household employment, labor force) — verifiable, no scraping.
  const nser  = (id) => monthsOf(find(id));
  const lastOf = (a) => a[a.length - 1];
  const prevOf = (a) => a[a.length - 2];
  const FULLMON = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const sgn = (n) => (n < 0 ? '−' : '+') + Math.abs(Math.round(n)).toLocaleString('en-US');
  const sgnK = (n) => (n < 0 ? '−' : '+') + Math.round(Math.abs(n) / 1000) + 'K';

  const nf = nser(EMPLOYMENT_SERIES.US_NONFARM);
  if (nf.length >= 3) {
    const relDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const cM = lastOf(nf), pM = prevOf(nf);
    const moK = (a, i) => (a[a.length - i].value - a[a.length - i - 1].value) * 1000; // i=1 newest MoM
    const ur  = nser(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_RATE);
    const u6  = nser(EMPLOYMENT_SERIES.US_U6);
    const hh  = nser(EMPLOYMENT_SERIES.US_HH_EMP);
    const lf  = nser(EMPLOYMENT_SERIES.US_LABOR_FORCE);

    const payCur = moK(nf, 1), payPrev = moK(nf, 2);
    const urCur = lastOf(ur).value, urPrev = prevOf(ur).value;
    const urChg = urCur === urPrev ? '(unchanged)' : urCur > urPrev ? '(up)' : '(down)';
    const hhCur = moK(hh, 1), hhPrev = moK(hh, 2);
    const lfCur = moK(lf, 1), lfPrev = moK(lf, 2);
    const sep25 = hh.find(p => p.year === 2025 && p.mon === 8); // employed since Sep 2025
    const cumSep = sep25 ? (lastOf(hh).value - sep25.value) * 1000 : null;

    const monShort = (p) => `${MON[p.mon]} ${p.year}`;
    const monLong  = (p) => `${FULLMON[p.mon]} ${p.year}`;

    // Overview landing subtitle (visible without switching tabs)
    setField('ov-nat-pay', sgnK(payCur));
    setField('ov-nat-ur',  urCur.toFixed(1) + '%');
    // National Employment alert block
    setField('nat-emp-month', monLong(cM));
    setField('nat-emp-rel',   relDate);
    setField('nat-emp-rel2',  relDate);
    setField('nat-payrolls',  sgn(payCur));
    setField('nat-ur',        urCur.toFixed(1) + '%');
    setField('nat-ur-chg',    urChg);
    setField('nat-u6',        u6.length ? lastOf(u6).value.toFixed(1) + '%' : '—');
    setField('nat-hh',        sgn(hhCur));
    setField('nat-lf',        sgn(lfCur));
    // National Context table
    setField('nat-ctx-month', monLong(cM));
    setField('nat-ctx-rel',   relDate);
    setField('nat-col-cur',   monShort(cM));
    setField('nat-col-prev',  monShort(pM));
    setField('nat-u3-cur',    urCur.toFixed(1) + '%');
    setField('nat-u3-prev',   urPrev.toFixed(1) + '%');
    if (u6.length >= 2) { setField('nat-u6-cur', lastOf(u6).value.toFixed(1) + '%'); setField('nat-u6-prev', prevOf(u6).value.toFixed(1) + '%'); }
    setField('nat-pay-cur',   sgn(payCur));
    setField('nat-pay-prev',  sgn(payPrev));
    setField('nat-hh-cur',    sgn(hhCur));
    setField('nat-hh-prev',   sgn(hhPrev));
    setField('nat-lf-cur',    sgn(lfCur));
    setField('nat-lf-prev',   sgn(lfPrev));
    if (cumSep != null) setField('nat-cum-sep', sgn(cumSep) + ' cumulative');
    setField('nat-src-date',  relDate);
    console.log(`   ✅ National block updated: ${monLong(cM)} — payrolls ${sgn(payCur)}, UR ${urCur}% ${urChg}`);
  }

  // Foreign-Born tab subtitle month
  const fbMonths = monthsOf(find(NATIVITY_SERIES.FB_EMP));
  if (fbMonths.length) {
    const p = fbMonths[fbMonths.length - 1];
    setField('nat-fb-month', `${MON[p.mon]} ${p.year}`);
  }

  // Men, Women & White-Collar tab — subtitle month + stat cards + table headers
  const grLast = (id) => { const a = monthsOf(find(id)); return a.length ? a[a.length - 1] : null; };
  const grMen = grLast(GENDER_RACE_SERIES.UR_MEN);
  if (grMen) {
    const p = grMen; const md = `${MON[p.mon]} ${p.year}`;
    const wm = grLast(GENDER_RACE_SERIES.UR_WHITEMEN);
    const wo = grLast(GENDER_RACE_SERIES.UR_WOMEN);
    const col = grLast(GENDER_RACE_SERIES.UR_COLLEGE);
    const all = grLast(GENDER_RACE_SERIES.UR_ALL);
    setField('gr-month',    md);
    setField('gr-tbl-cur',  md);
    setField('gr-tbl-prev', `${MON[p.mon]} ${p.year - 1}`);
    setField('gr-edu-cur',  md);
    setField('gr-men-ur',   grMen.value.toFixed(1) + '%');
    if (wo)  setField('gr-women-ur', wo.value.toFixed(1) + '%');
    if (col) setField('gr-col-ur',   col.value.toFixed(1) + '%');
    if (wm) {
      setField('gr-wm-ur', wm.value.toFixed(1) + '%');
      if (all) {
        const gap = (all.value - wm.value).toFixed(1);
        setField('gr-wm-sub', `${gap} pt below national`);
      }
    }
    console.log(`   ✅ Gender/race/education fields updated (${md}) — White men ${wm?.value}%, college ${col?.value}%`);
  }

  // Massachusetts white-collar & tech stat cards (BLS CES, thousands, SA)
  const pb = maSectorStat(find, MA_SECTOR_SERIES.PROF_BUS);
  if (pb) {
    const peakLbl = (s) => `${MON[s.peak.mon]} ${String(s.peak.year).slice(2)}`;
    const sub = (s) => `${s.delta < 0 ? '−' : '+'}${Math.abs(s.delta).toFixed(1)}K vs ${peakLbl(s)} peak`;
    const info = maSectorStat(find, MA_SECTOR_SERIES.INFO);
    const fin  = maSectorStat(find, MA_SECTOR_SERIES.FINANCIAL);
    const eh   = maSectorStat(find, MA_SECTOR_SERIES.EDUC_HEALTH);
    const pct = (s) => `${s.delta < 0 ? '−' : '+'}${Math.abs(s.delta / s.peak.value * 100).toFixed(1)}%`;
    const peakK = (s) => s.peak.value.toFixed(1);
    setField('ma-month',   `${MON[pb.last.mon]} ${pb.last.year}`);
    setField('ma-tbl-now', `${MON[pb.last.mon]} ${pb.last.year}`);
    setField('sec-month',  `${MON[pb.last.mon]} ${pb.last.year}`);
    setField('ma-pb-val',  pb.last.value.toFixed(1) + 'K');
    setField('ma-pb-sub',  sub(pb));
    setField('ma-pb-peak', peakK(pb)); setField('ma-pb-now', pb.last.value.toFixed(1)); setField('ma-pb-chg', pct(pb));
    if (info) { setField('ma-info-val', info.last.value.toFixed(1) + 'K'); setField('ma-info-sub', sub(info));
                setField('ma-info-peak', peakK(info)); setField('ma-info-now', info.last.value.toFixed(1)); setField('ma-info-chg', pct(info)); }
    if (fin)  { setField('ma-fin-val',  fin.last.value.toFixed(1) + 'K');  setField('ma-fin-sub',  sub(fin));
                setField('ma-fin-peak', peakK(fin)); setField('ma-fin-now', fin.last.value.toFixed(1)); setField('ma-fin-chg', pct(fin)); }
    if (eh)   { setField('ma-eh-val', eh.last.value.toFixed(1) + 'K'); setField('ma-eh-now', eh.last.value.toFixed(1)); }
    console.log(`   ✅ MA sectors updated (${MON[pb.last.mon]} ${pb.last.year}) — Prof/Bus ${pb.last.value}K, Info ${info?.last.value}K`);
  }

  // Charts — rewrite the auto-updating series arrays from the live BLS series
  if (empSeries?.length) {
    html = updateCharts(html, find);
    html = updateNativity(html, find);
    html = updateGenderRace(html, find);
    html = updateMASectors(html, find);
    html = updateMASectorSpectrum(html, find);
  }

  // Footer date
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
  html = html.replace(/Updated [^·]+·/, `Updated ${today} ·`);

  return html;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log('🔄 Fetching BLS employment data...\n');
  const currentYear = new Date().getFullYear();

  // ── 1. Employment series (critical — retry up to 3x) ──────────────────────
  let empSeries;
  try {
    empSeries = await fetchBLSData(
      Object.values(EMPLOYMENT_SERIES),
      currentYear - 2,
      currentYear
    );
  } catch (err) {
    // All retries exhausted — check if we have previous data to preserve
    console.error(`\n❌ Employment fetch failed: ${err.message}`);
    const prev = await loadPreviousData();
    if (prev) {
      console.warn('⚠️  Using cached data from previous run — dashboard NOT updated.');
      console.warn(`   Previous data: ${prev.fetched_at}`);
      // Exit 0 so GitHub Actions marks it as a warning, not a failure
      process.exit(0);
    }
    // No cache — exit 1 so the failure is visible
    console.error('❌ No cached data available. Dashboard not updated.');
    process.exit(1);
  }

  const findSeries = (id) => empSeries.find(s => s.seriesID === id);

  const data = {
    fetched_at:            new Date().toISOString(),
    ma_unemployment_rate:  { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_RATE)) },
    ma_unemployment_level: { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_LEVEL)) },
    ma_labor_force:        { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_LABOR_FORCE)) },
    ma_total_nonfarm:      { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_TOTAL_NONFARM)) },
    us_unemployment_rate:  { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_RATE)) },
    us_unemployment_level: {
      latest:   getLatestValue(findSeries(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_LEVEL)),
      byPeriod: periodMap(findSeries(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_LEVEL)),
    },
    us_job_openings:       null,
    jolts_note: 'BLS discontinued monthly state JOLTS in 2026. National JOLTS still monthly. First annual state release: July 2026.',
  };

  console.log(`   ✅ MA Unemployment:  ${data.ma_unemployment_rate.latest?.value}% (${data.ma_unemployment_rate.latest?.date})`);
  console.log(`   ✅ US Unemployment:  ${data.us_unemployment_rate.latest?.value}%`);
  console.log(`   ✅ MA Nonfarm:       ${data.ma_total_nonfarm.latest?.value?.toLocaleString()}K (${data.ma_total_nonfarm.latest?.date})`);
  console.log(`   ✅ MA Labor Force:   ${data.ma_labor_force.latest?.value?.toLocaleString()} (${data.ma_labor_force.latest?.date})`);

  // ── 2. JOLTS (non-critical — one retry, skip gracefully) ──────────────────
  console.log('\n🔄 Fetching JOLTS data (national only)...');
  try {
    const joltsSeries = await fetchBLSData(
      Object.values(JOLTS_SERIES),
      currentYear - 1,
      currentYear
    );
    const jolts = joltsSeries.find(s => s.seriesID === JOLTS_SERIES.US_JOB_OPENINGS);
    data.us_job_openings = { latest: getLatestValue(jolts) };
    console.log(`   ✅ US Job Openings: ${(data.us_job_openings.latest?.value / 1000).toFixed(1)}M (${data.us_job_openings.latest?.date})`);
  } catch (err) {
    console.warn(`   ⚠️  JOLTS skipped: ${err.message}`);
    data.jolts_error = err.message;
  }

  // ── 2b. Nativity (non-critical — feeds the Foreign-Born tab charts) ────────
  console.log('\n🔄 Fetching foreign-born / native-born data (NSA)...');
  try {
    const natSeries = await fetchBLSData(Object.values(NATIVITY_SERIES), currentYear - 2, currentYear);
    empSeries.push(...natSeries);
    const fb = natSeries.find(s => s.seriesID === NATIVITY_SERIES.FB_EMP);
    console.log(`   ✅ Nativity series fetched (${natSeries.length}) — FB employed latest ${getLatestValue(fb)?.date}`);
  } catch (err) {
    console.warn(`   ⚠️  Nativity skipped: ${err.message}`);
  }

  // ── 2c. Gender / race / education (non-critical — feeds the White-Collar tab) ─
  console.log('\n🔄 Fetching gender / race / education data (SA)...');
  try {
    const grSeries = await fetchBLSData(Object.values(GENDER_RACE_SERIES), currentYear - 2, currentYear);
    empSeries.push(...grSeries);
    const wm = grSeries.find(s => s.seriesID === GENDER_RACE_SERIES.UR_WHITEMEN);
    console.log(`   ✅ Gender/race series fetched (${grSeries.length}) — White men UR latest ${getLatestValue(wm)?.value}% (${getLatestValue(wm)?.date})`);
  } catch (err) {
    console.warn(`   ⚠️  Gender/race skipped: ${err.message}`);
  }

  // ── 2d. MA industry employment (non-critical — feeds the MA sector views) ──
  // Fetched from 2019 for the Jan-2022 index baseline + Feb-2020 pre-pandemic compare.
  console.log('\n🔄 Fetching MA industry employment (CES, SA, from 2019)...');
  try {
    const maSectors = await fetchBLSData(Object.values(MA_SECTOR_SERIES), 2019, currentYear);
    empSeries.push(...maSectors);
    const info = maSectors.find(s => s.seriesID === MA_SECTOR_SERIES.INFO);
    console.log(`   ✅ MA sectors fetched (${maSectors.length}) — Information latest ${getLatestValue(info)?.value}K (${getLatestValue(info)?.date})`);
  } catch (err) {
    console.warn(`   ⚠️  MA sectors skipped: ${err.message}`);
  }

  // ── 3. Save snapshot + rotate previous ───────────────────────────────────
  await fs.mkdir(path.dirname(DATA_OUTPUT_PATH), { recursive: true });
  // Rotate: current → previous before overwriting
  try {
    const current = await fs.readFile(DATA_OUTPUT_PATH, 'utf-8');
    await fs.writeFile(DATA_PREV_PATH, current);
  } catch { /* first run — no previous file yet */ }
  await fs.writeFile(DATA_OUTPUT_PATH, JSON.stringify(data, null, 2));
  console.log('\n💾 Saved data/employment-latest.json');

  // ── 4. Update dashboard HTML ──────────────────────────────────────────────
  const updatedHtml = await updateDashboard(data, empSeries);
  await fs.writeFile(DASHBOARD_PATH, updatedHtml);
  console.log('📄 Updated employment-dashboard.html');

  console.log('\n✨ Done!');
}

// Run unless imported for testing (BLS_SKIP_MAIN=1).
if (process.env.BLS_SKIP_MAIN !== '1') {
  main().catch(e => {
    console.error('❌ Fatal error:', e.message);
    process.exit(1);
  });
}

export { monthsOf, inject, injectHTMLBlock, updateMASectorSpectrum, MA_SECTOR_SERIES, MA_SECTOR_META };
