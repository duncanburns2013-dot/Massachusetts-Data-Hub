// Guards the "Released <date>" provenance stamp on the employment dashboard.
//
// The stamp used to come from new Date(), so every run on a non-release day
// published a date that had nothing to do with the data beside it — the Aug 5
// and Aug 6 2026 runs both claimed "June 2026 National Employment — Released
// August 5 / 6, 2026" when June went out on July 2, 2026.
//
// Run: BLS_SKIP_MAIN=1 node scripts/test-release-schedule.mjs
//   (or: npm run --prefix scripts test-release-schedule)

process.env.BLS_SKIP_MAIN = '1';
const { loadReleaseSchedule, releaseDateFor } = await import('./fetch-bls-data.js');

const FULLMON = ['January','February','March','April','May','June','July','August',
                 'September','October','November','December'];

const sched = await loadReleaseSchedule();
let failed = 0;

function check(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) failed++;
  console.log(`${ok ? '✅' : '❌'} ${label}\n     expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

// monIdx is 0-based, matching monthsOf()'s `mon`.
const rel = (y, monIdx) => releaseDateFor(sched, y, monIdx, FULLMON);

console.log('\n── BLS release-date lookup ──────────────────────────────────\n');

// The regression itself: June 2026 data was released July 2, NOT the Aug 5/6
// run dates the old code stamped on it.
check('June 2026 reference month → its real release day',      rel(2026, 5),  'July 2, 2026');
check('July 2026 reference month → its real release day',      rel(2026, 6),  'August 7, 2026');

// Not a first-Friday rule: April went out on the second Friday, and the
// December-2025 reference month slipped to January 9.
check('April 2026 (second Friday, not first)',                 rel(2026, 3),  'May 8, 2026');
check('December 2025 (crosses the year boundary)',             rel(2025, 11), 'January 9, 2026');

// Formatted from the date parts, not via Date parsing — "2026-08-07" as UTC
// midnight would render as August 6 on any runner west of Greenwich.
check('no UTC-midnight off-by-one on a day-07 date',           rel(2026, 6),  'August 7, 2026');

// Unknown month returns null so the caller can render an em dash. Returning
// today's date here is exactly the bug being guarded against.
check('month absent from the schedule → null, never today',    rel(2031, 0),  null);

console.log(`\n${failed === 0 ? '✨ all checks passed' : `❌ ${failed} check(s) failed`}\n`);
process.exit(failed === 0 ? 0 : 1);
