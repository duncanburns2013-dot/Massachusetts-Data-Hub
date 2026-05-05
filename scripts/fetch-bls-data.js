import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_PATH = path.join(__dirname, '..', 'employment-dashboard.html');
const DATA_OUTPUT_PATH = path.join(__dirname, '..', 'data', 'employment-latest.json');

// ── Series IDs ────────────────────────────────────────────────────────────────
const EMPLOYMENT_SERIES = {
  MA_UNEMPLOYMENT_RATE:  'LASST250000000000003',
  MA_UNEMPLOYMENT_LEVEL: 'LASST250000000000004',
  MA_LABOR_FORCE:        'LASST250000000000006',
  MA_TOTAL_NONFARM:      'SMS25000000000000001',
  US_UNEMPLOYMENT_RATE:  'LNS14000000',
};

// National JOLTS only — BLS discontinued monthly STATE JOLTS (last: Dec 2025).
// First annual state JOLTS release: July 2026.
const JOLTS_SERIES = {
  US_JOB_OPENINGS: 'JTS000000000000000JOL',
};

const BLS_API_BASE = 'https://api.bls.gov/publicAPI/v2/timeseries/data/';
const API_KEY      = process.env.BLS_API_KEY || '';
const TIMEOUT_MS   = 20000; // 20 seconds per request

// ── Helpers ───────────────────────────────────────────────────────────────────
async function fetchBLSData(seriesIds, startYear, endYear) {
  const payload = {
    seriesid: seriesIds,
    startyear: String(startYear),
    endyear: String(endYear),
    calculations: true,
  };
  if (API_KEY) payload.registrationkey = API_KEY;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(BLS_API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timer);

    const data = await response.json();
    if (data.status !== 'REQUEST_SUCCEEDED') {
      throw new Error(`BLS API error: ${data.message?.join(', ')}`);
    }
    return data.Results.series;

  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error(`BLS API timed out after ${TIMEOUT_MS / 1000}s`);
    }
    throw err;
  }
}

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

// ── Dashboard updater ─────────────────────────────────────────────────────────
async function updateDashboard(data) {
  let html = await fs.readFile(DASHBOARD_PATH, 'utf-8');

  // Helper: update any element by data-field attribute value
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

  // JOLTS national openings — updates stat cards and table via data-field anchors
  if (data.us_job_openings?.latest) {
    const v = data.us_job_openings.latest.value;
    const openingsM = (v / 1000).toFixed(1) + 'M';
    const date = data.us_job_openings.latest.date;
    const unemployed = data.ma_unemployment_level?.latest?.value ?? 186000;
    const ratio = (v / unemployed).toFixed(2);
    setField('jolts-openings', openingsM);
    setField('jolts-openings-date', `${date} · auto-updated`);
    setField('jolts-openings-table', openingsM);
    setField('jolts-col-current', date);
    setField('jolts-ratio', ratio);
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
  console.log('🔄 Fetching BLS employment data...');
  const currentYear = new Date().getFullYear();
  let joltsData = null;

  // 1. Employment series — these are critical; fail hard if they break
  const empSeries = await fetchBLSData(
    Object.values(EMPLOYMENT_SERIES),
    currentYear - 2,
    currentYear
  );
  const findSeries = (id) => empSeries.find(s => s.seriesID === id);

  const data = {
    fetched_at:           new Date().toISOString(),
    ma_unemployment_rate:  { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_RATE)) },
    ma_unemployment_level: { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_UNEMPLOYMENT_LEVEL)) },
    ma_labor_force:        { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_LABOR_FORCE)) },
    ma_total_nonfarm:      { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.MA_TOTAL_NONFARM)) },
    us_unemployment_rate:  { latest: getLatestValue(findSeries(EMPLOYMENT_SERIES.US_UNEMPLOYMENT_RATE)) },
    us_job_openings:       null, // filled in below if JOLTS succeeds
    jolts_note: 'BLS discontinued monthly state JOLTS in 2026. National JOLTS still monthly. First annual state release: July 2026.',
  };

  console.log(`   ✅ MA Unemployment: ${data.ma_unemployment_rate.latest?.value}% (${data.ma_unemployment_rate.latest?.date})`);
  console.log(`   ✅ US Unemployment: ${data.us_unemployment_rate.latest?.value}%`);
  console.log(`   ✅ MA Nonfarm Payrolls: ${data.ma_total_nonfarm.latest?.value?.toLocaleString()} (${data.ma_total_nonfarm.latest?.date})`);

  // 2. JOLTS — national only, non-critical; skip gracefully on failure
  console.log('\n🔄 Fetching JOLTS data (national only)...');
  try {
    const joltsSeries = await fetchBLSData(
      Object.values(JOLTS_SERIES),
      currentYear - 1,
      currentYear
    );
    const jolts = joltsSeries.find(s => s.seriesID === JOLTS_SERIES.US_JOB_OPENINGS);
    data.us_job_openings = { latest: getLatestValue(jolts) };
    console.log(`   ✅ US Job Openings: ${(data.us_job_openings.latest?.value / 1000).toFixed(0)}K (${data.us_job_openings.latest?.date})`);
  } catch (err) {
    // Non-fatal — employment dashboard still updates without JOLTS
    console.warn(`   ⚠️  JOLTS fetch skipped: ${err.message}`);
    console.warn('   Dashboard will update without JOLTS data.');
    data.jolts_error = err.message;
  }

  // 3. Write JSON snapshot
  await fs.mkdir(path.dirname(DATA_OUTPUT_PATH), { recursive: true });
  await fs.writeFile(DATA_OUTPUT_PATH, JSON.stringify(data, null, 2));
  console.log('\n💾 Saved data/employment-latest.json');

  // 4. Patch dashboard HTML
  const updatedHtml = await updateDashboard(data);
  await fs.writeFile(DASHBOARD_PATH, updatedHtml);
  console.log('📄 Updated employment-dashboard.html');

  console.log('\n✨ Done!');
}

main().catch(e => {
  console.error('❌ Fatal error:', e.message);
  process.exit(1);
});
