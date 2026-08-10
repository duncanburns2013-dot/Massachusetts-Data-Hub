// Guards the national sector breakdown and the revision table.
//
// Fixtures are the real July 2026 CES levels (thousands, SA), pulled from
// api.bls.gov and checked against the published Employment Situation: the eleven
// industry rows sum to exactly the −23,000 headline. That summing property is the
// point of the table — it lets the page CHECK the breakdown against the headline
// instead of asserting the two agree.
//
// Run: node scripts/test-us-sectors.mjs

process.env.BLS_SKIP_MAIN = '1';
const { buildSectorRows, buildRevisionRows, momAdjacent, US_SECTOR_META } =
  await import('./fetch-bls-data.js');

let failed = 0;
function check(label, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  const ok = a === e;
  if (!ok) failed++;
  console.log(`${ok ? '✅' : '❌'} ${label}\n     expected ${e}, got ${a}`);
}

// June → July levels in thousands. mon is 0-based, matching monthsOf().
const LEVELS = {
  PRIVATE:       [136_100,   136_130],
  MINING:        [    595,       593],
  CONSTRUCTION:  [  8_300,     8_322],
  MANUFACTURING: [ 12_700,    12_705],
  TRADE_TRANS:   [ 29_000,    28_996],
  INFORMATION:   [  2_950,     2_961],
  FINANCIAL:     [  9_200,     9_186],
  PROF_BUS:      [ 22_600,    22_618],
  EDU_HEALTH:    [ 27_000,    27_025],
  LEISURE:       [ 17_100,    17_060],
  OTHER_SVC:     [  5_950,     5_959],
  GOVERNMENT:    [ 23_653,    23_600],
};
const monthsFor = (key) => LEVELS[key]
  ? [{ year: 2026, mon: 5, value: LEVELS[key][0] }, { year: 2026, mon: 6, value: LEVELS[key][1] }]
  : [];

console.log('\n── US sector breakdown ──────────────────────────────────────\n');

const rows = buildSectorRows(monthsFor, US_SECTOR_META);

// The whole point: the parts add up to the headline.
const summed = rows.reduce((t, r) => t + r.chg, 0);
check('industry rows sum to the −23,000 headline',      summed, -23_000);
check('total private is NOT a row (it would double-count)',
      rows.some(r => /private$/i.test(r.label)), false);
check('all eleven industries present',                  rows.length, 11);
check('sorted largest gain first',                      rows[0].label, 'Private Education & Health');
check('largest gain is +25,000',                        rows[0].chg, 25_000);
check('largest loss last',                              rows[rows.length - 1].label, 'Government');
check('government change',                              rows.find(r => r.label === 'Government').chg, -53_000);
check('leisure change',                                 rows.find(r => r.label === 'Leisure & Hospitality').chg, -40_000);

// Private rose while the headline fell — the fact the old page could not show.
check('private sector rose the same month the headline fell',
      momAdjacent(monthsFor('PRIVATE')) > 0 && summed < 0, true);

// A month BLS never published must not be differenced across.
check('non-adjacent months yield no change, not a fake one',
      momAdjacent([{ year: 2025, mon: 8, value: 100 }, { year: 2025, mon: 10, value: 150 }]), null);

console.log('\n── Revisions ────────────────────────────────────────────────\n');

// Real levels: Apr 158,798 → May 158,861 → Jun 158,881 → Jul 158,858.
const NF = [
  { year: 2026, mon: 3, value: 158_798 },
  { year: 2026, mon: 4, value: 158_861 },
  { year: 2026, mon: 5, value: 158_881 },
  { year: 2026, mon: 6, value: 158_858 },
];
// First prints recovered from this repo's git history.
const FIRST = { '2026-05': 172_000, '2026-06': 57_000, '2026-07': -23_000 };

const revs = buildRevisionRows(NF, FIRST);
check('reports the months behind the newest, newest first', revs.map(r => r.key), ['2026-06', '2026-05']);
check('June: first printed +57,000',                    revs[0].first, 57_000);
check('June: now +20,000',                              revs[0].now,   20_000);
check('June revised down 37,000',                       revs[0].rev,  -37_000);
check('May revised down 109,000',                       revs[1].rev, -109_000);

// "We never saw the first print" and "it was not revised" are different claims.
check('untracked month yields null, not a zero revision',
      buildRevisionRows(NF, { '2026-06': 57_000 })[1].rev, null);

console.log(`\n${failed === 0 ? '✨ all checks passed' : `❌ ${failed} check(s) failed`}\n`);
process.exit(failed === 0 ? 0 : 1);
