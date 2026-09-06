import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_PATH    = path.join(__dirname, '..', 'employment-dashboard.html');
const DATA_OUTPUT_PATH  = path.join(__dirname, '..', 'data', 'employment-latest.json');
const DATA_PREV_PATH    = path.join(__dirname, '..', 'data', 'employment-previous.json');
const RELEASE_SCHED_PATH = path.join(__dirname, '..', 'data', 'bls-release-schedule.json');
const VINTAGES_PATH      = path.join(__dirname, '..', 'data', 'national-payroll-vintages.json');

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

// National CES industry employment (SA, all employees, level in thousands).
//
// The dashboard reported the headline payroll number and then told the reader
// "full sector breakdown & revisions in the release" — i.e. it linked out for the
// part that explains the figure it had just printed. July 2026 is the case in
// point: the headline was −23,000, but private payrolls ROSE 30,000 and
// government fell 53,000. "Payrolls fell" and "the private sector added jobs"
// were both true that month, and the page showed only the first.
//
// These sum to total nonfarm, so the table can be checked against the headline
// rather than asserted alongside it — see the reconciliation row.
const US_SECTOR_SERIES = {
  PRIVATE:       'CES0500000001',  // total private — the check row, not a line item
  MINING:        'CES1000000001',
  CONSTRUCTION:  'CES2000000001',
  MANUFACTURING: 'CES3000000001',
  TRADE_TRANS:   'CES4000000001',
  INFORMATION:   'CES5000000001',
  FINANCIAL:     'CES5500000001',
  PROF_BUS:      'CES6000000001',
  EDU_HEALTH:    'CES6500000001',
  LEISURE:       'CES7000000001',
  OTHER_SVC:     'CES8000000001',
  GOVERNMENT:    'CES9000000001',
};

// Display names, and the subset that forms the additive breakdown. PRIVATE is
// deliberately excluded: it is the sum of the private rows, so including it as a
// row would double-count and the reconciliation check would stop meaning anything.
const US_SECTOR_META = [
  ['EDU_HEALTH',    'Private Education & Health'],
  ['LEISURE',       'Leisure & Hospitality'],
  ['PROF_BUS',      'Professional & Business'],
  ['TRADE_TRANS',   'Trade, Transportation & Utilities'],
  ['GOVERNMENT',    'Government'],
  ['CONSTRUCTION',  'Construction'],
  ['MANUFACTURING', 'Manufacturing'],
  ['FINANCIAL',     'Financial Activities'],
  ['INFORMATION',   'Information'],
  ['OTHER_SVC',     'Other Services'],
  ['MINING',        'Mining & Logging'],
];

// National JOLTS only — BLS discontinued monthly state JOLTS (last: Dec 2025).
// First annual state JOLTS release: July 2026.
//
// Hires/separations/quits/layoffs are fetched (not just openings) because the
// JOLTS table publishes all five. They used to be hardcoded, and had drifted
// badly — the page showed 5.6M hires against an actual 5.2M, and its "YoY"
// column compared a live current month to a frozen Mar-2025 one, so the span
// silently stretched to 14 months. All five now come from the series, and the
// year-ago column is pulled for the SAME calendar month (see periodMap).
const JOLTS_SERIES = {
  US_JOB_OPENINGS:  'JTS000000000000000JOL',
  US_OPENINGS_RATE: 'JTS000000000000000JOR',
  US_HIRES:         'JTS000000000000000HIL',
  US_SEPARATIONS:   'JTS000000000000000TSL',
  US_QUITS:         'JTS000000000000000QUL',
  US_LAYOFFS:       'JTS000000000000000LDL',
};

// Foreign-born / native-born (CPS Table A-7). NOT seasonally adjusted — these
// drive the Foreign-Born vs Native tab. Series verified vs the published A-7.
const NATIVITY_SERIES = {
  FB_EMP:    'LNU02073395',  // foreign-born employed (thousands)
  NB_EMP:    'LNU02073413',  // native-born employed (thousands)
  FB_UR:     'LNU04073395',  // foreign-born unemployment rate
  NB_UR:     'LNU04073413',  // native-born unemployment rate
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
  UR_LESSHS:      'LNS14027660',  // less than high school, 25+
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

// ── BLS release schedule ──────────────────────────────────────────────────────
// The "Released <date>" stamps used to come from new Date(), i.e. whenever CI
// happened to run. That silently republished a false provenance line every time
// the workflow woke up on a non-release day: the Aug 5 and Aug 6 2026 runs both
// printed "June 2026 National Employment — Released August 5 / 6, 2026" when the
// June reference month was actually released July 2, 2026.
//
// The real dates cannot be derived — there is no first-Friday rule. In 2026 the
// Apr reference month went out on the *second* Friday (May 8) and Jun went out on
// a Thursday (Jul 2, moved for July 4). So the published schedule is pinned in
// data/bls-release-schedule.json and read here. bls.gov itself is not fetchable
// from CI (it 403s non-browser clients, same block that stalled the CBP feed);
// api.bls.gov serves the numbers but carries no release dates.
// Returns both schedules: `national` (Employment Situation, drives the national
// block) and `state` (State Employment and Unemployment, drives every MA
// citation). They are genuinely different calendars — the MA vintage lands about
// three weeks later — which is why the MA blocks legitimately sit a month behind.
async function loadReleaseSchedule() {
  try {
    const raw = JSON.parse(await fs.readFile(RELEASE_SCHED_PATH, 'utf-8'));
    return {
      national: raw.employment_situation || {},
      state:    raw.state_employment     || {},
    };
  } catch (err) {
    console.log(`::warning::Could not read ${path.basename(RELEASE_SCHED_PATH)} (${err.message}) — release dates will render as "—"`);
    return { national: {}, state: {} };
  }
}

// First-print payroll changes, so the page can show what BLS has since revised.
// BLS serves only the current vintage, so a month's first print is unrecoverable
// once missed — this file is the only record of it, and existing entries are
// therefore append-only. See the file's own _how_this_is_seeded note.
async function loadVintages() {
  try {
    const raw = JSON.parse(await fs.readFile(VINTAGES_PATH, 'utf-8'));
    return { doc: raw, firstPrint: raw.first_print || {} };
  } catch (err) {
    console.log(`::warning::Could not read ${path.basename(VINTAGES_PATH)} (${err.message}) — revisions will render as "—"`);
    return { doc: null, firstPrint: {} };
  }
}

// Record any reference month we have not seen before. Runs daily against a known
// release schedule, so a new month is captured on the day it is first published —
// which is what makes the stored value a first print. Existing months are never
// touched: overwriting one would quietly erase the revision it is there to expose.
async function saveNewVintages(doc, firstPrint, added) {
  if (!doc || !added.length) return;
  doc.first_print = Object.fromEntries(
    Object.entries(firstPrint).sort(([a], [b]) => a.localeCompare(b))
  );
  await fs.writeFile(VINTAGES_PATH, JSON.stringify(doc, null, 2) + '\n');
  console.log(`   📌 First print recorded for ${added.join(', ')}`);
}

// Month-over-month change in jobs, defined only where the two newest points are
// genuinely adjacent months. BLS published no Oct 2025 (the appropriations lapse)
// and monthsOf drops absent months, so differencing straight across the hole would
// report two months of movement as one month's change.
function momAdjacent(arr) {
  if (!arr || arr.length < 2) return null;
  const a = arr[arr.length - 1], b = arr[arr.length - 2];
  return ordOf(a) - ordOf(b) === 1 ? Math.round((a.value - b.value) * 1000) : null;
}

// Industry rows for the "where the change came from" table, largest gain first.
// `monthsFor` maps a US_SECTOR_SERIES key to its month array. Pure so the
// reconciliation property (rows sum to the headline) can be tested offline.
function buildSectorRows(monthsFor, meta) {
  return meta
    .map(([key, label]) => {
      const m = monthsFor(key) || [];
      return { label, chg: momAdjacent(m), lvl: m.length ? m[m.length - 1].value : null };
    })
    .filter(r => r.chg != null && r.lvl != null)
    .sort((a, b) => b.chg - a.chg);
}

// What BLS has revised: the months behind the newest, each compared against the
// first print recorded on its release day. `first: null` means the month predates
// tracking — the caller renders an em dash, never a zero, because "we don't know"
// and "unrevised" are different claims.
function buildRevisionRows(nfMonths, firstPrint, back = 3) {
  const out = [];
  for (let i = 1; i <= back; i++) {
    const idx = nfMonths.length - 1 - i;
    if (idx < 1) break;
    const m = nfMonths[idx], prev = nfMonths[idx - 1];
    if (ordOf(m) - ordOf(prev) !== 1) continue;
    const now = Math.round((m.value - prev.value) * 1000);
    const key = `${m.year}-${String(m.mon + 1).padStart(2, '0')}`;
    const first = firstPrint[key] == null ? null : firstPrint[key];
    out.push({ year: m.year, mon: m.mon, key, first, now, rev: first == null ? null : now - first });
  }
  return out;
}

// Reference month → the day BLS actually published it. Formatted from the date
// parts rather than through Date/toLocaleDateString, because "2026-08-07" parses
// as UTC midnight and would render as August 6 on any runner west of Greenwich.
// Returns null when the month is not in the schedule — the caller renders an em
// dash rather than substituting today, which is the bug this replaced.
function releaseDateFor(sched, year, monIdx, FULLMON) {
  const iso = sched[`${year}-${String(monIdx + 1).padStart(2, '0')}`];
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  return `${FULLMON[m - 1]} ${d}, ${y}`;
}

// ── Chart-array helpers ─────────────────────────────────────────────────────────
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const FULLMON = ['January','February','March','April','May','June','July','August','September','October','November','December'];

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

// Monotonic month ordinal — unlike mkey, consecutive months always differ by 1,
// so it can test whether two points are genuinely adjacent across a year end.
const ordOf = p => p.year * 12 + p.mon;

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


// ── MA vs nation comparison box (Overview tab) ───────────────────────────────
// Twenty-six months of both geographies on ONE shared axis, so the page can read
// a 12-month change at the same index for each and never has to align anything
// itself.
//
// The national series publish about two weeks before the state ones, so the
// newest month routinely carries a US value and a null for MA. That is deliberate
// and must stay: the page anchors on MA's newest complete month and reads the US
// column at that same index, which is the only way the two columns describe the
// same period. Trimming the axis to MA's end would throw away the US value that
// is needed the moment MA catches up.
//
// Exported so the alignment is testable without an API key — see
// scripts/test-comparison-box.mjs.
const CMP_TAGS = ['cmp-lab', 'cmp-ma-ur', 'cmp-us-ur', 'cmp-ma-nf', 'cmp-us-nf',
                  'cmp-ma-lf', 'cmp-us-lf'];

function buildComparisonBox(html, s) {
  const cols = [s.maUR, s.usUR, s.maNF, s.usNF, s.maLF, s.usLF];
  if (!cols.every(a => a && a.length)) {
    // Left as a no-op on purpose: a transient gap in one BLS series should not
    // fail the whole employment refresh, and last month's box is better than a
    // half-written one. But it must not pass in silence either -- if a series is
    // renamed the box would sit frozen forever looking perfectly healthy.
    const missing = ['maUR', 'usUR', 'maNF', 'usNF', 'maLF', 'usLF']
      .filter(k => !s[k] || !s[k].length);
    console.warn(`   ⚠️  comparison box NOT updated — no data for: ${missing.join(', ')}. ` +
                 `It is still showing the month it was last built with.`);
    return html;
  }

  // inject() only WARNS when a marker is missing. For this box that would leave
  // every figure frozen at whatever month it was last built with while the rest
  // of the page moved on — silent staleness, which is the failure mode this repo
  // keeps paying for. Seven markers is enough surface to get one wrong, so they
  // are checked up front and a miss is fatal rather than a log line nobody reads.
  for (const t of CMP_TAGS) {
    if (!new RegExp(`/\\*@${t}\\*/[\\s\\S]*?/\\*@\\*/`).test(html)) {
      throw new Error(
        `comparison-box marker @${t} is missing from employment-dashboard.html. ` +
        `The box would keep publishing a stale month. Restore the marker.`);
    }
  }

  const keys = [...new Set(cols.flat().map(mkey))].sort((a, b) => a - b).slice(-26);
  const axis = keys.map(k => ({ year: Math.floor(k / 100), mon: k % 100 }));
  const col = (pts, divisor = 1, dp = 1) => {
    const m = new Map(pts.map(p => [mkey(p), p.value]));
    return keys.map(k => (m.has(k) ? (m.get(k) / divisor).toFixed(dp) : 'null')).join(',');
  };

  html = inject(html, 'cmp-lab',   axisLabels(axis));
  html = inject(html, 'cmp-ma-ur', col(s.maUR));
  html = inject(html, 'cmp-us-ur', col(s.usUR));
  html = inject(html, 'cmp-ma-nf', col(s.maNF));
  html = inject(html, 'cmp-us-nf', col(s.usNF));
  // MA labour force is published in PERSONS; every other level on this axis is
  // thousands. Divided here so the page never has to know which is which.
  html = inject(html, 'cmp-ma-lf', col(s.maLF, 1000, 3));
  html = inject(html, 'cmp-us-lf', col(s.usLF));
  return html;
}

// Build every auto-chart literal from the fetched series, then inject into the HTML.
function updateCharts(html, find, findLong) {
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

  // c-laborforce — MA labor force level, plus the table and the peak-to-latest
  // sentence underneath it.
  //
  // Injected from LF_ANCHOR, not the chart's trailing 16 months. Those consumers
  // find the peak by scanning this array, and on a 16-month window the Mar-2025
  // peak was one month from sliding off the back — after which "the peak" would
  // silently become the highest month still in view and the sentence would
  // re-anchor itself without saying so.
  //
  // Jan 2024 rather than all of history: the page's claim is about the post-2024
  // decline. Feeding it 2019 makes the peak Feb 2020 and quietly turns a sentence
  // about the current cycle into one about the pandemic — a different claim than
  // the page is making. The chart slices to its 16-month window at the point of use.
  const LF_ANCHOR = { year: 2024, mon: 0 };
  const lfW = maLF.filter(p => ordOf(p) >= ordOf(LF_ANCHOR));
  if (lfW.length) {
    html = inject(html, 'lf-lab',  axisLabels(lfW));
    html = inject(html, 'lf-data', lfW.map(p => p.value).join(','));
  }

  // MA unemployed persons, level — the "why" behind the rate move. Fetched on
  // every run since the series list was written, but never injected, so the
  // sentence explaining the rate carried a hand-typed count nothing could update.
  const maUL = monthsOf(find(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_LEVEL))
    .filter(p => ordOf(p) >= ordOf(LF_ANCHOR));
  if (maUL.length) {
    html = inject(html, 'ul-lab',  axisLabels(maUL));
    html = inject(html, 'ul-data', maUL.map(p => p.value).join(','));
  }

  // c-monthly, plus every payroll figure in the prose — MA nonfarm month-over-month
  // job change (levels are in thousands).
  //
  // Injected as the FULL history, not the chart's trailing 16-month window: the
  // page derives full-year and since-a-given-month totals from this array, and a
  // sliding window silently turns those into partial sums as its start month
  // falls off the end. The chart slices to 16 client-side.
  //
  // Only emit a change where the two months are genuinely adjacent. Where BLS
  // published no value (the Oct-2025 appropriations lapse), monthsOf drops the
  // month, and differencing straight across the hole would fabricate a one-month
  // "change" that is really two months of movement.
  const nfLong = monthsOf(findLong(MA_SECTOR_SERIES.TOTAL));
  const nfSrc  = nfLong.length >= maNF.length ? nfLong : maNF;
  if (nfSrc.length > 1) {
    const diffs = [];
    for (let i = 1; i < nfSrc.length; i++) {
      if (ordOf(nfSrc[i]) - ordOf(nfSrc[i - 1]) !== 1) continue;
      diffs.push({
        year: nfSrc[i].year, mon: nfSrc[i].mon,
        value: Math.round((nfSrc[i].value - nfSrc[i - 1].value) * 1000),
      });
    }
    html = inject(html, 'mom-lab',  axisLabels(diffs));
    html = inject(html, 'mom-data', diffs.map(p => p.value).join(','));
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

  html = buildComparisonBox(html, {
    maUR, usUR: natUR, maNF, maLF,
    usNF: monthsOf(find(EMPLOYMENT_SERIES.US_NONFARM)),
    usLF: monthsOf(find(EMPLOYMENT_SERIES.US_LABOR_FORCE)),
  });

  return html;
}

// c-jobs — MA annual net job growth, measured December-to-December (BLS CES).
//
// These bars were hardcoded and were a pre-benchmark-revision vintage throughout:
// the page shipped +1,300 for full-year 2025 when the revised series says −17,300
// — not a flat year but a contraction, and the wrong sign. Every annual revision
// would silently re-break them, so they are computed from the series now. Needs
// the 2019-start CES history (findLong), since the employment batch only fetches
// three years and each bar needs the prior December.
function updateJobsAnnual(html, findLong) {
  const nf = monthsOf(findLong(MA_SECTOR_SERIES.TOTAL));
  if (nf.length < 13) return html;

  const dec = new Map(nf.filter(p => p.mon === 11).map(p => [p.year, p.value]));
  const years = [...dec.keys()].sort((a, b) => a - b).filter(y => dec.has(y - 1)).slice(-5);
  if (!years.length) return html;

  html = inject(html, 'jobs-lab',  years.map(y => `'${y}'`).join(','));
  html = inject(html, 'jobs-data', years.map(y => Math.round((dec.get(y) - dec.get(y - 1)) * 1000)).join(','));
  console.log(`   ✅ Annual job growth updated: ${years.map(y => `${y} ${Math.round((dec.get(y) - dec.get(y - 1)) * 1000)}`).join(', ')}`);
  return html;
}

// c-jolts — national job openings RATE, monthly (JOLTS JOR).
// Was hardcoded under a dataset labelled "National (auto-updated)" while in fact
// updating never — it had drifted to 4.1 for Mar 2026 against an actual 4.2 and
// stopped two months short of the published data.
function updateJoltsChart(html, find) {
  const jor = monthsOf(find(JOLTS_SERIES.US_OPENINGS_RATE)).filter(p => p.year >= 2024);
  if (!jor.length) return html;
  html = inject(html, 'jolts-lab', axisLabels(jor));
  html = inject(html, 'jolts-nat', jor.map(p => p.value.toFixed(1)).join(','));
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
  const releaseSchedule = await loadReleaseSchedule();
  const { doc: vintageDoc, firstPrint } = await loadVintages();
  const addedVintages = [];
  const find = (id) => empSeries?.find(s => s.seriesID === id);

  // MA release dates go to the client, keyed the way renderDerived() keys months
  // and pre-formatted so the page never parses a date string (and so no browser
  // timezone can shift "2026-07-21" back to the 20th).
  //
  // Client-side deliberately: every MA figure in the prose is derived there from
  // the injected series, so the month those sentences describe is only settled in
  // the browser. Stamping the citation anywhere else lets the date and the figure
  // beside it disagree — which is exactly how all six MA citations came to read
  // "June 23, 2026" (the May vintage) under prose that had moved on to June data.
  html = inject(html, 'ma-rel-sched', '{' + Object.entries(releaseSchedule.state)
    .map(([key, iso]) => {
      const [y, m, d] = iso.split('-').map(Number);
      return `"${key}":"${FULLMON[m - 1]} ${d}, ${y}"`;
    })
    .join(',') + '}');

  // MA total nonfarm (SMS25000000000000001) is fetched twice — once in the
  // employment batch (3 years) and once in the sector batch (from 2019) — so
  // find() returns whichever landed first, which is the short one. Anything that
  // needs real history (annual Dec-to-Dec bars, full-year sums) must ask for the
  // longest copy explicitly.
  const findLong = (id) =>
    (empSeries || [])
      .filter(s => s.seriesID === id)
      .reduce((a, b) => ((b.data?.length || 0) > (a?.data?.length || 0) ? b : a), null);

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

  // Hero: national unemployment rate + its month. The hero replace above only
  // ever matched the MA card, so this stat stayed hardcoded at "4.3% (May 2026)"
  // while the auto values further down the page had already moved to 4.2% (Jun).
  if (data.us_unemployment_rate?.latest) {
    setField('hero-nat-ur', data.us_unemployment_rate.latest.value.toFixed(1) + '%');
    setField('hero-nat-mo', data.us_unemployment_rate.latest.date);
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
    setField('jolts-col-current',    date);
    if (ratio) {
      setField('jolts-ratio', ratio);
    } else {
      console.warn(`   ⚠️  JOLTS ratio skipped: no US unemployment level for ${period}`);
    }
    console.log(`   ✅ JOLTS fields updated: ${openingsM} (${date}), ratio ${ratio ?? 'n/a'} (both ${period})`);

    // ── JOLTS table — all five metrics, current month vs the SAME month a year
    // earlier. The year-ago column was a frozen "Mar 2025" while the current
    // column auto-advanced, so the "YoY Change" header above it had quietly come
    // to span 14 months; the four non-openings rows were hardcoded and had drifted
    // outright (5.6M hires against an actual 5.2M). Same-month pairing via
    // periodMap is the same fix the openings-per-unemployed ratio needed.
    const prevYear    = Number(data.us_job_openings.latest.year) - 1;
    const yrAgoPeriod = `${prevYear}-${data.us_job_openings.latest.period}`;
    const kFmt = (n) => (n < 0 ? '−' : '+') + Math.abs(Math.round(n)).toLocaleString('en-US') + 'K';
    setField('jolts-tbl-month', date);
    setField('jolts-col-prev',  `${data.us_job_openings.latest.periodName} ${prevYear}`);

    for (const [key, tag] of [
      ['US_JOB_OPENINGS', 'open'], ['US_HIRES', 'hire'], ['US_SEPARATIONS', 'sep'],
      ['US_QUITS', 'quit'], ['US_LAYOFFS', 'layoff'],
    ]) {
      const m    = periodMap(find(JOLTS_SERIES[key]));
      const cur  = m[period];
      const prev = m[yrAgoPeriod];
      if (cur == null) { console.warn(`   ⚠️  JOLTS ${key}: no value for ${period} — fields left as-is`); continue; }
      setField(`jolts-${tag}-cur`,  (cur / 1000).toFixed(1) + 'M');
      setField(`jolts-${tag}-prev`, prev == null ? '—' : (prev / 1000).toFixed(1) + 'M');
      setField(`jolts-${tag}-yoy`,  prev == null ? '—' : kFmt(cur - prev));
    }
    console.log(`   ✅ JOLTS table updated: ${period} vs ${yrAgoPeriod} (same calendar month)`);
  }

  // ── National Employment Situation block + table ───────────────────────────
  // National data leads MA state data by ~3 weeks, so this carries the newest
  // month. Figures are computed from the same SA series BLS headlines (payrolls,
  // U-3, U-6, household employment, labor force) — verifiable, no scraping.
  const nser  = (id) => monthsOf(find(id));
  const lastOf = (a) => a[a.length - 1];
  const prevOf = (a) => a[a.length - 2];
  const sgn = (n) => (n < 0 ? '−' : '+') + Math.abs(Math.round(n)).toLocaleString('en-US');
  const sgnK = (n) => (n < 0 ? '−' : '+') + Math.round(Math.abs(n) / 1000) + 'K';

  const nf = nser(EMPLOYMENT_SERIES.US_NONFARM);
  if (nf.length >= 3) {
    const cM = lastOf(nf), pM = prevOf(nf);
    // Two distinct dates that used to be the same value, which is what made the
    // old stamp wrong. relDate = the day BLS published this reference month.
    // runDate = the day this script last rewrote the page. Only the second one
    // is "today", and only the second one describes the auto-update itself.
    const relDate = releaseDateFor(releaseSchedule.national, cM.year, cM.mon, FULLMON);
    const runDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    if (!relDate) {
      console.log(`::warning::No BLS release date on file for ${FULLMON[cM.mon]} ${cM.year} — top up data/bls-release-schedule.json from https://www.bls.gov/schedule/news_release/empsit.htm`);
    }
    const relStamp = relDate || '—';
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
    setField('nat-emp-rel',   relStamp);
    setField('nat-emp-rel2',  relStamp);
    setField('nat-payrolls',  sgn(payCur));
    setField('nat-ur',        urCur.toFixed(1) + '%');
    setField('nat-ur-chg',    urChg);
    setField('nat-u6',        u6.length ? lastOf(u6).value.toFixed(1) + '%' : '—');
    setField('nat-hh',        sgn(hhCur));
    setField('nat-lf',        sgn(lfCur));
    // National Context table
    setField('nat-ctx-month', monLong(cM));
    setField('nat-ctx-rel',   relStamp);
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
    // ── Where the headline came from: CES industry breakdown ───────────────
    // The rows are additive to total nonfarm, so the reconciliation line under
    // the table is an actual check — if the industry rows stop summing to the
    // headline, it shows on the page instead of being asserted away.
    const secMonths = (key) => monthsOf(find(US_SECTOR_SERIES[key]));
    const secRows = buildSectorRows(secMonths, US_SECTOR_META);

    if (secRows.length) {
      setField('us-sec-month', monLong(cM));
      const cls = (n) => (n < 0 ? ' class="td-red"' : n > 0 ? ' class="td-green"' : '');
      html = injectHTMLBlock(html, 'us-sec-table', secRows.map(r =>
        `<tr><td>${r.label}</td><td${cls(r.chg)}>${sgn(r.chg)}</td>`
        + `<td>${Math.round(r.lvl).toLocaleString('en-US')}K</td></tr>`).join(''));

      const priv = momAdjacent(secMonths('PRIVATE'));
      const gov  = secRows.find(r => r.label === 'Government')?.chg;
      const summed = secRows.reduce((t, r) => t + r.chg, 0);
      // Stated, not assumed: if the parts ever stop adding to the headline, say so.
      const recon = summed === payCur
        ? `Private ${sgn(priv)} · Government ${sgn(gov)} · Total ${sgn(payCur)} — industry rows sum to the headline`
        : `Private ${sgn(priv)} · Government ${sgn(gov)} · rows sum to ${sgn(summed)} vs headline ${sgn(payCur)} — BLS rounds each industry independently`;
      setField('us-sec-recon', recon);
      console.log(`   ✅ US sector table: ${secRows.length} industries, private ${sgn(priv)}, gov ${sgn(gov)}, sum ${sgn(summed)} vs headline ${sgn(payCur)}`);
    }

    // ── What BLS has revised since first print ─────────────────────────────
    // BLS revises the prior two months with each release. Showing only the
    // current vintage silently rewrites history: May 2026 was first reported as
    // +172,000 and now stands at +63,000, and without this the month simply
    // reads as though it had always been +63,000.
    // Record the newest month's first print, once. ONLY the newest month is safe
    // to record: BLS revises on release, so within a cycle the newest month's
    // value is still exactly what was first published, and daily runs guarantee
    // we see it before the next release moves it. Backfilling an older month here
    // would store an already-revised figure as its "first print" and quietly
    // report a real revision as zero.
    const cmKey = `${cM.year}-${String(cM.mon + 1).padStart(2, '0')}`;
    if (firstPrint[cmKey] == null) {
      firstPrint[cmKey] = payCur;
      addedVintages.push(cmKey);
    }

    const revRows = buildRevisionRows(nf, firstPrint).map(r =>
      `<tr><td>${MON[r.mon]} ${r.year}</td>`
      + `<td>${r.first == null ? '—' : sgn(r.first)}</td><td>${sgn(r.now)}</td>`
      + `<td${r.rev == null ? '' : r.rev < 0 ? ' class="td-red"' : r.rev > 0 ? ' class="td-green"' : ''}>`
      + `${r.rev == null ? '—' : r.rev === 0 ? 'unrevised' : sgn(r.rev)}</td></tr>`);

    if (revRows.length) {
      html = injectHTMLBlock(html, 'us-rev-table', revRows.join(''));
      const tracked = Object.keys(firstPrint).length;
      setField('us-rev-note', tracked ? `Tracking ${tracked} months of first prints.` : '');
    }

    // "Headline aggregates auto-updated <date>" — this one really is the run
    // date; it describes this script, not the BLS release.
    setField('nat-src-date',  runDate);
    console.log(`   ✅ National block updated: ${monLong(cM)} — payrolls ${sgn(payCur)}, UR ${urCur}% ${urChg}, BLS released ${relStamp}`);
  }

  // Foreign-Born tab subtitle month
  const fbMonths = monthsOf(find(NATIVITY_SERIES.FB_EMP));
  if (fbMonths.length) {
    const p = fbMonths[fbMonths.length - 1];
    setField('nat-fb-month', `${MON[p.mon]} ${p.year}`);
  }

  // Foreign-Born tab stat cards. These were hardcoded to April 2026 while the
  // tab's own auto subtitle already read Jun 2026 — the foreign-born employed
  // card asserted 31.65M against a series that had moved to 30.73M (~920K out),
  // and native-born UR read 4.1% against an actual 4.6%. Levels and rates now
  // come from the series, and each year-ago figure is the SAME calendar month
  // rather than whatever each series' own latest happens to be.
  const natLbl  = (yr, mo) => `${MON[mo]} ${String(yr).slice(2)}`;
  const natStat = (id, tag, fmtVal, fmtDelta) => {
    const a = monthsOf(find(id));
    if (!a.length) { console.warn(`   ⚠️  nativity ${tag}: no data — fields left as-is`); return; }
    const cur  = a[a.length - 1];
    const prev = a.find(x => x.year === cur.year - 1 && x.mon === cur.mon);
    setField(`${tag}-mo`,  natLbl(cur.year, cur.mon));
    setField(`${tag}-val`, fmtVal(cur.value));
    setField(`${tag}-sub`, prev == null
      ? `no ${natLbl(cur.year - 1, cur.mon)} comparison published`
      : `${fmtDelta(cur.value - prev.value)} vs ${natLbl(cur.year - 1, cur.mon)}`);
  };
  const mFmt  = (v) => (v / 1000).toFixed(2) + 'M';
  const kDelt = (n) => (n < 0 ? '−' : '+') + Math.abs(Math.round(n)).toLocaleString('en-US') + 'K';
  const pFmt  = (v) => v.toFixed(1) + '%';
  const pDelt = (n) => (n < 0 ? '−' : '+') + Math.abs(n).toFixed(1) + ' pt';
  natStat(NATIVITY_SERIES.FB_EMP, 'nat-fbemp', mFmt, kDelt);
  natStat(NATIVITY_SERIES.NB_EMP, 'nat-nbemp', mFmt, kDelt);
  natStat(NATIVITY_SERIES.FB_UR,  'nat-fbur',  pFmt, pDelt);
  natStat(NATIVITY_SERIES.NB_UR,  'nat-nbur',  pFmt, pDelt);

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
    // Less-than-high-school completes the education table. Its three sibling rows
    // read from the c-gr-edu arrays client-side; this one has no chart line, so it
    // needs its own field — otherwise the table's "auto-update" caption is a lie
    // for a quarter of its rows.
    const lhs = grLast(GENDER_RACE_SERIES.UR_LESSHS);
    if (lhs) setField('gr-lhs-ur', lhs.value.toFixed(1) + '%');

    // c-gr-lfpr's trailing point. LFPR_MEN2554/LFPR_WOMEN2554 were fetched every
    // run and then dropped on the floor: the chart, the stat card and the table's
    // last row were all hardcoded, so the one row that actually moves was the one
    // nothing updated. Earlier points are settled annual averages and stay put.
    const pm = grLast(GENDER_RACE_SERIES.LFPR_MEN2554);
    const pw = grLast(GENDER_RACE_SERIES.LFPR_WOMEN2554);
    if (pm && pw) {
      html = inject(html, 'grlfpr-lab',   `'${MON[pm.mon]} ${String(pm.year).slice(2)}'`);
      html = inject(html, 'grlfpr-men',   pm.value.toFixed(1));
      html = inject(html, 'grlfpr-women', pw.value.toFixed(1));
    }
    if (wm) {
      setField('gr-wm-ur', wm.value.toFixed(1) + '%');
      if (all) {
        // Direction is derived, not baked in. This read `${gap} pt below national`
        // with "below" hardcoded, so the day White men's rate crossed the national
        // one it would have rendered "−0.2 pt below national" — a negative distance
        // in the wrong direction. Currently 0.7 pt below, but that is not a
        // property of the sentence.
        const gap = all.value - wm.value;
        setField('gr-wm-sub', `${Math.abs(gap).toFixed(1)} pt ${gap >= 0 ? 'below' : 'above'} national`);
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
    html = updateCharts(html, find, findLong);
    html = updateJobsAnnual(html, findLong);
    html = updateJoltsChart(html, find);
    html = updateNativity(html, find);
    html = updateGenderRace(html, find);
    html = updateMASectors(html, find);
    html = updateMASectorSpectrum(html, find);
  }

  // Footer provenance. Only the date used to be auto; the rest was hand-written
  // and had gone stale claiming the page "Reflects MA April 2026 release" long
  // after MA had moved to May and national to June — the footer contradicted the
  // very date stamped beside it. Both vintages are now read from the series.
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
  setField('foot-updated', today);
  if (data.ma_unemployment_rate?.latest) setField('foot-ma-mo',  data.ma_unemployment_rate.latest.date);
  if (data.us_unemployment_rate?.latest) setField('foot-nat-mo', data.us_unemployment_rate.latest.date);

  await saveNewVintages(vintageDoc, firstPrint, addedVintages);

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
    // Two years back, not one: the table's year-ago column needs the same
    // calendar month a year before the latest JOLTS month, and early in a year
    // that month falls into the year before last.
    const joltsSeries = await fetchBLSData(
      Object.values(JOLTS_SERIES),
      currentYear - 2,
      currentYear
    );
    empSeries.push(...joltsSeries);
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

  // ── 2e. US industry employment (non-critical — feeds the sector breakdown) ──
  console.log('\n🔄 Fetching US industry employment (CES national, SA)...');
  try {
    const usSectors = await fetchBLSData(Object.values(US_SECTOR_SERIES), currentYear - 1, currentYear);
    empSeries.push(...usSectors);
    const gov = usSectors.find(s => s.seriesID === US_SECTOR_SERIES.GOVERNMENT);
    console.log(`   ✅ US sectors fetched (${usSectors.length}) — Government latest ${getLatestValue(gov)?.value}K (${getLatestValue(gov)?.date})`);
  } catch (err) {
    console.warn(`   ⚠️  US sectors skipped: ${err.message}`);
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

export { monthsOf, inject, injectHTMLBlock, buildComparisonBox, CMP_TAGS, updateMASectorSpectrum, MA_SECTOR_SERIES, MA_SECTOR_META, loadReleaseSchedule, releaseDateFor, buildSectorRows, buildRevisionRows, momAdjacent, US_SECTOR_META };
