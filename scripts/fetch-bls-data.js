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
};

// National JOLTS only — BLS discontinued monthly state JOLTS (last: Dec 2025).
// First annual state JOLTS release: July 2026.
const JOLTS_SERIES = {
  US_JOB_OPENINGS: 'JTS000000000000000JOL',
};

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

// ── Dashboard updater ─────────────────────────────────────────────────────────
async function updateDashboard(data) {
  let html = await fs.readFile(DASHBOARD_PATH, 'utf-8');

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
    const unemployed = data.ma_unemployment_level?.latest?.value ?? 186000;
    const ratio      = (v / unemployed).toFixed(2);
    setField('jolts-openings',       openingsM);
    setField('jolts-openings-date',  `${date} · auto-updated`);
    setField('jolts-openings-table', openingsM);
    setField('jolts-col-current',    date);
    setField('jolts-ratio',          ratio);
    console.log(`   ✅ JOLTS fields updated: ${openingsM} (${date})`);
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
  const updatedHtml = await updateDashboard(data);
  await fs.writeFile(DASHBOARD_PATH, updatedHtml);
  console.log('📄 Updated employment-dashboard.html');

  console.log('\n✨ Done!');
}

main().catch(e => {
  console.error('❌ Fatal error:', e.message);
  process.exit(1);
});
