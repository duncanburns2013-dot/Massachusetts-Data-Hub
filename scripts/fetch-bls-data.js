import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_PATH = path.join(__dirname, '..', 'employment-dashboard.html');
const DATA_OUTPUT_PATH = path.join(__dirname, '..', 'data', 'employment-latest.json');

const SERIES = {
  MA_UNEMPLOYMENT_RATE: 'LASST250000000000003',
  MA_UNEMPLOYMENT_LEVEL: 'LASST250000000000004',
  MA_LABOR_FORCE: 'LASST250000000000006',
  MA_TOTAL_NONFARM: 'SMS25000000000000001',
  US_UNEMPLOYMENT_RATE: 'LNS14000000',
  US_JOB_OPENINGS: 'JTS000000000000000JOL',
};

const BLS_API_BASE = 'https://api.bls.gov/publicAPI/v2/timeseries/data/';
const API_KEY = process.env.BLS_API_KEY || '';

async function fetchBLSData(seriesIds, startYear, endYear) {
  const payload = {
    seriesid: seriesIds,
    startyear: String(startYear),
    endyear: String(endYear),
    calculations: true,
  };
  if (API_KEY) payload.registrationkey = API_KEY;
  
  const response = await fetch(BLS_API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  
  const data = await response.json();
  if (data.status !== 'REQUEST_SUCCEEDED') {
    throw new Error(`BLS API failed: ${data.message?.join(', ')}`);
  }
  return data.Results.series;
}

function getLatestValue(series) {
  if (!series?.data?.length) return null;
  const latest = series.data[0];
  return {
    value: parseFloat(latest.value),
    year: latest.year,
    period: latest.period,
    periodName: latest.periodName,
    date: `${latest.periodName} ${latest.year}`,
  };
}

async function updateDashboard(data) {
  let html = await fs.readFile(DASHBOARD_PATH, 'utf-8');
  
  // Update hero stat for MA unemployment
  if (data.ma_unemployment_rate?.latest) {
    const rate = data.ma_unemployment_rate.latest.value.toFixed(1);
    const date = data.ma_unemployment_rate.latest.date;
    html = html.replace(
      /(<div class="hero-stat"><div class="val[^"]*">)[\d.]+%(<\/div><div class="lbl">MA Unemployment[^<]*<\/div><\/div>)/,
      `$1${rate}%</div><div class="lbl">MA Unemployment (${date})</div></div>`
    );
  }
  
  // Update footer date
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  html = html.replace(/Updated [^·]+·/, `Updated ${today} ·`);
  
  return html;
}

async function main() {
  console.log('🔄 Fetching BLS data...\n');
  const currentYear = new Date().getFullYear();
  
  const series = await fetchBLSData(Object.values(SERIES), currentYear - 2, currentYear);
  const findSeries = (id) => series.find(s => s.seriesID === id);
  
  const data = {
    fetched_at: new Date().toISOString(),
    ma_unemployment_rate: { latest: getLatestValue(findSeries(SERIES.MA_UNEMPLOYMENT_RATE)) },
    ma_labor_force: { latest: getLatestValue(findSeries(SERIES.MA_LABOR_FORCE)) },
    ma_total_nonfarm: { latest: getLatestValue(findSeries(SERIES.MA_TOTAL_NONFARM)) },
    us_unemployment_rate: { latest: getLatestValue(findSeries(SERIES.US_UNEMPLOYMENT_RATE)) },
    us_job_openings: { latest: getLatestValue(findSeries(SERIES.US_JOB_OPENINGS)) },
  };
  
  console.log('📈 Latest values:');
  console.log(`   MA Unemployment: ${data.ma_unemployment_rate.latest?.value}% (${data.ma_unemployment_rate.latest?.date})`);
  console.log(`   US Unemployment: ${data.us_unemployment_rate.latest?.value}%`);
  
  await fs.mkdir(path.dirname(DATA_OUTPUT_PATH), { recursive: true });
  await fs.writeFile(DATA_OUTPUT_PATH, JSON.stringify(data, null, 2));
  
  const updatedHtml = await updateDashboard(data);
  await fs.writeFile(DASHBOARD_PATH, updatedHtml);
  
  console.log('\n✨ Done!');
}

main().catch(e => { console.error('❌', e.message); process.exit(1); });
