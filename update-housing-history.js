#!/usr/bin/env node
// Pull long-run MA housing indices from FRED:
//   BOXRSA  — S&P/Case-Shiller MA-Boston Home Price Index, monthly, 1987-
//   MASTHPI — FHFA All-Transactions HPI for Massachusetts, quarterly, 1975-
//
// Computes inflation-adjusted ("real") series via CUUR0000SA0 (CPI-U) and
// writes both nominal + real, indexed to 100 at Jan-2000 for comparability.
// Injects between HOUSING_HISTORY markers in ma-housing-dashboard.html and
// also writes data/housing-history-latest.json.
//
// Requires: FRED_API_KEY env var.

const fs    = require('fs');
const path  = require('path');
const https = require('https');

const KEY = process.env.FRED_API_KEY;
if (!KEY) {
  // Don't fail the whole workflow over a missing optional secret — the price-
  // distribution data is the main payload, and the historical panel falls back
  // to whatever was last baked in.
  console.warn('[housing-history] FRED_API_KEY not set — skipping refresh, panel keeps prior values');
  process.exit(0);
}

const REPO = __dirname;
const FRED = 'https://api.stlouisfed.org/fred/series/observations';

const SERIES = {
  boxrsa:  { id: 'BOXRSA',  start: '1987-01-01', label: 'Case-Shiller Boston (monthly, NSA)' },
  masthpi: { id: 'MASTHPI', start: '1975-01-01', label: 'FHFA MA All-Transactions HPI (quarterly, NSA)' },
  cpi:     { id: 'CPIAUCSL',    start: '1975-01-01', label: 'CPI-U All Items (monthly, SA)' },
};

function getJson(url, maxRetries = 4) {
  return new Promise((resolve, reject) => {
    const attempt = (n) => {
      const req = https.get(url, { headers: { 'User-Agent': 'MA-Data-Hub/HousingHistory/1.0' } }, (res) => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => {
          if (res.statusCode >= 400) {
            if ((res.statusCode === 429 || res.statusCode >= 500) && n < maxRetries) {
              return setTimeout(() => attempt(n + 1), 1500 * (n + 1));
            }
            return reject(new Error(`HTTP ${res.statusCode}: ${body.slice(0, 200)}`));
          }
          try { resolve(JSON.parse(body)); } catch (e) { reject(e); }
        });
      });
      req.on('error', (e) => n < maxRetries ? setTimeout(() => attempt(n + 1), 1500 * (n + 1)) : reject(e));
    };
    attempt(0);
  });
}

class InvalidKeyError extends Error {}

async function fetchSeries(id, start) {
  const url = `${FRED}?series_id=${id}&api_key=${KEY}&file_type=json&observation_start=${start}`;
  let j;
  try {
    j = await getJson(url);
  } catch (e) {
    // FRED returns HTTP 400 with "api_key is not registered" for an invalid/
    // rotated key. Mark this as recoverable so the caller can skip cleanly.
    if (/HTTP 400/.test(e.message) && /api_key/i.test(e.message)) {
      throw new InvalidKeyError(e.message);
    }
    throw e;
  }
  return j.observations
    .filter(o => o.value && o.value !== '.')
    .map(o => ({ d: o.date, v: +o.value }));
}

// Rebase a series so that the value at (or nearest to) anchorDate = 100.
function rebase(series, anchorDate) {
  const anchor = series.find(p => p.d >= anchorDate) || series[0];
  const base = anchor.v;
  return series.map(p => ({ d: p.d, v: +(100 * p.v / base).toFixed(2) }));
}

// Deflate `series` (nominal) by `cpi` so all values are in current ($today) dollars.
// Both must be sorted ascending by date.
function realize(series, cpi) {
  const cpiMap = new Map(cpi.map(p => [p.d.slice(0, 7), p.v])); // YYYY-MM key
  const latestCpi = cpi[cpi.length - 1].v;
  return series.map(p => {
    const ym = p.d.slice(0, 7);
    let c = cpiMap.get(ym);
    if (c == null) {
      // For quarterly series, the CPI of that month may not align — walk back up to 3 months
      const [y, m] = ym.split('-').map(Number);
      for (let back = 1; back <= 3; back++) {
        const md = new Date(Date.UTC(y, m - 1 - back, 1));
        const k = md.toISOString().slice(0, 7);
        c = cpiMap.get(k);
        if (c != null) break;
      }
    }
    if (c == null) return null;
    return { d: p.d, v: +(p.v * latestCpi / c).toFixed(2) };
  }).filter(Boolean);
}

// Compress monthly to a smaller payload — keep every Nth point, plus every endpoint.
// For 39 years × 12 months = ~468 points, keeping every 3rd gives ~160 — plenty for a chart.
function decimate(series, every) {
  if (series.length <= 12) return series;
  const out = [];
  for (let i = 0; i < series.length; i += every) out.push(series[i]);
  if (out[out.length - 1] !== series[series.length - 1]) out.push(series[series.length - 1]);
  return out;
}

(async () => {
  console.log('[housing-history] fetching FRED series…');
  let boxrsaRaw, masthpiRaw, cpiRaw;
  try {
    [boxrsaRaw, masthpiRaw, cpiRaw] = await Promise.all([
      fetchSeries(SERIES.boxrsa.id,  SERIES.boxrsa.start),
      fetchSeries(SERIES.masthpi.id, SERIES.masthpi.start),
      fetchSeries(SERIES.cpi.id,     SERIES.cpi.start),
    ]);
  } catch (e) {
    if (e instanceof InvalidKeyError) {
      console.warn('[housing-history] FRED rejected api_key — skipping refresh, panel keeps prior values');
      console.warn('  (rotate FRED_API_KEY repo secret at github.com/<owner>/<repo>/settings/secrets/actions)');
      process.exit(0);
    }
    throw e;
  }
  console.log(`  BOXRSA:  ${boxrsaRaw.length} monthly obs (${boxrsaRaw[0].d} → ${boxrsaRaw[boxrsaRaw.length-1].d})`);
  console.log(`  MASTHPI: ${masthpiRaw.length} quarterly obs (${masthpiRaw[0].d} → ${masthpiRaw[masthpiRaw.length-1].d})`);
  console.log(`  CPI:     ${cpiRaw.length} monthly obs`);

  // Real (inflation-adjusted) versions, both expressed in present-day dollars
  const boxrsaReal  = realize(boxrsaRaw,  cpiRaw);
  const masthpiReal = realize(masthpiRaw, cpiRaw);

  // Rebase everything to Jan-2000 = 100 for cross-series comparability.
  // (Case-Shiller is already Jan-2000 = 100; FHFA is 1991-Q1 = 100. Rebasing
  // both to Jan-2000 lets users compare apples-to-apples.)
  const anchor = '2000-01-01';
  const out = {
    meta: {
      generated:  new Date().toISOString().slice(0, 10),
      anchor:     anchor,
      sources: {
        BOXRSA:     'S&P/Case-Shiller MA-Boston Home Price Index, FRED',
        MASTHPI:    'FHFA All-Transactions HPI for Massachusetts, FRED',
        CPIAUCSL:   'CPI-U All Items, BLS via FRED',
      },
      latest_cpi: cpiRaw[cpiRaw.length - 1].v,
      latest_cpi_date: cpiRaw[cpiRaw.length - 1].d,
    },
    nominal: {
      boxrsa:  decimate(rebase(boxrsaRaw,  anchor), 1),
      masthpi: decimate(rebase(masthpiRaw, anchor), 1),
    },
    real: {
      boxrsa:  decimate(rebase(boxrsaReal,  anchor), 1),
      masthpi: decimate(rebase(masthpiReal, anchor), 1),
    },
  };

  // ---- write JSON ----
  fs.mkdirSync(path.join(REPO, 'data'), { recursive: true });
  const outJson = path.join(REPO, 'data', 'housing-history-latest.json');
  fs.writeFileSync(outJson, JSON.stringify(out, null, 2));
  console.log(`[housing-history] wrote ${path.relative(REPO, outJson)} (${Math.round(fs.statSync(outJson).size / 1024)} KB)`);

  // ---- inject into dashboard ----
  const dash = path.join(REPO, 'ma-housing-dashboard.html');
  const START = '/* HOUSING_HISTORY_START */';
  const END   = '/* HOUSING_HISTORY_END */';
  const jsLit = 'const housingHistory = ' + JSON.stringify(out) + ';';
  const html = fs.readFileSync(dash, 'utf8');
  if (html.includes(START) && html.includes(END)) {
    const escRe = s => s.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&');
    const pat = new RegExp(escRe(START) + '[\\s\\S]*?' + escRe(END));
    const newHtml = html.replace(pat, START + jsLit + END);
    if (newHtml === html) {
      console.error('[housing-history] marker substitution made no change — aborting write');
      process.exit(1);
    }
    fs.writeFileSync(dash, newHtml);
    console.log(`[housing-history] injected into ${path.basename(dash)}`);
  } else {
    console.log(`[housing-history] WARN: ${START}/${END} markers not in ${path.basename(dash)} — JSON only`);
  }

  // ---- analyze: peak/trough/spike characterization ----
  const real = out.real.boxrsa;
  function peakIn(start, end) {
    let p = { d: null, v: -Infinity };
    for (const r of real) if (r.d >= start && r.d <= end && r.v > p.v) p = r;
    return p;
  }
  function troughIn(start, end) {
    let p = { d: null, v: Infinity };
    for (const r of real) if (r.d >= start && r.d <= end && r.v < p.v) p = r;
    return p;
  }
  const cycles = [
    { name: '1989 peak → 1992 trough', peak: peakIn('1987-01-01', '1991-12-31'), trough: troughIn('1990-01-01', '1995-12-31') },
    { name: '2006 peak → 2009 trough', peak: peakIn('2004-01-01', '2007-12-31'), trough: troughIn('2007-01-01', '2012-12-31') },
    { name: '2020 → today',           peak: peakIn('2024-01-01', '2026-12-31'), trough: troughIn('2019-01-01', '2020-06-30') },
  ];
  console.log('\n[housing-history] Real (inflation-adjusted) cycle analysis:');
  for (const c of cycles) {
    const dropOrRise = c.trough.v < c.peak.v ? 'drop' : 'rise';
    const pct = ((c.peak.v - c.trough.v) / Math.min(c.peak.v, c.trough.v)) * 100;
    console.log(`  ${c.name}: peak ${c.peak.v} (${c.peak.d}) ↔ trough ${c.trough.v} (${c.trough.d}) — ${dropOrRise} ${Math.abs(pct).toFixed(1)}%`);
  }
  console.log('[housing-history] Done.');
})().catch(e => { console.error('FAILED:', e); process.exit(1); });
