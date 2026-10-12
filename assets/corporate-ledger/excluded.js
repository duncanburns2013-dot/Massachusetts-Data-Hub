/* Amounts not counted tab: the register of headline amounts left out under the cash-only rule
   (data/ledger.json -> excluded_amounts, copied from data/manual/excluded-amounts.csv), sortable, with a totals row,
   and the counts of every other skipped case by reason. Text goes in through esc(); only http(s) URLs become links.
   URL parameters: ?tab=excluded  &xq=<company id or text> */
(function () {
  'use strict';

  var usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  var usd2 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var sig3 = new Intl.NumberFormat('en-US', { minimumSignificantDigits: 3, maximumSignificantDigits: 3 });
  var int0 = new Intl.NumberFormat('en-US');
  function exact(n) { return Math.round(n) === n ? usd0.format(n) : usd2.format(n); }
  function short(n) {
    var a = Math.abs(n);
    if (a >= 1e9) return '$' + sig3.format(a / 1e9) + 'B';
    if (a >= 1e6) return '$' + sig3.format(a / 1e6) + 'M';
    return usd0.format(n);
  }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : null; }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return 'link'; } }
  function has(n) { return n !== null && n !== undefined; }

  var COLS = [
    ['company', 'Company', false], ['case', 'Case', false], ['date', 'Date', false], ['headline', 'Headline', true],
    ['counted', 'Counted', true], ['not', 'Not counted', true], ['category', 'Category', false],
    ['reason', 'Reason', false], ['source', 'Source', false]
  ];
  var state = { sort: 'not', dir: -1, q: '' };
  var ROWS = [], NAMES = {}, TOTALS = null, OTHER = [], SHARED = null;
  // Rows left out because another row counts the same dollars are shown, but not summed with the cash-only rule's figures.
  var DUP = { duplicate_counted_once: 1, possible_duplicate: 1 };

  function kind(pid) {
    if (pid.indexOf('skipped:') === 0) return 'skipped case, not entered';
    if (pid.indexOf('shared:') === 0) return 'payment shared by several defendants, split not stated';
    return 'entered penalty row';
  }
  function key(r, k) {
    switch (k) {
      case 'company': return (NAMES[r.company_id] || r.defendant || '').toLowerCase();
      case 'case': return (r.defendant || '').toLowerCase();
      case 'date': return r.date || '';
      case 'headline': return has(r.headline_amount) ? r.headline_amount : -1;
      case 'counted': return has(r.counted_amount) ? r.counted_amount : -1;
      case 'not': return has(r.not_counted_amount) ? r.not_counted_amount : -1;
      case 'category': return r.category_label || '';
      case 'reason': return r.reason || '';
      default: return r.source_url || '';
    }
  }

  function headers() {
    var tr = document.getElementById('xa-cols');
    tr.innerHTML = '';
    COLS.forEach(function (c) {
      var th = document.createElement('th');
      th.scope = 'col';
      if (c[2]) th.className = 'n';
      if (c[0] === 'reason' || c[0] === 'source') { th.textContent = c[1]; tr.appendChild(th); return; }
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'sort';
      b.textContent = c[1];
      b.dataset.key = c[0];
      b.addEventListener('click', function () {
        if (state.sort === c[0]) state.dir = -state.dir;
        else { state.sort = c[0]; state.dir = c[2] ? -1 : 1; }
        render();
      });
      th.appendChild(b);
      tr.appendChild(th);
    });
  }

  function td(label, cls, html) { return '<td class="' + cls + '" data-label="' + esc(label) + '">' + html + '</td>'; }
  function amt(n, missing) { return has(n) ? '<span title="' + esc(exact(n)) + '">' + esc(short(n)) + '</span>' : '<span class="muted">' + esc(missing) + '</span>'; }

  function rowHtml(r) {
    var u = safeUrl(r.source_url);
    var co = r.company_id ? (NAMES[r.company_id] || r.company_id) : (r.penalty_id.indexOf('shared:') === 0 ? 'in no company total' : 'not a ledger company');
    var coHtml = r.company_id && NAMES[r.company_id] ?
      '<a href="?lens=all&amp;expand=' + encodeURIComponent(r.company_id) + '">' + esc(co) + '</a>' : '<span class="muted">' + esc(co) + '</span>';
    return '<tr id="' + esc(r.register_id) + '">' +
      td('Company', 'co', coHtml) +
      td('Case', 'case', esc(r.defendant) + '<span class="sub" style="white-space:normal">' + esc(r.agency) + '; ' + esc(kind(r.penalty_id)) + '; ' + esc(r.register_id) + '</span>') +
      td('Date', 'n', esc(r.date)) +
      td('Headline', 'n', amt(r.headline_amount, 'not entered')) +
      td('Counted', 'n', amt(r.counted_amount, 'none')) +
      td('Not counted', 'n', amt(r.not_counted_amount, 'no dollar value')) +
      td('Category', 'cat', esc(r.category_label)) +
      td('Reason', 'why', esc(r.reason)) +
      td('Source', 'src', u ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(host(u)) + '</a>' : '<span class="muted">' + esc(r.source_url || 'none') + '</span>') +
      '</tr>';
  }

  function visible() {
    var q = state.q.trim().toLowerCase();
    return ROWS.filter(function (r) {
      return !q || r.company_id === q || [r.company_id, NAMES[r.company_id], r.defendant, r.register_id, r.agency]
        .some(function (s) { return s && String(s).toLowerCase().indexOf(q) >= 0; });
    }).sort(function (a, b) {
      var x = key(a, state.sort), y = key(b, state.sort);
      if (x < y) return -state.dir;
      if (x > y) return state.dir;
      return a.register_id < b.register_id ? -1 : 1;
    });
  }

  function totalsOf(list) {
    var t = { h: 0, c: 0, n: 0, nh: 0, nd: 0, d: 0 };
    list.forEach(function (r) {
      if (DUP[r.category]) { t.nd += 1; t.d += r.not_counted_amount || 0; return; }
      if (has(r.headline_amount)) { t.h += r.headline_amount; t.c += r.counted_amount || 0; } else t.nh += 1;
      if (has(r.not_counted_amount)) t.n += r.not_counted_amount;
    });
    return t;
  }

  function render() {
    var list = visible();
    document.getElementById('xa-rows').innerHTML = list.length ? list.map(rowHtml).join('') :
      '<tr><td colspan="9" class="empty">No row matches "' + esc(state.q) + '". Clear the search to see all ' + int0.format(ROWS.length) + '.</td></tr>';
    var t = totalsOf(list);
    document.getElementById('xa-foot').innerHTML = '<tr>' +
      '<td class="lab" colspan="3">Totals, ' + int0.format(list.length) + (list.length === 1 ? ' row' : ' rows') +
        '<span class="xa-tnote">Headline and counted sum the ' + int0.format(list.length - t.nh - t.nd) + ' rows that have a headline; not counted sums every row with a dollar value. ' +
        (t.nd ? int0.format(t.nd) + (t.nd === 1 ? ' row' : ' rows') + ' left out as the same payment counted on another row (' + esc(exact(t.d)) + ') are not in these sums.' : '') + '</span></td>' +
      td('Headline', 'n', esc(exact(t.h))) + td('Counted', 'n', esc(exact(t.c))) + td('Not counted', 'n', esc(exact(t.n))) +
      td('', '', '') + td('', '', '') + td('', '', '') + '</tr>';
    document.querySelectorAll('#xa-cols .sort').forEach(function (b) {
      if (b.dataset.key === state.sort) b.setAttribute('aria-sort', state.dir < 0 ? 'descending' : 'ascending');
      else b.removeAttribute('aria-sort');
    });
  }

  function dupSummary() {
    var D = TOTALS.duplicates, out = '';
    if (D && D.n) {
      out += ' Rows left out because another row counts the same dollars: ' + int0.format(D.n) + ' rows, <span class="mono">' + esc(short(D.left_out)) + '</span> (not in the sums above)';
      if (D.n_possible) out += '; ' + int0.format(D.n_possible) + ' of them ' + (D.n_possible === 1 ? 'is a possible duplicate' : 'are possible duplicates') + ', <span class="mono">' + esc(short(D.possible_left_out)) + '</span>, counted once until verified';
      out += '.';
    }
    var ns = SHARED && SHARED.by_basis && SHARED.by_basis.not_stated;
    if (ns && ns.n) out += ' Shared totals counted for no company because the source gives no split: ' + int0.format(ns.n) + ' rows, <span class="mono">' + esc(short(ns.shared_total_not_counted)) + '</span> (in gross).';
    return out;
  }

  function summary() {
    var T = TOTALS;
    var cats = Object.keys(T.by_category).map(function (k) { return T.by_category[k]; })
      .sort(function (a, b) { return b.n - a.n; })
      .map(function (c) { return esc(c.label.toLowerCase()) + ' ' + int0.format(c.n); }).join('; ');
    document.getElementById('xa-sum').innerHTML = int0.format(T.n) + ' rows. Where a headline is entered (' + int0.format(T.n - T.n_headline_not_stated) +
      ' rows), releases headlined <span class="mono">' + esc(short(T.headline_total)) + '</span> and the ledger counts <span class="mono">' +
      esc(short(T.counted_total)) + '</span> of it. Not counted in all: <span class="mono">' + esc(short(T.not_counted_total)) +
      '</span>. By category: ' + cats + '. Each row gives the reason and the source; a row with no headline says why.' + dupSummary();
  }

  function other() {
    var n = OTHER.reduce(function (s, g) { return s + g.n; }, 0);
    var html = '<h3 class="section-title" style="font-size:1.1rem">Other exclusions</h3>' +
      '<p>Every case the release-sourcing pass skipped, by reason (' + int0.format(n) + ' cases). These are not counted for reasons other than the cash-only rule; the cases under the rule are the rows above.</p><ul>';
    OTHER.forEach(function (g) {
      html += '<li><span class="mono">' + int0.format(g.n) + '</span> ' + (g.n === 1 ? 'case' : 'cases') + ' skipped: ' + esc(/^[A-Z][a-z]/.test(g.label) ? g.label.charAt(0).toLowerCase() + g.label.slice(1) : g.label) + '</li>';
    });
    html += '</ul><p class="source">Source: skip logs of the release-sourcing pass (repo folder review/batches, files ending -skipped.csv), grouped by the reason written for each case.</p>';
    document.getElementById('xa-other').innerHTML = html;
  }

  // Settlements the coverage check found in the Justice Department's press-release database that are not in the ledger.
  function gapMoney(m) { return m >= 1000 ? '$' + (m / 1000) + ' billion' : '$' + m + ' million'; }
  function gap() {
    var box = document.getElementById('xa-gap');
    if (!box) return;
    fetch('data/corporate-ledger/coverage-gap.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (rows) {
      var body = rows.map(function (r) {
        var u = safeUrl(r.url);
        return '<tr><td data-label="Date" class="mono">' + esc(r.date) + '</td><td data-label="Amount in the title" class="mono">' +
          esc(gapMoney(r.amount_millions)) + '</td><td data-label="Release">' + (u ? '<a href="' + esc(u) + '" rel="noopener">' + esc(r.title) + '</a>' : esc(r.title)) + '</td></tr>';
      }).join('');
      box.innerHTML = '<h3 class="section-title" style="font-size:1.1rem">Settlements found but not yet in the ledger</h3>' +
        '<p>While checking coverage against the Justice Department’s own press-release database, we found <span class="mono">' + int0.format(rows.length) +
        '</span> settlements of $1 million or more announced by the U.S. Attorney’s Office for Massachusetts with companies that are not yet in this ledger. ' +
        'They are listed so nothing is hidden. They are not in any total on this site. The list is a floor: it holds only releases that carry a dollar amount in the title; ' +
        'settlements announced by other Justice Department offices, and releases with no amount in the title, were not found this way.</p>' +
        '<div class="table-card"><table class="xa"><thead><tr><th>Date</th><th>Amount in the title</th><th>Release</th></tr></thead><tbody>' + body + '</tbody></table></div>' +
        '<p class="source">Source: the justice.gov press-release interface (api/v1/press_releases), every release with Million or Billion in its title from July 2009, read 2026-10-11 and filtered to the U.S. Attorney’s Office for Massachusetts; the list is the repo file review/coverage-gap-usao-ma.tsv.</p>';
    }).catch(function () { box.textContent = 'The coverage list (data/coverage-gap.json) could not be loaded. Reload the page to try again.'; });
  }

  // How every penalty row was checked against its own source page (pipeline/authenticity.py).
  var VERDICT = {
    verified: 'the source page names the defendant and states the amount',
    verified_manual: 'read by a person in a browser (the page blocks scripted readers); the page states the amount',
    registry_verified_by_doj: 'registry row; the Justice Department’s own release states the amount',
    registry_corrected_from_doj: 'registry row whose amount the Justice Department’s release corrects (listed in the corrections file)',
    registry_only: 'registry row not yet matched to an agency document',
    fetch_failed: 'source page could not be read by a script (bot check, rate limit or scanned PDF)',
    amount_not_found: 'source page read, amount not found on it',
    defendant_not_found: 'source page read, defendant not found on it',
    year_not_found: 'source page read, year not found on it'
  };
  function auth() {
    var box = document.getElementById('xa-auth');
    if (!box) return;
    fetch('data/corporate-ledger/authenticity.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      var order = Object.keys(VERDICT);
      var total = order.reduce(function (s, k) { return s + (d.counts[k] || 0); }, 0);
      var lis = order.filter(function (k) { return d.counts[k]; }).map(function (k) {
        return '<li><span class="mono">' + int0.format(d.counts[k]) + '</span> ' + esc(VERDICT[k]) + '</li>';
      }).join('');
      var rows = d.unverified.map(function (r) {
        var u = safeUrl(r.url);
        return '<tr><td data-label="Row">' + esc(r.defendant) + '</td><td data-label="Date" class="mono">' + esc(r.date) + '</td><td data-label="Amount" class="mono">' +
          esc(short(r.amount)) + '</td><td data-label="Why">' + esc(VERDICT[r.verdict] || r.verdict) + '</td><td data-label="Source">' +
          (u ? '<a href="' + esc(u) + '" rel="noopener">' + esc(host(u)) + '</a>' : '<span class="muted">registry file</span>') + '</td></tr>';
      }).join('');
      box.innerHTML = '<h3 class="section-title" style="font-size:1.1rem">How every penalty row was checked against its source</h3>' +
        '<p>Each of the <span class="mono">' + int0.format(total) + '</span> penalty rows was tested against the page it cites: does it name the defendant, and does it state the amount, or amounts that add up to it? Checked ' + esc(d.checked) + '.</p>' +
        '<ul>' + lis + '</ul>' +
        '<p>Rows that could not be confirmed this way stay in the ledger and are listed here, largest first, so a reader can check them by hand.</p>' +
        '<div class="table-card"><table class="xa"><thead><tr><th>Row</th><th>Date</th><th>Amount</th><th>Why not confirmed</th><th>Source</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
        '<p class="source">Source: review/authenticity-results.csv, written by pipeline/authenticity.py from pages read in headless Chrome and, for pages that block scripts, in a browser by a person (review/authenticity-manual.csv); registry rows are checked against the Justice Department’s releases (review/authenticity-registry.csv).</p>';
    }).catch(function () { box.textContent = 'The source-check summary (data/authenticity.json) could not be loaded. Reload the page to try again.'; });
  }

  function init() {
    var params = new URLSearchParams(location.search);
    if (params.get('xq')) state.q = params.get('xq');
    headers();
    var input = document.getElementById('xa-q');
    input.value = state.q;
    input.addEventListener('input', function (e) { state.q = e.target.value; render(); });
    window.XA_FILTER = function (q) { state.q = q || ''; input.value = state.q; if (ROWS.length) render(); };
    fetch('data/corporate-ledger/ledger.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      var x = d.excluded_amounts || { rows: [], totals: null, other_exclusions: [] };
      (d.companies || []).forEach(function (c) { NAMES[c.company_id] = c.name; });
      ROWS = x.rows; TOTALS = x.totals; OTHER = x.other_exclusions || []; SHARED = x.shared_totals || null;
      if (TOTALS) summary();
      render();
      other();
      gap();
      auth();
      document.documentElement.dataset.excludedReady = '1';
    }).catch(function () {
      document.getElementById('xa-sum').textContent = 'The register (data/ledger.json) could not be loaded. Reload the page to try again.';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
