/* "How it connects" tab (?tab=connects). Reads the audited "intertwined" block of data/ledger.json (through ledger.js, which
   owns the file and the lens toggle) and shows, for the current lens: how far the penalized companies reach into the other
   records, the four ledgers side by side, what the state paid in the same and in later fiscal years, the criminal cases,
   who received the employee donations, officials' disclosed ties and the regulator findings, then the owner's view.
   Every number is read from that block when the page loads; none is written in this file or in corporate-ledger.html.
   Officials' disclosed ties are counted without mortgage lenders (an ordinary lender relationship); the counts that include
   them are separate, labelled figures.
   Caveats are the statistics' own strings, shown with them. Text goes in through textContent; only http(s) URLs become links.
   Colours are the page's stream variables (--s-*), read by the stylesheet, none is written here. */
(function () {
  'use strict';

  var API = window.LEDGER_API;
  if (!API) return;

  var LEDGER = null, IW = null;
  var ui = { view: 'chart', crim: 'all' };   // view choices that survive a lens change

  var REC = [
    { key: 'payments', word: 'State payments', v: '--s-contract' },
    { key: 'donations', word: 'Donations', v: '--s-donation' },
    { key: 'lobbying', word: 'Lobbying', v: '--s-lobbying' },
    { key: 'holdings', word: "Officials' ties", v: '--s-holding' }
  ];
  var LENS_NAME = { ma_conduct: 'Massachusetts case', ma_hq: 'Massachusetts headquarters', all: 'all lenses' };
  var LENS_DEF = {
    ma_conduct: 'Penalties that cover conduct in Massachusetts.',
    ma_hq: 'Massachusetts-headquartered companies, penalized anywhere, from the date each headquarters moved here.',
    all: 'Every penalty row, under either lens.'
  };
  var SRC = {
    'data/ledger.json companies': 'the ledger table (ledger.json)',
    'data/ledger.json lenses': 'the ledger table (ledger.json)',
    'data/penalties.csv': 'agency penalty releases and the Corporate Prosecution Registry',
    'data/contracts.csv': 'CTHRU, MBTA, Massport and MSBA payment records',
    'data/donations-matched.csv': 'OCPF and FEC contribution files (confirmed employer matches)',
    'data/lobbying.csv': 'Secretary of the Commonwealth lobbying disclosures',
    'data/holdings.csv': "officials' Statements of Financial Interest",
    'data/person-links.csv': 'case documents and contribution files (strict person links)',
    'data/manual/overlaps.csv': 'the register of penalty rows that restate another row',
    'data/manual/regulator-findings.csv': 'the register of regulator findings',
    'sources/case-files': 'release texts kept in the repository'
  };
  var AGREEMENT = { plea: 'plea', DPA: 'deferred prosecution agreement', NPA: 'non-prosecution agreement', trial: 'trial' };
  var KIND_NAME = { employer: 'Employer, own or spouse', investment: 'Investment', officer_director: 'Officer or director', ownership: 'Ownership' };

  // ---------- formatting and small DOM helpers ----------
  var usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  var sig3 = new Intl.NumberFormat('en-US', { minimumSignificantDigits: 3, maximumSignificantDigits: 3 });
  var int0 = new Intl.NumberFormat('en-US');
  function money(n) {
    var a = Math.abs(n), s = n < 0 ? '-' : '';
    if (a >= 1e9) return s + '$' + sig3.format(a / 1e9) + 'B';
    if (a >= 1e6) return s + '$' + sig3.format(a / 1e6) + 'M';
    return usd0.format(n);
  }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function add(parent) {
    for (var i = 1; i < arguments.length; i++) {
      var k = arguments[i];
      if (k === null || k === undefined || k === false) continue;
      parent.appendChild(typeof k === 'string' || typeof k === 'number' ? document.createTextNode(String(k)) : k);
    }
    return parent;
  }
  function num(n) { return el('span', 'num mono', int0.format(n)); }
  function mono(text) { return el('span', 'mono', text); }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : null; }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return 'link'; } }
  function link(url, text) {
    var u = safeUrl(url);
    if (!u) return document.createTextNode(text || '');
    var a = el('a', null, text || host(u));
    a.href = u; a.target = '_blank'; a.rel = 'noopener';
    return a;
  }
  function plural(n, one, many) { return n === 1 ? one : many; }
  function pctW(x, max) { return (max > 0 ? Math.max(0, Math.min(100, x / max * 100)) : 0).toFixed(2) + '%'; }
  function fyLabel(y) { return y ? 'FY' + y : ''; }
  function nameOf(id) { var c = API.byId(id); return c ? c.name : id; }
  function pct(x, d) { return (x * 100).toFixed(d || 0) + '%'; }
  function countWord(n) { return ({ 1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five' })[n] || int0.format(n); }
  function joinNames(a) { return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }

  function stat(id, lens) {
    var L = IW.lenses[lens || API.lens()];
    for (var i = 0; i < L.statistics.length; i++) if (L.statistics[i].id === id) return L.statistics[i];
    return null;
  }
  function caveat(st, prefix) {
    for (var i = 0; i < st.caveats.length; i++) if (st.caveats[i].indexOf(prefix) === 0) return st.caveats[i];
    return '';
  }

  // ---------- pieces shared by the sections ----------
  function section(id, title, st) {
    var card = el('section', 'card cx-sec');
    card.id = 'cx-sec-' + id;
    card.setAttribute('aria-labelledby', 'cx-h-' + id);
    var h = el('h3', 'section-title', title);
    h.id = 'cx-h-' + id;
    add(card, h);
    if (st) add(card, el('p', 'lede', st.definition));
    return card;
  }
  function caveatBox(st, skip) {
    var box = el('div', 'cx-cav');
    add(box, el('h4', null, 'Caveats from the data'));
    var ul = el('ul');
    st.caveats.forEach(function (c) {
      if ((skip || []).indexOf(c) >= 0) return;
      add(ul, el('li', null, c));
    });
    return add(box, ul);
  }
  function sourceLine(st, extra) {
    var seen = {}, names = [];
    st.sources.forEach(function (f) { var n = SRC[f] || f; if (!seen[n]) { seen[n] = 1; names.push(n); } });
    return el('p', 'source', 'Source: audited statistic ' + st.id + ' in ledger.json (intertwined block, ' + lensPhrase(st.lens) +
      '), computed from ' + names.join('; ') + '.' + (extra ? ' ' + extra : ''));
  }
  function seg(label, options, current, onPick) {
    var wrap = el('div');
    var lab = el('span', 'ctl-label', label);
    lab.id = 'cx-seg-' + label.toLowerCase().replace(/[^a-z]+/g, '-');
    var g = el('div', 'seg');
    g.setAttribute('role', 'group');
    g.setAttribute('aria-labelledby', lab.id);
    options.forEach(function (o) {
      var b = el('button', null, o[1]);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(o[0] === current));
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(g.children, function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        onPick(o[0]);
      });
      add(g, b);
    });
    return add(wrap, lab, g);
  }
  function companyButton(id, label) {
    var b = el('button', 'xl-name', label || nameOf(id));
    b.type = 'button';
    b.setAttribute('data-open', id);
    b.title = 'Open this company in the Ledger';
    return b;
  }
  function dots(flags, cls) {
    var wrap = el('span', 'cx-dots' + (cls ? ' ' + cls : ''));
    wrap.setAttribute('aria-hidden', 'true');
    var first = -1, last = -1;
    flags.forEach(function (f, i) {
      var d = el('i', f.on ? 'on' : '');
      if (f.on) { d.style.setProperty('--c', 'var(' + f.v + ')'); if (first < 0) first = i; last = i; }
      add(wrap, d);
    });
    wrap.style.setProperty('--a', first < 0 ? 0 : first);
    wrap.style.setProperty('--b', last < 0 ? 0 : last);
    return wrap;
  }
  function comboTitle(k) {
    if (k === 'none') return 'No other record';
    var parts = k.split('+').map(function (p) { return REC.filter(function (r) { return r.key === p; })[0].word; });
    return parts.length === 1 ? parts[0] + ' only' : parts.join(' + ');
  }
  function comboSize(k) { return k === 'none' ? 0 : k.split('+').length; }
  function noun(n) { return plural(n, 'company', 'companies'); }
  function lensPhrase(l) { return l === 'all' ? 'all-lenses' : LENS_NAME[l] + ' lens'; }

  // ---------- head: headline sentence, lens note, the two rules ----------
  function renderHead() {
    var st = stat('reach'), v = st.values, lens = API.lens();
    var h = $('cx-headline');
    h.textContent = '';
    add(h, 'Of ', num(v.n_penalized), ' penalized companies and institutions, ', num(v.in_any_excluding_mortgage), ' also appear in at least one other record. Of those, ',
      num(v.in_payments_donations_lobbying), ' appear in state payments, donations and lobbying, and ', num(v.in_all_four_excluding_mortgage),
      " in all four: those three plus officials' disclosed ties, not counting mortgages.");
    $('cx-keyline').textContent = "The four records: state payments (CTHRU, MBTA, Massport and MSBA), donations by employees (OCPF for state officials, FEC for federal), " +
      "lobbying, and officials' disclosed ties. A company appears in a record when its total there is above zero.";
    var mn = $('cx-mortgage');
    if (mn) {
      mn.textContent = '';
      if (v.n_holdings_mortgage_only > 0) {
        add(mn, el('strong', null, 'Mortgages, shown apart: '), "officials' disclosed ties here leave out mortgages, an ordinary lender relationship. ",
          num(v.n_holdings_mortgage_only), ' ' + noun(v.n_holdings_mortgage_only) + ' have a mortgage as their only disclosed tie. Counting them, ',
          num(v.in_any), ' appear in at least one other record and ', num(v.in_holdings), " in officials' disclosed ties.");
      }
      mn.hidden = !(v.n_holdings_mortgage_only > 0);
    }
    $('cx-lens-note').textContent = LENS_DEF[lens] + ' Counted over ' + st.denominator.what + '.';
    Array.prototype.forEach.call(document.querySelectorAll('#cx-lens button'), function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-lens') === lens));
    });
    // the two rules, from the ledger file (the same text the Ledger tab shows)
    $('cx-rule-window').textContent = LEDGER.disclaimer;
    var rule = (LEDGER.rules || {}).penalty_amount_rule || '', box = $('cx-rule-amount'), key = 'Amounts not counted', i = rule.indexOf(key);
    box.textContent = '';
    if (i >= 0) {
      var a = el('a', null, key);
      a.href = '?tab=excluded';
      add(box, rule.slice(0, i), a, rule.slice(i + key.length));
    } else add(box, rule);
    $('cx-rule-dup').textContent = (LEDGER.rules || {}).duplicate_rule || '';
    $('cx-rule-shared').textContent = (LEDGER.rules || {}).shared_total_rule || '';
    $('cx-rules').hidden = false;
  }

  function renderTeaser() {
    var t = $('cx-teaser');
    if (!t) return;
    var st = stat('reach'), v = st.values;
    t.textContent = '';
    var a = el('a', null, 'How it connects');
    a.href = '?tab=connects';
    add(t, el('b', null, int0.format(v.in_any_excluding_mortgage)), ' of ', el('b', null, int0.format(v.n_penalized)), ' penalized companies and institutions (', lensPhrase(API.lens()),
      ') also appear in at least one other record. ', a);
    t.hidden = false;
  }

  // ---------- 2. the overlap view ----------
  function secOverlap() {
    var st = stat('reach'), v = st.values, n = v.n_penalized;
    var card = section('reach', 'Which records they appear in', st);
    var combos = v.combos_excluding_mortgage;
    var keys = Object.keys(combos).filter(function (k) { return combos[k] > 0; });
    keys.sort(function (a, b) { return combos[b] - combos[a] || comboSize(b) - comboSize(a) || (a < b ? -1 : 1); });
    var max = keys.length ? combos[keys[0]] : 0;

    var tools = el('div', 'cx-tools');
    var chartBox = el('div'), listBox = el('div');
    function showView(k) { ui.view = k; chartBox.hidden = k !== 'chart'; listBox.hidden = k !== 'list'; }
    add(tools, seg('View', [['chart', 'Chart'], ['list', 'List']], ui.view, showView));
    add(card, tools);

    // with only a few combinations the chart is short: the two aside blocks then sit beside each other under it
    var grid = el('div', 'cx-grid ov' + (keys.length <= 5 ? ' few' : ''));
    var main = el('div'), aside = el('div', 'cx-aside'), asideA = el('div'), asideB = el('div');

    // chart: dots say which records, the bar says how many companies; every row is a button
    var legend = el('p', 'cx-legend');
    legend.setAttribute('aria-hidden', 'true');
    REC.forEach(function (r) {
      var s = el('span', 'lg-d');
      var d = el('span', 'cdot');
      d.style.setProperty('--c', 'var(' + r.v + ')');
      add(s, d, r.word);
      add(legend, s);
    });
    add(legend, el('span', null, 'A hollow dot means not in that record.'));
    add(chartBox, legend);
    var ol = el('ol', 'cx-up');
    ol.setAttribute('aria-label', 'Combinations of the four records, most companies first. Select one to open exactly those companies in the Ledger.');
    keys.forEach(function (k) {
      var count = combos[k], on = k === 'none' ? [] : k.split('+');
      var li = el('li'), b = el('button', 'cx-up-btn');
      b.type = 'button';
      b.setAttribute('data-combo', k);
      b.setAttribute('aria-label', comboTitle(k) + ': ' + int0.format(count) + ' ' + noun(count) + '. Show them in the Ledger.');
      var bar = el('span', 'cx-bar'), fill = el('span', 'cx-fill' + (k === 'none' ? ' none' : on.length === REC.length ? ' all' : ''));
      fill.style.width = pctW(count, max);
      add(bar, fill);
      add(b, dots(REC.map(function (r) { return { on: on.indexOf(r.key) >= 0, v: r.v }; })), el('span', 'cx-up-lab', comboTitle(k)), bar, el('span', 'cx-up-n mono', int0.format(count)));
      add(li, b);
      add(ol, li);
    });
    add(chartBox, ol);
    var none = Math.pow(2, REC.length) - keys.length;
    add(chartBox, el('p', 'cx-hint', 'Grey bar: no other record. Red bar: all four. ' + (none ? int0.format(none) + ' of the ' + int0.format(Math.pow(2, REC.length)) +
      ' possible combinations have no company in this lens and are not drawn. ' : '') + 'Select a row to open exactly those companies in the Ledger.'));

    // list view: the same rows as a table
    var tbl = el('table', 'cx-tab stack');
    var cap = el('caption', 'sr', 'The same combinations of records as the chart, with the number of companies in each');
    var thead = el('thead'), hr = el('tr');
    add(hr, el('th', null, 'Records the company appears in'), el('th', 'n', 'Companies'), el('th', null, 'Ledger'));
    add(thead, hr);
    var tb = el('tbody');
    keys.forEach(function (k) {
      var tr = el('tr'), c = combos[k];
      var td3 = el('td'), btn = el('button', 'more', 'Show in the Ledger');
      btn.type = 'button'; btn.style.marginTop = '0';
      btn.setAttribute('data-combo', k);
      btn.setAttribute('aria-label', 'Show the ' + int0.format(c) + ' ' + noun(c) + ' that appear in: ' + comboTitle(k) + ', in the Ledger');
      add(td3, btn);
      var tdn = el('td', 'n', int0.format(c)); tdn.setAttribute('data-label', 'Companies');
      add(tr, el('td', null, comboTitle(k)), tdn, td3);
      add(tb, tr);
    });
    add(tbl, cap, thead, tb);
    add(listBox, tbl);

    add(main, chartBox, listBox);
    showView(ui.view);

    // aside: each record on its own
    add(asideA, el('h4', 'cx-h4', 'Each record on its own'));
    add(asideA, el('p', 'cx-sub', 'Companies in the record, out of ' + int0.format(n) + '. The rows overlap, so they are not added.'));
    var ul = el('ul', 'cx-each');
    function eachRow(label, count, cssVar, fine, hatch) {
      var li = el('li'), r1 = el('span', 'r1'), r2 = el('span', 'r2');
      add(r1, el('span', null, label), el('span', 'mono', int0.format(count)));
      var f = el('span', 'cx-fill s' + (hatch ? ' hatch' : ''));
      f.style.setProperty('--c', 'var(' + cssVar + ')');
      f.style.width = pctW(count, n);
      add(r2, f);
      add(li, r1, r2);
      if (fine) add(li, el('span', 'fine', fine));
      add(ul, li);
    }
    eachRow('State payments', v.in_payments, '--s-contract', '');
    eachRow('Donations by employees', v.in_donations, '--s-donation', 'State (OCPF) ' + int0.format(v.in_donations_ocpf) + ' and federal (FEC) ' + int0.format(v.in_donations_fec) +
      ' companies. A company can be in both, and the two are never added.');
    eachRow('Lobbying', v.in_lobbying, '--s-lobbying', '');
    eachRow("Officials' disclosed ties, not counting mortgages", v.in_holdings_excluding_mortgage, '--s-holding', v.n_holdings_mortgage_only > 0 ?
      'Shown apart: ' + int0.format(v.n_holdings_mortgage_only) + ' more ' + noun(v.n_holdings_mortgage_only) + ' have a mortgage as their only disclosed tie, an ordinary lender relationship. Counting them, ' +
      int0.format(v.in_holdings) + ' appear there.' : '');
    add(asideA, ul);

    // companies and institutions: the kind split the caveats refer to
    var KIND_ROW = { company: 'Companies', 'institution/nonprofit': 'Institutions and nonprofits', 'case-file (below $1M)': 'Case-file company (penalties below $1M)' };
    var byKind = v.by_kind_excluding_mortgage;
    var kinds = Object.keys(byKind).sort(function (a, b) { return byKind[b].n - byKind[a].n || (a < b ? -1 : 1); });
    add(asideB, el('h4', 'cx-h4', 'Companies and institutions'));
    var kt = el('table', 'cx-tab'), khr = el('tr');
    add(khr, el('th', null, 'Kind'), el('th', 'n', 'Entries'), el('th', 'n', 'In no other record'), el('th', 'n', 'In all four'));
    add(kt, el('caption', 'sr', 'The entries split by kind, with how many appear in no other record and in all four'), add(el('thead'), khr));
    var ktb = el('tbody');
    kinds.forEach(function (k) {
      var b = byKind[k], tr = el('tr');
      add(tr, el('td', null, KIND_ROW[k] || k), el('td', 'n', int0.format(b.n)), el('td', 'n', int0.format(b.none)), el('td', 'n', int0.format(b.all_four)));
      add(ktb, tr);
    });
    add(kt, ktb);
    add(asideB, kt);
    add(aside, asideA, asideB);
    add(grid, main, aside);
    add(card, grid);
    add(card, caveatBox(st), sourceLine(st));
    return card;
  }

  // ---------- 3. the ledgers side by side ----------
  function secLedgers() {
    var st = stat('ledgers'), v = st.values, n = st.denominator.n;
    var card = section('ledgers', 'The ledgers side by side', st);
    var VAR = { penalties: '--s-penalty', state_payments: '--s-contract', donations_ocpf: '--s-donation', donations_fec: '--s-donation-fed', lobbying: '--s-lobbying' };
    var leds = el('div', 'cx-leds');
    v.rows.forEach(function (r) {
      var c = el('div', 'cx-led'), h = el('h4');
      var d = el('span', 'cdot' + (r.id === 'donations_fec' ? ' hatch' : ''));
      d.style.setProperty('--c', 'var(' + VAR[r.id] + ')');
      d.setAttribute('aria-hidden', 'true');
      add(h, d, el('span', null, r.label));
      var val = el('p', 'cx-led-v mono', money(r.amount));
      val.title = usd0.format(r.amount);
      var m = el('p', 'cx-led-m');
      add(m, el('span', null, r.id === 'penalties' ? int0.format(r.n_companies) + ' companies and institutions' : int0.format(r.n_companies) + ' of ' + int0.format(n) + ' companies'),
        el('span', 'mono', r.period));
      add(c, h, val, m, el('p', 'cx-led-n', r.note));
      if (r.id === 'penalties') {
        var note = el('span', 'hnote', 'Cash paid only. ');
        var a = el('a', null, 'Amounts not counted');
        a.href = '?tab=excluded';
        add(note, a);
        add(c, note);
      }
      add(leds, c);
    });
    add(card, leds);
    var never = caveat(st, 'OCPF (state) and FEC (federal)'), span = caveat(st, 'The five rows cover different spans');
    add(card, el('p', 'cx-note', [never, span].filter(Boolean).join(' ')));
    var cc = v.payments_concentration;
    if (cc && cc.top && cc.top.length) {
      var cn = el('p', 'cx-note cx-conc');
      var inst = (cc.by_kind || {})['institution/nonprofit'];
      add(cn, el('strong', null, 'Who the state payments went to: '), countWord(cc.top.length) + ' payees (' + joinNames(cc.top.map(function (t) { return t.name; })) + ') received ',
        pct(cc.top_share), ' of state payments, ', pct(cc.top_departments_share_of_top), ' of that from ' + joinNames(cc.top_department_labels.map(function (l) { return 'the ' + l; })) + '. ',
        cc.top[0].name + ' alone is ', pct(cc.top[0].share, 1), ' of the dollars.', inst ? ' Institutions and nonprofits take ' + pct(inst.share, 1) + ' of the dollars.' : '');
      add(card, cn);
    }
    var det = el('details', 'dt'), sum = el('summary', null, 'Exact figures');
    var tw = el('div', 'tscroll'), t = el('table', 'mini');
    var hr = el('tr');
    add(hr, el('th', null, 'Ledger'), el('th', null, 'Dollars'), el('th', null, 'Companies'), el('th', null, 'Period'));
    add(t, add(el('thead'), hr));
    var tb = el('tbody');
    v.rows.forEach(function (r) {
      var tr = el('tr');
      add(tr, el('td', null, r.label), el('td', null, usd0.format(r.amount)), el('td', null, int0.format(r.n_companies)), el('td', null, r.period));
      add(tb, tr);
    });
    add(t, tb);
    add(det, sum, add(tw, t));
    add(card, det);
    add(card, caveatBox(st, [never, span]), sourceLine(st));
    return card;
  }

  // ---------- 4. sequence ----------
  function secSequence() {
    var st = stat('sequence'), v = st.values, n = v.n_penalized;
    var card = section('sequence', 'Paid by the state in the same fiscal year as a penalty, and in later ones', st);
    var grid = el('div', 'cx-grid seq'), left = el('div'), right = el('div');

    add(left, el('h4', 'cx-h4', 'Companies paid by the state'));
    add(left, el('p', 'cx-sub', 'Out of ' + int0.format(n) + '. A company can be in several rows.'));
    var ul = el('ul', 'cx-meter');
    [['Paid in any fiscal year', v.n_paid_any_year], ['Paid in the same fiscal year as one of their penalties', v.n_paid_same_fy],
      ['Paid in a later fiscal year than their first penalty', v.n_paid_later_fy], ['Paid in an earlier fiscal year than their first penalty', v.n_paid_before_first_penalty_fy]
    ].forEach(function (r) {
      var li = el('li'), r1 = el('span', 'r1'), tr = el('span', 'cx-track'), f = el('span', 'cx-fill s');
      f.style.setProperty('--c', 'var(--s-contract)');
      f.style.width = pctW(r[1], n);
      add(r1, el('span', null, r[0]), el('span', 'mono', int0.format(r[1])));
      add(tr, f);
      add(li, r1, tr);
      add(ul, li);
    });
    add(left, ul);
    var cov = LEDGER.coverage.contracts;
    var dol = el('ul', 'cx-dol');
    [[v.dollars_same_fy, "Net payments in the fiscal years of their penalties: the whole year's payments, not payments for the penalized matter."],
      [v.dollars_after_first_penalty_fy, "Net payments in the fiscal years after each company's first penalty in the window."],
      [v.dollars_all_years, 'Net payments in all years, ' + cov.from + ' to ' + cov.to + '. The newest fiscal year is partial.']
    ].forEach(function (r) {
      var li = el('li'), m = el('span', 'mono', money(r[0]));
      m.title = usd0.format(r[0]);
      add(li, m, el('span', null, r[1]));
      add(dol, li);
    });
    add(left, dol);
    var fy = caveat(st, 'The records give state payments by fiscal year');
    if (fy) add(left, el('p', 'cx-note', fy));

    add(right, el('h4', 'cx-h4', 'The largest same-year pairs'));
    add(right, el('p', 'cx-sub', int0.format(v.n_same_fy_pairs) + ' company and fiscal-year pairs have a state payment and a penalty in the same fiscal year. The ' +
      int0.format(v.examples.length) + ' with the most dollars paid that year are listed; select a name to open the company in the Ledger.'));
    var ex = el('ul', 'cx-ex');
    v.examples.forEach(function (e) {
      var li = el('li');
      var pen = e.penalties.map(function (p) { return p.agency + ', ' + p.date + ', ' + money(p.amount); }).join('; ');
      var l2 = el('span', 'l2');
      add(l2, el('span', 'mono', fyLabel(e.fiscal_year)), ' state payments ', mono(money(e.paid_that_fy)));
      add(li, companyButton(e.company_id, e.name), l2, el('span', 'l3', plural(e.penalties.length, 'Penalty in that fiscal year: ', 'Penalties in that fiscal year: ') + pen));
      add(ex, li);
    });
    add(right, ex);
    add(grid, left, right);
    add(card, grid);
    add(card, caveatBox(st, [fy]), sourceLine(st));
    return card;
  }

  // ---------- 5. criminal cases ----------
  function agencyName(a) {
    var p = String(a || '').split('_');
    return [p[0]].concat(p.slice(1).map(function (x) { return x.toLowerCase(); })).join(' ');
  }
  function dateRange(a, b) {
    var s = el('span', 'k');
    add(s, el('span', 'nw mono', a), ' to ', el('span', 'nw mono', b));
    return s;
  }
  // A plea has two dates (the plea, then the judgment); an agreement (deferred, non-prosecution) has one; a trial has a judgment.
  function caseWhen(r) {
    var s = el('span');
    if (r.agreement === 'plea') {
      add(s, 'plea ', r.plea_date ? el('span', 'nw mono', r.plea_date) : 'date not in the registry',
        r.judgment_date ? ', judgment ' : ', registry date ', el('span', 'nw mono', r.judgment_date || r.date));
    } else if (r.agreement === 'trial') {
      add(s, r.judgment_date ? 'trial, judgment ' : 'trial, registry date ', el('span', 'nw mono', r.judgment_date || r.date));
    } else add(s, el('span', 'nw mono', r.date), ' ' + (AGREEMENT[r.agreement] || r.agreement));
    return s;
  }
  function crimRow(e) {
    var tr = el('tr');
    var co = el('td', 'co');
    var p = e.paid_by_state, d = e.donations, l = e.lobbying;
    var inPay = p.total > 0, inDon = d.ocpf + d.fec > 0, inLob = l.total > 0;
    add(co, companyButton(e.company_id, e.name));
    var rd = el('span', 'row-dots');
    add(rd, dots([{ on: inPay, v: REC[0].v }, { on: inDon, v: REC[1].v }, { on: inLob, v: REC[2].v }]));
    add(co, rd);
    add(tr, co);

    var tc = el('td'); tc.setAttribute('data-label', 'Criminal case');
    e.criminal_rows.forEach(function (r) {
      var c = el('span', 'case');
      add(c, caseWhen(r), ', ' + agencyName(r.agency) + ', ', mono(money(r.amount)),
        r.counted ? '' : ' (restates another row, not counted twice)');
      add(tc, c);
    });
    add(tr, tc);

    if (!inPay && !inDon && !inLob) {
      var none = el('td', 'nr', 'Not in state payments, donations or lobbying.');
      none.colSpan = 3;
      add(tr, none);
      return tr;
    }

    var tp = el('td'); tp.setAttribute('data-label', 'State payments');
    if (inPay) {
      add(tp, mono(money(p.total)), el('span', 'k', fyLabel(p.first_fy) + ' to ' + fyLabel(p.last_fy) + ', ' + int0.format(p.n_fiscal_years) + ' fiscal ' + plural(p.n_fiscal_years, 'year', 'years')),
        el('span', 'k', p.paid_same_fy_as_a_criminal_row ? 'Includes a fiscal year with a criminal row.' : 'No payment in a fiscal year with a criminal row.'));
    } else add(tp, el('span', 'none', 'None'));
    add(tr, tp);

    var td = el('td'); td.setAttribute('data-label', 'Donations by employees');
    if (inDon) {
      if (d.ocpf > 0) add(td, add(el('span', 'case'), 'State (OCPF) ', mono(money(d.ocpf))));
      if (d.fec > 0) add(td, add(el('span', 'case'), 'Federal (FEC) ', mono(money(d.fec))));
      add(td, el('span', 'k', int0.format(d.n) + ' ' + plural(d.n, 'gift', 'gifts')), dateRange(d.first_date, d.last_date));
    } else add(td, el('span', 'none', 'None'));
    add(tr, td);

    var tl = el('td'); tl.setAttribute('data-label', 'Lobbying');
    if (inLob) add(tl, mono(money(l.total)), el('span', 'k', l.first_year + ' to ' + l.last_year));
    else add(tl, el('span', 'none', 'None'));
    add(tr, tl);
    return tr;
  }
  function secCriminal() {
    var st = stat('criminal'), v = st.values;
    var card = section('criminal', 'Criminal cases and the other records', st);
    var sum = el('p', 'cx-note');
    add(sum, num(v.n_companies), ' ' + noun(v.n_companies) + ' have a criminal row. ', num(v.n_paid), ' were paid by the state, ', num(v.n_donated),
      ' have employee donations and ', num(v.n_lobbied), ' lobbied. ', num(v.n_any), ' appear in at least one of the three, ', num(v.n_all_three), ' in all three and ', num(v.n_none), ' in none.');
    add(card, sum);
    var tools = el('div', 'cx-tools');
    var wrap = el('div', 'tw');
    var tbl = el('table', 'cx-crim'), tb = el('tbody');
    function fill() {
      tb.textContent = '';
      v.companies.filter(function (e) {
        var any = e.paid_by_state.total > 0 || e.donations.ocpf + e.donations.fec > 0 || e.lobbying.total > 0;
        return ui.crim === 'all' || (ui.crim === 'any' ? any : !any);
      }).forEach(function (e) { add(tb, crimRow(e)); });
    }
    add(tools, seg('Show', [['all', 'All ' + int0.format(v.n_companies)], ['any', 'In another record ' + int0.format(v.n_any)], ['none', 'In none ' + int0.format(v.n_none)]], ui.crim,
      function (k) { ui.crim = k; fill(); }));
    add(card, tools);
    var hr = el('tr');
    ['Company', 'Criminal case', 'State payments', 'Donations by employees', 'Lobbying'].forEach(function (t, i) { add(hr, el('th', 'c' + (i + 1), t)); });
    add(tbl, el('caption', 'sr', 'Companies with a criminal row, with the dates of the case and of the other records'), add(el('thead'), hr), tb);
    fill();
    add(wrap, tbl);
    add(card, wrap);
    add(card, el('p', 'cx-sub', 'Dates are shown so the order can be read. Nothing more is claimed about it. The three small dots under a name show which of state payments, donations and lobbying the company appears in.'));

    if (v.n_held_individuals > 0) {
      add(card, el('p', 'cx-held', countWord(v.n_held_individuals) + ' named ' + plural(v.n_held_individuals, 'individual is', 'individuals are') +
        ' held pending confirmation. A person who donated and is named in a case is listed only after the identity and the outcome of the case are confirmed from primary documents.'));
    }
    if (v.named_individuals && v.named_individuals.length) {
      var box = el('div', 'cx-people');
      add(box, el('h4', 'cx-h4', 'Individuals named in these cases who also appear as donors'));
      add(box, el('p', 'cx-sub', caveat(st, 'Named individuals are linked only when')));
      var ul = el('ul');
      v.named_individuals.forEach(function (p) {
        var li = el('li');
        var basis = String(p.basis || '').replace('+', ' and ');
        add(li, add(el('span'), el('b', null, p.person_name), ', ' + p.role + '.'),
          add(el('span'), 'Company: ', companyButton(p.company_id)),
          add(el('span'), 'Gave ', mono(usd0.format(p.amount)), ' to ' + p.recipient_name + ' on ', mono(p.date), ', matched on ' + basis + '.'),
          add(el('span'), link(p.case_source_url, 'Case document (' + host(p.case_source_url) + ')'), '; ', link(p.donation_source_url, 'Contribution record (' + host(p.donation_source_url) + ')')));
        add(ul, li);
      });
      add(box, ul);
      add(card, box);
    }
    add(card, caveatBox(st, [caveat(st, 'Named individuals are linked only when')]), sourceLine(st));
    return card;
  }

  // ---------- 6. who received the employee donations ----------
  var INST = 'institution/nonprofit';
  // "Of this, 5% is from employees of institutions and nonprofits; the three largest are A, B and C."
  function kindSentence(by_kind, top, lead) {
    var i = (by_kind || {})[INST];
    if (!i || !(i.share > 0)) return lead + ', none is from employees of institutions and nonprofits.';
    var names = (top || []).map(function (t) { return t.name; });
    return lead + ', ' + pct(i.share) + ' is from employees of institutions and nonprofits' +
      (names.length ? '; the ' + (names.length > 1 ? int0.format(names.length) + ' largest are ' : 'largest is ') + joinNames(names) : '') + '.';
  }
  function secRecipients() {
    var st = stat('recipients'), v = st.values;
    var card = section('recipients', 'Who received the employee donations', st);
    var donors = caveat(st, 'These are donations by individuals'), lawful = caveat(st, 'Donations are lawful and public');
    add(card, el('p', 'cx-note', [donors, lawful].filter(Boolean).join(' ')));
    var grid = el('div', 'cx-grid two');
    [['ocpf', 'State: candidates and committees (OCPF)', false], ['fec', 'Federal: candidates and committees (FEC)', true]].forEach(function (g) {
      var r = v[g[0]], col = el('div');
      add(col, el('h4', 'cx-h4', g[1]));
      add(col, el('p', 'cx-sub', int0.format(r.n_donations_all) + ' donations to ' + int0.format(r.n_recipients) + ' recipients, ' + money(r.total_all) + ' in all. The ' +
        int0.format(r.top.length) + ' below received ' + money(r.top_total) + '.'));
      add(col, el('p', 'cx-sub cx-kindline', kindSentence(r.by_kind, r.top_institutions, 'Of all of this money')));
      var ol = el('ol', 'cx-rank'), top = r.top.length ? r.top[0].total : 0;
      r.top.forEach(function (x) {
        var li = el('li'), nm = el('span', 'nm');
        add(nm, x.name, x.office ? el('span', 'off', x.office) : null);
        var bar = el('span', 'bar'), f = el('span', 'cx-fill s' + (g[2] ? ' hatch' : ''));
        f.style.setProperty('--c', 'var(' + (g[2] ? '--s-donation-fed' : '--s-donation') + ')');
        f.style.width = pctW(x.total, top);
        add(bar, f);
        add(li, el('span', 'rk', String(x.rank)), nm, el('span', 'v1 mono', money(x.total)), bar,
          el('span', 'meta', int0.format(x.n_donations) + ' ' + plural(x.n_donations, 'donation', 'donations') + ' by employees of ' + int0.format(x.n_companies) + ' penalized companies and institutions'),
          el('span', 'meta kind', kindSentence(x.by_kind, x.top_institutions, 'Of this')));
        add(ol, li);
      });
      add(col, ol);
      add(grid, col);
    });
    add(card, grid);
    add(card, caveatBox(st, [donors, lawful]), sourceLine(st));
    return card;
  }

  // ---------- 7. officials' disclosed ties ----------
  function secOfficials() {
    var st = stat('officials'), v = st.values;
    var card = section('officials', "Officials' disclosed ties", st);
    var grid = el('div', 'cx-grid two'), left = el('div'), right = el('div');
    var big = el('p', 'cx-big');
    add(big, num(v.n_officials_excluding_mortgage), ' ' + plural(v.n_officials_excluding_mortgage, 'official', 'officials') +
      " disclosed a tie, their own or a spouse's, to a penalized company, not counting mortgages. Annual filings, " + v.first_year + ' to ' + v.last_year + '.');
    add(left, big);
    var kinds = Object.keys(v.by_kind).filter(function (k) { return k !== 'mortgage'; }).sort(function (a, b) { return v.by_kind[b].officials - v.by_kind[a].officials; });
    var kmax = kinds.length ? v.by_kind[kinds[0]].officials : 0, ksum = 0;
    add(left, el('h4', 'cx-h4', 'By kind of tie, mortgages left out'));
    var ul = el('ul', 'cx-kinds');
    kinds.forEach(function (k) {
      var b = v.by_kind[k], li = el('li'), r1 = el('span', 'r1'), f = el('span', 'cx-fill s');
      ksum += b.officials;
      f.style.setProperty('--c', 'var(--s-holding)');
      f.style.width = pctW(b.officials, kmax);
      add(r1, el('span', null, KIND_NAME[k] || k.replace(/_/g, ' ')), el('span', 'mono', int0.format(b.officials) + ' ' + plural(b.officials, 'official', 'officials') + ', ' + int0.format(b.rows) + ' ' + plural(b.rows, 'row', 'rows')));
      add(li, r1, f);
      add(ul, li);
    });
    add(left, ul);
    if (ksum > v.n_officials_excluding_mortgage) add(left, el('p', 'cx-sub', 'The kinds add to more than the headline because one official can have several.'));

    var m = v.by_kind.mortgage, apart = el('p', 'cx-apart');
    if (m) {
      add(apart, el('strong', null, 'Mortgage ties, shown apart: '), int0.format(m.officials) + ' ' + plural(m.officials, 'official lists', 'officials list') + ' a mortgage with a penalized lender (',
        int0.format(m.rows) + ' ' + plural(m.rows, 'row', 'rows') + '). A mortgage is an ordinary lender relationship, so it is left out of the figure above. Counting every kind, the filings hold ',
        el('span', 'mono', int0.format(v.n_officials)), ' ' + plural(v.n_officials, 'official', 'officials') + ' across ' + int0.format(v.n_companies) + ' ' + noun(v.n_companies) + ' and institutions.');
    } else add(apart, el('strong', null, 'Mortgage ties, shown apart: '), 'none in this lens.');
    add(left, apart);

    add(right, el('h4', 'cx-h4', 'Companies named by the most officials, mortgages left out'));
    var ol = el('ol', 'cx-rank stack-v'), top = v.top_companies_excluding_mortgage, tmax = top.length ? top[0].officials : 0;
    top.forEach(function (c, i) {
      var li = el('li'), nm = el('span', 'nm'), bar = el('span', 'bar'), f = el('span', 'cx-fill s');
      add(nm, companyButton(c.company_id, c.name));
      f.style.setProperty('--c', 'var(--s-holding)');
      f.style.width = pctW(c.officials, tmax);
      add(bar, f);
      add(li, el('span', 'rk', String(i + 1)), nm, el('span', 'v1 mono', int0.format(c.officials) + ' ' + plural(c.officials, 'official', 'officials') + ', ' + int0.format(c.rows) + ' ' + plural(c.rows, 'row', 'rows')), bar);
      add(ol, li);
    });
    add(right, ol);
    add(grid, left, right);
    add(card, grid);
    add(card, caveatBox(st), sourceLine(st));
    return card;
  }

  // ---------- 8. regulator findings ----------
  // Always the same facts whatever the lens: the findings of improper payments are stated first, from the all-lenses list,
  // each with its quote, its source and its lens. The lens only says how many of them the Ledger's totals include.
  var CAT = { improper_payments_to_officials: 'Improper payments to officials', political_finance: 'Political-finance violation' };
  var TAG = { political_finance: 'political-finance (campaign contributions)' };
  var CRIME = { FCPA: 'FCPA (Foreign Corrupt Practices Act)' };
  var DISP = { NP: 'non-prosecution agreement', DP: 'deferred prosecution agreement', plea: 'plea', trial: 'trial' };
  var ADMIT = { yes: 'yes', no: 'no', neither: 'neither admitted nor denied', '': 'not stated' };
  function catName(c) { return CAT[c] || String(c).replace(/_/g, ' '); }
  function findingCard(f, inLens) {
    var box = el('div', 'cx-find'), left = el('div'), right = el('div');
    add(left, el('h4', 'cx-h4', catName(f.category) + ': ' + f.name));
    add(left, el('blockquote', 'cx-quote', f.quote));
    add(left, el('p', 'cx-note', f.scope_note));
    add(left, el('p', 'cx-sub', 'Text read from: ' + f.text_source + '.'));
    var dl = el('dl', 'cx-facts');
    function fact(k, node) { add(dl, el('dt', null, k), add(el('dd'), node)); }
    var rg = f.registry;
    fact('Agency', agencyName(f.agency) + (agencyName(f.agency).toLowerCase().indexOf(f.case_type) >= 0 ? '' : ', ' + f.case_type));
    fact('Date', rg ? add(el('span'), mono(f.date), " (the registry's date for the agreement)") : mono(f.date));
    fact('Admitted', ADMIT[f.admitted || ''] || f.admitted);
    fact('Amount counted', mono(usd0.format(f.amount)));
    if (rg) {
      var parts = [];
      if (rg.fine) parts.push('fine ' + usd0.format(rg.fine));
      if (rg.forfeiture_disgorgement) parts.push('disgorgement or forfeiture ' + usd0.format(rg.forfeiture_disgorgement));
      if (parts.length) fact('Made up of', mono(parts.join(', ')));
      fact('Kind of record', (DISP[rg.disposition_type] || rg.disposition_type) + (rg.disposition_type === 'NP' || rg.disposition_type === 'DP' ? '; not a conviction' : ''));
      fact('Registry crime code', CRIME[rg.crime_code] || rg.crime_code);
      fact('Registry country', rg.country);
      fact('Registry jurisdictions', rg.jurisdiction);
    }
    fact('Lens', lensPhrase(f.lens) + (inLens ? ', the lens now selected' : ', not the one now selected'));
    (f.tags || []).forEach(function (t) { fact('Also', TAG[t] || t.replace(/_/g, ' ')); });
    fact('Source', add(el('span'), link(f.url, host(f.url)), rg ? ' (the registry data file: a summary of the agreement; the agreement itself is not linked here)' : ''));
    add(right, dl);
    var open = el('button', 'more', 'Open ' + f.name + ' in the Ledger');
    open.type = 'button'; open.setAttribute('data-open', f.company_id);
    add(right, open);
    return add(box, left, right);
  }
  function secFindings() {
    var st = stat('regulator_findings'), v = st.values, lens = API.lens();
    var all = lens === 'all' ? st : stat('regulator_findings', 'all');
    var A = all.values;
    var card = section('findings', st.label, st);
    var here = {};
    v.findings.forEach(function (f) { here[f.finding_id] = 1; });
    var improper = A.findings.filter(function (f) { return f.category === 'improper_payments_to_officials'; });
    var rest = A.findings.filter(function (f) { return f.category !== 'improper_payments_to_officials'; });
    var scope = caveat(st, 'The search read the penalty notes');

    var fixed = el('div', 'cx-fixed'), fl = el('div'), fr = el('div');
    if (improper.length) {
      add(fl, el('p', 'cx-plain', 'The data holds ' + int0.format(improper.length) + ' regulator ' + plural(improper.length, 'finding', 'findings') +
        ' of improper payments to public officials, under any lens: ' +
        joinNames(improper.map(function (f) { return f.name + ' (' + agencyName(f.agency) + ', ' + f.date + ')'; })) + '. ' +
        (improper.length === 1 ? 'It is the only one found in the data.' : 'These are the only ones found in the data.')));
    } else add(fl, el('p', 'cx-plain', 'No regulator finding of improper payments to public officials is in the data, under any lens.'));
    add(fl, el('p', 'cx-sub', scope));
    var elsewhere = A.findings.filter(function (f) { return !here[f.finding_id]; });
    add(fr, el('p', 'cx-sub', lens === 'all' ?
      'Under all lenses: ' + v.result + '.' :
      'Under the ' + LENS_NAME[lens] + ' lens the Ledger counts ' + int0.format(v.findings.length) + ' of these ' + int0.format(A.findings.length) +
        ' findings (' + v.result + '). The others sit under another lens and are shown here with their lens.'));
    if (elsewhere.length) {
      var sw = el('button', 'more', 'Show the ' + lensPhrase(elsewhere[0].lens));
      sw.type = 'button'; sw.setAttribute('data-setlens', elsewhere[0].lens);
      add(fr, sw);
    }
    add(fixed, fl, fr);
    add(card, fixed);

    var list = el('div', 'cx-finds');
    improper.concat(rest).forEach(function (f) { add(list, findingCard(f, !!here[f.finding_id])); });
    if (!A.findings.length) add(list, el('p', 'cx-plain', 'No regulator finding of this kind is in the data (' + A.result + ').'));
    add(card, list);

    var tools = el('div', 'cx-find-tools');
    var seen = v.considered_not_counted || [];
    if (seen.length) {
      var det = el('details', 'cx-det'), ul2 = el('ul');
      add(det, el('summary', null, int0.format(seen.length) + ' ' + plural(seen.length, 'row matched', 'rows matched') + ' a search term and ' + plural(seen.length, 'is', 'are') + ' not counted as findings'));
      seen.forEach(function (x) { add(ul2, add(el('li'), el('b', null, nameOf(x.company_id)), ' (matched: ' + x.terms_matched + '). ' + x.reason)); });
      add(det, ul2);
      add(tools, det);
    }
    var det2 = el('details', 'cx-det');
    add(det2, el('summary', null, 'What was searched'));
    add(det2, el('p', 'cx-sub', 'Terms: ' + v.search_terms.join(', ') + '. Fields: ' + v.searched.fields.join('; ') + '. Penalty rows read under this lens: ' + int0.format(v.searched.penalty_rows) + '.'));
    add(tools, det2);
    add(card, tools);
    add(card, caveatBox(st, [scope]), sourceLine(st));
    return card;
  }

  // ---------- assembly ----------
  function renderBody() {
    var body = $('cx-body');
    body.textContent = '';
    [secOverlap, secLedgers, secSequence, secCriminal, secRecipients, secOfficials, secFindings].forEach(function (f) { add(body, f()); });
  }
  function renderFinal() {
    var latest = '';
    (IW.inputs || []).forEach(function (i) { if (i.retrieved_max && i.retrieved_max > latest) latest = i.retrieved_max; });
    var box = $('cx-disclaimer');
    box.textContent = LEDGER.disclaimer + ' Audited statistics generated ' + IW.generated + '; source tables retrieved through ' + latest + '.';
    var oc = $('cx-owner-caveat');
    if (oc) oc.textContent = caveat(stat('reach'), 'Appearing in two lists');
  }
  function renderAll() {
    if (!IW) {
      $('cx-headline').textContent = 'The audited statistics are not in the ledger file (data/ledger.json). Reload the page to try again.';
      return;
    }
    renderHead();
    renderTeaser();
    renderBody();
    renderFinal();
    document.documentElement.dataset.connectsReady = API.lens();
  }

  function init() {
    // delegated: overlap rows, company names and the lens switches
    var root = $('tab-connects');
    root.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('[data-combo],[data-open],[data-setlens]');
      if (!t || !root.contains(t)) return;
      if (t.hasAttribute('data-combo')) API.openCombo(t.getAttribute('data-combo'));
      else if (t.hasAttribute('data-open')) API.openCompany(t.getAttribute('data-open'));
      else API.setLens(t.getAttribute('data-setlens'));
    });
    Array.prototype.forEach.call(document.querySelectorAll('#cx-lens button'), function (b) {
      b.addEventListener('click', function () { API.setLens(b.getAttribute('data-lens')); });
    });
    API.whenReady(function (d) {
      LEDGER = d;
      IW = d.intertwined || null;
      renderAll();
      API.onLens(function () { if (IW) renderAll(); });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
