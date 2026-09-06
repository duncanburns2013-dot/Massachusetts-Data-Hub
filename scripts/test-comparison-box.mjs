// Guards the Overview tab's "Massachusetts vs. the Nation" box.
//
// The property under test is the one that would go wrong silently: the national
// series publish about two weeks before the state ones, so the shared axis ends
// on a month the US has and MA does not. If that trailing MA null ever stopped
// appearing — because someone trimmed the axis to MA's end, or forward-filled it
// — the page would start reading a US figure from one month against an MA figure
// from another and every gap in the box would be wrong, with nothing on screen
// to show it.
//
// Fixtures are the real values for those months (BLS, seasonally adjusted):
// MA runs through July 2026, the US through August 2026, exactly as published.
//
// Run: node scripts/test-comparison-box.mjs

process.env.BLS_SKIP_MAIN = '1';
const { buildComparisonBox, CMP_TAGS } = await import('./fetch-bls-data.js');

let failed = 0;
function check(label, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  const ok = a === e;
  if (!ok) failed++;
  console.log(`${ok ? '✅' : '❌'} ${label}` + (ok ? '' : `\n     expected ${e}\n     got      ${a}`));
}

// mon is 0-based, matching monthsOf(). 2026: May=4, Jun=5, Jul=6, Aug=7.
const pt = (mon, value) => ({ year: 2026, mon, value });

const series = {
  maUR: [pt(4, 4.5), pt(5, 4.4), pt(6, 4.4)],
  usUR: [pt(4, 4.3), pt(5, 4.2), pt(6, 4.1), pt(7, 4.1)],
  maNF: [pt(4, 3711.1), pt(5, 3717.1), pt(6, 3712.5)],
  usNF: [pt(4, 158_800.0), pt(5, 158_892.0), pt(6, 158_913.0), pt(7, 159_075.0)],
  // Published in PERSONS — the box divides these to thousands.
  maLF: [pt(4, 3_879_513), pt(5, 3_873_490), pt(6, 3_870_833)],
  usLF: [pt(4, 169_500.0), pt(5, 169_600.0), pt(6, 169_700.0), pt(7, 169_777.0)],
};

const template = CMP_TAGS.map(t => `var x=[/*@${t}*/SEED/*@*/];`).join('\n');
const out = buildComparisonBox(template, series);

const grab = (tag) => {
  const m = out.match(new RegExp(`/\\*@${tag}\\*/([\\s\\S]*?)/\\*@\\*/`));
  return m ? m[1].split(',') : null;
};

// 1. Nothing was left holding its seed.
check('every marker was written', CMP_TAGS.filter(t => grab(t)?.[0] === 'SEED'), []);

// 2. The axis spans the union of both geographies, so it ends on August.
check('axis length is the union (4 months)', grab('cmp-lab').length, 4);
check('axis ends at August', grab('cmp-lab').at(-1), "'Aug 26'");

// 3. THE POINT: the trailing month has a US value and an MA null, in every pair.
check('MA rate is null in the trailing month',   grab('cmp-ma-ur').at(-1), 'null');
check('US rate is present there',                grab('cmp-us-ur').at(-1), '4.1');
check('MA payrolls null in trailing month',      grab('cmp-ma-nf').at(-1), 'null');
check('US payrolls present there',               grab('cmp-us-nf').at(-1), '159075.0');
check('MA labor force null in trailing month',   grab('cmp-ma-lf').at(-1), 'null');
check('US labor force present there',            grab('cmp-us-lf').at(-1), '169777.0');

// 4. MA's last real value sits one slot back, where the page anchors.
check('MA rate at the anchor index', grab('cmp-ma-ur').at(-2), '4.4');
check('US rate at the same index',   grab('cmp-us-ur').at(-2), '4.1');

// 5. Units: MA labour force converted persons -> thousands, everything else left.
check('MA labor force scaled to thousands', grab('cmp-ma-lf').at(-2), '3870.833');
check('US labor force left in thousands',   grab('cmp-us-lf').at(-2), '169700.0');

// 6. A missing marker is fatal, not a warning. This is the whole reason the
//    check exists: inject() would log and carry on, publishing a frozen month.
let threw = null;
try {
  buildComparisonBox(template.replace('/*@cmp-ma-lf*/', '/*@typo*/'), series);
} catch (e) {
  threw = e.message.includes('cmp-ma-lf');
}
check('a missing marker throws, naming the tag', threw, true);

// 7. Incomplete input is a no-op, not a crash or a half-written box.
check('missing a series leaves the html untouched',
  buildComparisonBox(template, { ...series, usLF: [] }), template);

console.log(failed ? `\n${failed} check(s) failed` : '\nAll checks passed');
process.exit(failed ? 1 : 0);
