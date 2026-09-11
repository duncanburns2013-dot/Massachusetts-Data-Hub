// Guards the two MA metro charts on the MA Regions tab.
//
// These were inline literals frozen at April 2026 -- headings, bars and the
// paragraph beneath them all describing a month the data had left three months
// earlier. Nothing failed; they were simply not connected. The tests below pin
// the three properties that would let that happen again quietly.
//
// Run: node scripts/test-metro-charts.mjs

process.env.BLS_SKIP_MAIN = '1';
const { buildMetroCharts, METRO_TAGS, MA_METRO_SERIES, MA_METRO_UR_SERIES } =
  await import('./fetch-bls-data.js');

let failed = 0;
function check(label, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  const ok = a === e;
  if (!ok) failed++;
  console.log(`${ok ? '✅' : '❌'} ${label}` + (ok ? '' : `\n     expected ${e}\n     got      ${a}`));
}

// BLS periods are 'M07'; monthsOf() turns them into 0-based mon.
const per = (year, mon1, value) =>
  ({ year: String(year), period: `M${String(mon1).padStart(2, '0')}`, value: String(value) });

// Levels chosen so the ranking is unambiguous and the arithmetic checkable.
// Every metro reaches Jul 2026 EXCEPT Pittsfield, which stops at Jun -- so the
// charts must settle on June, the newest month all seven share.
const LEVELS = {
  'Barnstable':                  { 202506: 100, 202605: 100, 202606: 104, 202607: 110 },
  'Worcester':                   { 202506: 200, 202605: 200, 202606: 206, 202607: 210 },
  'Springfield':                 { 202506: 100, 202605: 100, 202606: 102, 202607: 103 },
  'Boston Metro Div':            { 202506: 1000, 202605: 1000, 202606: 1010, 202607: 1020 },
  'Pittsfield':                  { 202506: 100, 202605: 100, 202606:  99 },
  'Cambridge-Newton-Framingham': { 202506: 1000, 202605: 1000, 202606: 1005, 202607: 1010 },
  'Amherst-Northampton':         { 202506: 100, 202605: 100, 202606: 101, 202607: 102 },
};

// Unemployment rates for the same seven, a year apart: 3 up, 3 down, 1 flat.
const URS = {
  'Barnstable':                  { 202506: 3.9, 202606: 4.2 },   // up
  'Springfield':                 { 202506: 5.9, 202606: 6.0 },   // up
  'Pittsfield':                  { 202506: 4.1, 202606: 4.5 },   // up
  'Worcester':                   { 202506: 4.9, 202606: 4.8 },   // down
  'Cambridge-Newton-Framingham': { 202506: 4.6, 202606: 4.4 },   // down
  'Amherst-Northampton':         { 202506: 4.3, 202606: 4.2 },   // down
  'Boston Metro Div':            { 202506: 4.6, 202606: 4.6 },   // flat
};

function makeFind(levels, urs = URS) {
  const byId = {};
  const put = (id, lv) => {
    byId[id] = lv
      ? { seriesID: id, data: Object.entries(lv).map(([k, v]) =>
            per(Math.floor(k / 100), k % 100, v)) }
      : { seriesID: id, data: [] };
  };
  for (const [name, id] of Object.entries(MA_METRO_SERIES)) put(id, levels[name]);
  for (const [name, id] of Object.entries(MA_METRO_UR_SERIES)) put(id, urs[name]);
  return (id) => byId[id];
}

const template =
  METRO_TAGS.map(t => `var x=[/*@${t}*/SEED/*@*/];`).join('\n') +
  '\n<span data-field="metro-mom-head">OLD</span>' +
  '\n<span data-field="metro-yoy-head">OLD</span>' +
  '\n<span data-field="metro-ur-rose">X</span><span data-field="metro-ur-fell">X</span>' +
  '<span data-field="metro-ur-same">X</span><span data-field="metro-ur-n">X</span>' +
  '<span data-field="metro-ur-window">OLD</span>';

const out = buildMetroCharts(template, makeFind(LEVELS));
const grab = (tag) => {
  const m = out.match(new RegExp(`/\\*@${tag}\\*/([\\s\\S]*?)/\\*@\\*/`));
  return m ? m[1].split(',') : null;
};
const field = (f) => (out.match(new RegExp(`data-field="${f}">([^<]*)<`)) || [])[1];

check('no marker left holding its seed', METRO_TAGS.filter(t => grab(t)?.[0] === 'SEED'), []);

// 1. Settles on June -- the newest month ALL seven share, not July.
check('heading uses the shared month, not the newest', field('metro-mom-head'), 'May 2026 → Jun 2026');
check('yoy heading likewise',                          field('metro-yoy-head'), 'Jun 2025 → Jun 2026');

// 2. Bars are sorted strongest-first, labels reordered with them.
//    Jun vs May: Barnstable +4, Worcester +3, Boston +1, Amherst +1,
//    Springfield +2, Cambridge +0.5, Pittsfield -1.
check('MoM sorted strongest first', grab('metro-mom-lab').slice(0, 3),
      ["'Barnstable'", "'Worcester'", "'Springfield'"]);
check('MoM values match their labels', grab('metro-mom-data').slice(0, 3), ['4', '3', '2']);
check('MoM puts the decline last', grab('metro-mom-lab').at(-1), "'Pittsfield'");
check('and it is negative',        grab('metro-mom-data').at(-1), '-1');

// 3. Labels and data stay the same length, or the bars carry the wrong names.
check('lab and data lengths agree (mom)', grab('metro-mom-lab').length, grab('metro-mom-data').length);
check('lab and data lengths agree (yoy)', grab('metro-yoy-lab').length, grab('metro-yoy-data').length);
check('all seven metros present',        grab('metro-yoy-lab').length, 7);

// 3b. The unemployment sentence is counted, not asserted, over the same seven.
check('unemployment rose count', field('metro-ur-rose'), '3');
check('unemployment fell count', field('metro-ur-fell'), '3');
check('unemployment unchanged count', field('metro-ur-same'), '1');
check('counted over all seven', field('metro-ur-n'), '7');
check('counts sum to the total',
      Number(field('metro-ur-rose')) + Number(field('metro-ur-fell')) + Number(field('metro-ur-same')),
      Number(field('metro-ur-n')));
check('unemployment window is year-over-year', field('metro-ur-window'), 'Jun 2025 → Jun 2026');

// 3c. A division queried under the wrong prefix returns nothing; the counts must
//     then not be published at all rather than silently counting five of seven.
const partial = { ...URS }; delete partial['Boston Metro Div'];
const po = buildMetroCharts(template, makeFind(LEVELS, partial));
check('a missing UR series leaves the counts untouched',
      (po.match(/data-field="metro-ur-n">([^<]*)</) || [])[1], 'X');

// 4. A missing marker is fatal, not a warning -- inject() alone would log and
//    carry on, republishing the frozen month.
let threw = null;
try {
  buildMetroCharts(template.replace('/*@metro-yoy-data*/', '/*@typo*/'), makeFind(LEVELS));
} catch (e) { threw = e.message.includes('metro-yoy-data'); }
check('a missing marker throws, naming the tag', threw, true);

// 5. A missing series is a no-op, not a half-written chart.
const gone = { ...LEVELS }; delete gone['Worcester'];
check('a missing metro leaves the html untouched', buildMetroCharts(template, makeFind(gone)), template);

console.log(failed ? `\n${failed} check(s) failed` : '\nAll checks passed');
process.exit(failed ? 1 : 0);
