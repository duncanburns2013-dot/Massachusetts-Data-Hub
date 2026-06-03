#!/usr/bin/env node
// Pull 5-year SF sale-price distribution from MLS PIN via Bridge V2.
//
// For each of 5 geographies × 6 year-windows × 8 price buckets, hit the
// listings endpoint with limit=1 and read `total` — Bridge returns the
// matching count without us paging records. ~240 fast calls, ~20s total.
//
// Writes data/price-distribution-latest.json AND injects the JS literal
// between the PRICE_DIST_START / PRICE_DIST_END markers in
// ma-housing-dashboard.html.
//
// Requires: BRIDGE_TOKEN env var.

const fs    = require('fs');
const path  = require('path');
const https = require('https');

const TOKEN = process.env.BRIDGE_TOKEN;
if (!TOKEN) {
  console.error('BRIDGE_TOKEN env var not set');
  process.exit(1);
}

const REPO = __dirname;
const BASE = 'https://api.bridgedataoutput.com/api/v2/mlspin/listings';
const TODAY = new Date();
const CURRENT_YEAR = TODAY.getUTCFullYear();

// 8-bucket standard ladder (lower inclusive, upper exclusive; null = open)
const BUCKETS = [
  ['<250K',       null,        250_000],
  ['250-500K',    250_000,     500_000],
  ['500-750K',    500_000,     750_000],
  ['750K-1M',     750_000,   1_000_000],
  ['1-1.5M',    1_000_000,   1_500_000],
  ['1.5-2M',    1_500_000,   2_000_000],
  ['2-3M',      2_000_000,   3_000_000],
  ['3M+',       3_000_000,        null],
];

// 5 full prior years + current YTD
const YEARS = Array.from({length: 6}, (_, i) => CURRENT_YEAR - 5 + i);
const YTD_LABEL = `${CURRENT_YEAR} YTD`;

const GN_TOWNS = ['Newburyport','Amesbury','Salisbury','Newbury','Rowley','West Newbury'];

const GEOS = {
  ma:     { label: 'Massachusetts',       filter: { 'StateOrProvince.in': 'MA' } },
  boston: { label: 'Boston',              filter: { 'StateOrProvince.in': 'MA', 'City.in': 'Boston' } },
  essex:  { label: 'Essex County',        filter: { 'StateOrProvince.in': 'MA', 'CountyOrParish.in': 'Essex' } },
  gn:     { label: 'Greater Newburyport', filter: { 'StateOrProvince.in': 'MA', 'City.in': GN_TOWNS.join(',') } },
  nbpt:   { label: 'Newburyport',         filter: { 'StateOrProvince.in': 'MA', 'City.in': 'Newburyport' } },
};

const PT_FILTER = {
  'StandardStatus.in':  'Closed',
  'PropertyType.in':    'Residential',
  'PropertySubType.in': 'Single Family Residence',
};

function ymd(d) { return d.toISOString().slice(0, 10); }
function yearWindow(yr) {
  const start = new Date(Date.UTC(yr, 0, 1));
  let end = new Date(Date.UTC(yr + 1, 0, 1));
  const tomorrow = new Date(Date.UTC(
    TODAY.getUTCFullYear(), TODAY.getUTCMonth(), TODAY.getUTCDate() + 1));
  if (end > tomorrow) end = tomorrow;
  return [ymd(start), ymd(end)];
}

function bucketFilter(low, high) {
  const f = {};
  if (low  != null) f['ClosePrice.gte'] = low;
  if (high != null) f['ClosePrice.lt']  = high;
  return f;
}

function getTotal(params, maxRetries = 8) {
  return new Promise((resolve, reject) => {
    const qs = new URLSearchParams({ ...params, limit: 1, fields: 'ListingId' }).toString();
    const url = `${BASE}?${qs}`;
    const attempt = (n) => {
      const req = https.get(url, {
        timeout: 30000,
        headers: { Authorization: `Bearer ${TOKEN}`, 'User-Agent': 'MA-Data-Hub/PriceDist/1.0' }
      }, (res) => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => {
          if (res.statusCode >= 400) {
            // Retry on 429 (rate-limited) and any 5xx. Exponential backoff with jitter so
            // 8 parallel workers don't all wake up and resend simultaneously.
            if ((res.statusCode === 429 || res.statusCode >= 500) && n < maxRetries) {
              const wait = Math.min(60000, Math.pow(2, n) * 1000) + Math.random() * 1000;
              return setTimeout(() => attempt(n + 1), wait);
            }
            return reject(new Error(`HTTP ${res.statusCode} after ${n+1} attempts: ${body.slice(0, 200)}`));
          }
          try {
            const data = JSON.parse(body);
            resolve(Number(data.total) || 0);
          } catch (e) { reject(e); }
        });
      });
      req.on('error', (e) => {
        if (n < maxRetries) {
          const wait = Math.min(60000, Math.pow(2, n) * 1000) + Math.random() * 1000;
          setTimeout(() => attempt(n + 1), wait);
        } else reject(e);
      });
      req.on('timeout', () => { req.destroy(new Error('socket timeout')); });
    };
    attempt(0);
  });
}

// Simple pool limit so we don't slam Bridge. 4 workers keeps us well clear
// of Bridge's per-second cap even when the queue is hot.
async function pool(items, worker, limit = 4) {
  const out = new Array(items.length);
  let i = 0;
  async function next() {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await worker(items[idx], idx);
    }
  }
  await Promise.all(Array.from({length: limit}, next));
  return out;
}

(async () => {
  // Build job list
  const jobs = [];
  for (const gk of Object.keys(GEOS)) {
    for (const yr of YEARS) {
      for (const [bl, low, high] of BUCKETS) {
        jobs.push({ gk, yr, bl, low, high });
      }
    }
  }
  console.log(`[price-dist] ${jobs.length} count queries (${Object.keys(GEOS).length} geos × ${YEARS.length} years × ${BUCKETS.length} buckets)`);

  // results[gk][yr][bl] = count
  const results = {};
  for (const gk of Object.keys(GEOS)) {
    results[gk] = {};
    for (const yr of YEARS) results[gk][yr] = {};
  }

  let done = 0;
  const t0 = Date.now();
  await pool(jobs, async (j) => {
    const [start, end] = yearWindow(j.yr);
    const params = {
      ...PT_FILTER,
      ...GEOS[j.gk].filter,
      ...bucketFilter(j.low, j.high),
      'CloseDate.gte': start,
      'CloseDate.lt':  end,
    };
    const n = await getTotal(params);
    results[j.gk][j.yr][j.bl] = n;
    done++;
    if (done % 20 === 0 || done === jobs.length) {
      console.log(`  [${done}/${jobs.length}] ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
  }, 4);
  console.log(`[price-dist] all counts fetched in ${((Date.now() - t0) / 1000).toFixed(1)}s\n`);

  const bucketLabels = BUCKETS.map(b => b[0]);
  const yearLabels = YEARS.map(y => y === CURRENT_YEAR ? YTD_LABEL : String(y));

  const payload = {
    meta: {
      generated:     TODAY.toISOString().slice(0, 10),
      source:        'MLS PIN via Bridge Data Output',
      property_type: 'Single Family Residence (Residential)',
      buckets:       bucketLabels,
      year_labels:   yearLabels,
      years:         YEARS,
    },
    geos: {},
  };
  for (const gk of Object.keys(GEOS)) {
    const counts = YEARS.map(yr => bucketLabels.map(bl => results[gk][yr][bl] ?? 0));
    payload.geos[gk] = {
      label:  GEOS[gk].label,
      counts,
      totals: counts.map(row => row.reduce((a, b) => a + b, 0)),
    };
  }

  // ---- write JSON ----
  fs.mkdirSync(path.join(REPO, 'data'), { recursive: true });
  const outJson = path.join(REPO, 'data', 'price-distribution-latest.json');
  fs.writeFileSync(outJson, JSON.stringify(payload, null, 2));
  console.log(`[price-dist] wrote ${path.relative(REPO, outJson)} (${Math.round(fs.statSync(outJson).size / 1024)} KB)`);

  // ---- inject into dashboard ----
  const dash = path.join(REPO, 'ma-housing-dashboard.html');
  const START = '/* PRICE_DIST_START */';
  const END   = '/* PRICE_DIST_END */';
  const jsLit = 'const priceDist = ' + JSON.stringify(payload) + ';';
  const html = fs.readFileSync(dash, 'utf8');
  if (html.includes(START) && html.includes(END)) {
    const escRe = s => s.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&');
    const pat = new RegExp(escRe(START) + '[\\s\\S]*?' + escRe(END));
    const newHtml = html.replace(pat, START + jsLit + END);
    if (newHtml === html) {
      console.error('[price-dist] marker substitution made no change — aborting write');
      process.exit(1);
    }
    fs.writeFileSync(dash, newHtml);
    console.log(`[price-dist] injected data block into ${path.basename(dash)}`);
  } else {
    console.log(`[price-dist] WARN: ${START}/${END} markers not found in ${path.basename(dash)} — JSON only`);
  }

  // ---- summary print ----
  console.log('\n[price-dist] Distribution shift — 5 years ago vs. current YTD');
  console.log(`  ${'Geography'.padEnd(22)} ${'Bucket'.padEnd(12)} ${'5y ago %'.padStart(10)} ${'Now %'.padStart(10)}  Shift`);
  for (const gk of Object.keys(GEOS)) {
    const g = payload.geos[gk];
    const t0p = Math.max(g.totals[0], 1);
    const tLast = Math.max(g.totals[g.totals.length - 1], 1);
    for (let i = 0; i < bucketLabels.length; i++) {
      const p0 = 100 * g.counts[0][i] / t0p;
      const pL = 100 * g.counts[g.counts.length - 1][i] / tLast;
      const sh = pL - p0;
      const arrow = sh > 0.5 ? '↑' : (sh < -0.5 ? '↓' : ' ');
      console.log(`  ${g.label.padEnd(22)} ${bucketLabels[i].padEnd(12)} ${p0.toFixed(1).padStart(9)}% ${pL.toFixed(1).padStart(9)}%   ${arrow}${Math.abs(sh).toFixed(1).padStart(4)}`);
    }
    console.log(`  ${g.label.padEnd(22)} ${'TOTAL'.padEnd(12)} ${String(g.totals[0]).padStart(10)} ${String(g.totals[g.totals.length-1]).padStart(10)}\n`);
  }
  console.log('[price-dist] Done.');
})().catch(e => { console.error('FAILED:', e); process.exit(1); });
