/* Ledger tab: reads data/ledger.json (and data/graph.json for payments by payer and donations by year), renders the
   six KPI tiles, four linked charts, a company panel with a combined timeline of all five streams, and a sortable,
   filterable table. All text goes in through textContent or the esc() helper; only http(s) source URLs become links.
   Colours are read from the CSS variables in corporate-ledger.html (--s-*, --pay-*); none is written here.
   View state lives in the URL hash so a view can be shared:
     #co=<company_id>&lens=ma_conduct|ma_hq|all&q=text&f=crim,xa,don,lob,grp&kind=company|inst&sort=key&dir=asc|desc
      &hide=col,col&rf=<stream>&ry=<year>&cb=<records>
   cb is the "How it connects" filter: the companies that appear in exactly these records (payments, donations, lobbying,
   holdings joined by +, or none). The older query parameters still work: ?lens= ?q= ?sort= ?expand=<company_id> (opens
   that company). window.LEDGER_API (bottom of this file) is what assets/connects.js uses. */
(function () {
  'use strict';

  var LENS_NAME = { ma_conduct: 'Massachusetts case', ma_hq: 'Massachusetts headquarters', all: 'all lenses' };
  var STREAMS = [
    ['penalty', 'penalty'], ['contract', 'state payment'], ['donation', 'donation'],
    ['lobbying', 'lobbying'], ['holding', 'disclosed tie'], ['person_link', 'named individual']
  ];
  var STREAM_LABEL = {};
  STREAMS.forEach(function (s) { STREAM_LABEL[s[0]] = s[1]; });
  var PAGE = 50;          // table rows per step
  var REC_PAGE = 60;      // records per step in the company panel
  var PAYERS = ['CTHRU', 'MBTA', 'MASSPORT', 'MSBA'];   // stack order, darkest step at the base
  var PAYER_NAME = { CTHRU: 'CTHRU (state agencies)', MBTA: 'MBTA', MASSPORT: 'Massport', MSBA: 'MSBA (school building authority)' };
  var FILTERS = {
    crim: function (c) { return (c.penalties.criminal || 0) > 0; },
    xa: function (c) { return !!c.excluded; },
    don: function (c) { return (c.donations.ocpf || 0) + (c.donations.fec || 0) > 0; },
    lob: function (c) { return (c.lobbying.firm_fee || 0) + (c.lobbying.in_house || 0) > 0; },
    grp: function (c) { return !!(c.entities && c.entities.length > 1); }
  };
  var FILTER_NAME = { crim: 'criminal case', xa: 'amounts not counted', don: 'donations', lob: 'lobbying', grp: 'co-defendant group' };

  // The four records a company can appear in besides its penalties. A company "appears" in a record when its total there is
  // above zero; pipeline/intertwined.py (_flags) applies the same rule to the same fields, so the counts match. Officials'
  // disclosed ties leave out mortgage lenders (an ordinary lender relationship): holdings is true when the company has a
  // confirmed tie of any other kind (c.holdings.by_kind), the rule the audited counts use.
  function hasTie(c) {
    var k = (c.holdings || {}).by_kind || {};
    return Object.keys(k).some(function (x) { return x !== 'mortgage' && k[x] > 0; });
  }
  var RECORDS = ['payments', 'donations', 'lobbying', 'holdings'];
  var REC_WORD = { payments: 'state payments', donations: 'donations', lobbying: 'lobbying', holdings: "officials' ties" };
  function recordFlags(c) {
    return {
      payments: (c.contracts.total || 0) > 0,
      donations: (c.donations.ocpf || 0) + (c.donations.fec || 0) > 0,
      lobbying: (c.lobbying.firm_fee || 0) + (c.lobbying.in_house || 0) > 0,
      holdings: hasTie(c)
    };
  }
  function comboKey(c) {
    var f = recordFlags(c), k = RECORDS.filter(function (r) { return f[r]; });
    return k.length ? k.join('+') : 'none';
  }
  function validCombo(k) {
    if (k === 'none') return true;
    var parts = String(k || '').split('+');
    return parts.every(function (p, i) { return RECORDS.indexOf(p) >= 0 && (i === 0 || RECORDS.indexOf(parts[i - 1]) < RECORDS.indexOf(p)); });
  }
  function comboLabel(k) {
    if (k === 'none') return 'no other record';
    return k.split('+').map(function (p) { return REC_WORD[p]; }).join(' + ');
  }
  var KIND = {
    all: function () { return true; },
    company: function (c) { return c.kind === 'company'; },
    inst: function (c) { return c.kind === 'institution/nonprofit'; }
  };

  // Names of the same company group, compared without legal-form words, for the "matched as" chip.
  var LEGAL = /\b(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LLC|L L C|LTD|LIMITED|LP|LLP|PLC|NA|N A|THE|PC|P C)\b/g;
  function nameKey(s) {
    return String(s || '').toUpperCase().replace(/&/g, ' AND ').replace(/[^A-Z0-9 ]+/g, ' ').replace(LEGAL, ' ')
      .replace(/\s+/g, ' ').trim();
  }
  // The vendor, payer or donor employer text a record was matched on, read from its label.
  function matchedName(it) {
    var L = it.label || '';
    if (it.stream === 'contract') return L.replace(/ \(FY\d{4}, [A-Z]+\)$/, '');
    if (it.stream === 'lobbying') { var i = L.lastIndexOf(' to '); return i > 0 ? L.slice(0, i) : ''; }
    if (it.stream === 'donation') { var j = L.indexOf('; employer '); return j >= 0 ? L.slice(j + 11) : ''; }
    return '';
  }
  function differs(name, canon) {
    var a = nameKey(name), b = nameKey(canon);
    if (!a || !b || a === b) return false;
    return (a + ' ').indexOf(b + ' ') !== 0 && (b + ' ').indexOf(a + ' ') !== 0;
  }
  function inclHtml(c, cls) {
    if (!c || !c.entities || c.entities.length < 2) return '';
    return '<span class="' + cls + '" title="' + esc(c.entities_note || '') + '">Includes: ' + esc(c.entities.join('; ')) + '</span>';
  }

  // Columns. dot: the stream colour variable shown beside the header; hatch marks the federal and in-house steps.
  var COLS = [
    { key: 'name', label: 'Company', short: 'Company', get: function (c) { return c.name.toLowerCase(); }, asc: true, fixed: true },
    { key: 'pen', label: 'Counted (gross)', short: 'Penalties counted', dot: '--s-penalty', get: function (c) { return penFor(c); } },
    { key: 'noadmit', label: 'Without admitting fault', short: 'Without admitting fault', get: function (c) { return c.penalties.admitted_share ? c.penalties.admitted_share.no_or_neither : -1; } },
    { key: 'con', label: 'State payments, FY2010 on', short: 'State payments', dot: '--s-contract', get: function (c) { return c.contracts.total || 0; } },
    { key: 'ocpf', label: 'State (OCPF)', short: 'Employee donations, state', dot: '--s-donation', get: function (c) { return c.donations.ocpf || 0; } },
    { key: 'fec', label: 'Federal (FEC)', short: 'Employee donations, federal', dot: '--s-donation-fed', hatch: true, get: function (c) { return c.donations.fec || 0; } },
    { key: 'firm', label: 'Firm fees', short: 'Lobbying firm fees', dot: '--s-lobbying', get: function (c) { return c.lobbying.firm_fee || 0; } },
    { key: 'inhouse', label: 'In-house', short: 'Lobbying in-house', dot: '--s-lobbying-in', hatch: true, get: function (c) { return c.lobbying.in_house || 0; } },
    { key: 'hold', label: "Officials' disclosed ties", short: "Officials' disclosed ties", dot: '--s-holding', get: function (c) { return c.holdings.n || 0; } }
  ];
  var COL = {};
  COLS.forEach(function (c) { COL[c.key] = c; });
  var GROUPS = [
    ['', ['name']], ['Penalties', ['pen', 'noadmit']], ['', ['con']], ['Employee donations, confirmed', ['ocpf', 'fec']],
    ['Lobbying, 2010 on', ['firm', 'inhouse']], ['', ['hold']]
  ];

  var DEFAULT = { lens: 'ma_conduct', q: '', sort: 'pen', dir: -1, kind: 'all' };
  var state = { lens: 'ma_conduct', q: '', sort: 'pen', dir: -1, sel: null, f: {}, kind: 'all', hide: {}, shown: PAGE, rf: null, ry: null, cb: '' };
  var LEDGER = null, BYID = {}, GD = null;
  var cache = {};
  var C = {};   // colours, read from CSS variables at start

  // ---------- formatting ----------
  var usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  var sig3 = new Intl.NumberFormat('en-US', { minimumSignificantDigits: 3, maximumSignificantDigits: 3 });
  var sig2 = new Intl.NumberFormat('en-US', { maximumSignificantDigits: 2 });
  var int0 = new Intl.NumberFormat('en-US');
  function money(n) {
    if (n === null || n === undefined || isNaN(n)) return '';
    var a = Math.abs(n), s = n < 0 ? '-' : '';
    if (a >= 1e9) return s + '$' + sig3.format(a / 1e9) + 'B';
    if (a >= 1e6) return s + '$' + sig3.format(a / 1e6) + 'M';
    return usd0.format(n);
  }
  function axisMoney(n) {
    var a = Math.abs(n);
    if (a >= 1e9) return '$' + sig2.format(n / 1e9) + 'B';
    if (a >= 1e6) return '$' + sig2.format(n / 1e6) + 'M';
    if (a >= 1e3) return '$' + sig2.format(n / 1e3) + 'K';
    return '$' + sig2.format(n);
  }
  function pct(x) { return Math.round(x * 100) + '%'; }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : null; }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return 'link'; } }
  function cssEsc(s) { return window.CSS && CSS.escape ? CSS.escape(s) : s.replace(/"/g, '\\"'); }
  function $(id) { return document.getElementById(id); }
  function cssv(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function reduced() { return window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches; }
  function trimTo(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '...' : s; }

  function readColours() {
    C = {
      penalty: cssv('--s-penalty'), contract: cssv('--s-contract'), donation: cssv('--s-donation'),
      donationFed: cssv('--s-donation-fed'), lobbying: cssv('--s-lobbying'), lobbyingIn: cssv('--s-lobbying-in'),
      holding: cssv('--s-holding'), person: cssv('--s-person'), surface: cssv('--card') || '#FFFFFF',
      pay: { CTHRU: cssv('--pay-cthru'), MBTA: cssv('--pay-mbta'), MASSPORT: cssv('--pay-massport'), MSBA: cssv('--pay-msba') }
    };
  }

  function penFor(c) {
    if (state.lens === 'all') return c.penalties.counted || 0;
    return (c.penalties.by_lens || {})[state.lens] || 0;
  }
  // A company is in a lens when it has a penalty row under it, even one whose cash counted is $0 (see Amounts not counted).
  function inLens(c) { return state.lens === 'all' || Object.prototype.hasOwnProperty.call(c.penalties.by_lens || {}, state.lens); }
  function anyFilter() { return Object.keys(state.f).some(function (k) { return state.f[k]; }) || state.kind !== 'all' || !!state.q.trim() || !!state.cb; }

  function visible() {
    var q = state.q.trim().toLowerCase();
    var col = COL[state.sort];
    return LEDGER.companies.filter(function (c) {
      if (!inLens(c) || !KIND[state.kind](c)) return false;
      if (state.cb && comboKey(c) !== state.cb) return false;
      for (var k in state.f) if (state.f[k] && !FILTERS[k](c)) return false;
      return !q || c.name.toLowerCase().indexOf(q) >= 0 || c.company_id.indexOf(q) >= 0 ||
        (c.entities || []).some(function (n) { return n.toLowerCase().indexOf(q) >= 0; });
    }).sort(function (x, y) {
      var a = col.get(x), b = col.get(y);
      if (a < b) return -state.dir;
      if (a > b) return state.dir;
      return x.name < y.name ? -1 : 1;
    });
  }

  // ---------- URL hash ----------
  function readUrl() {
    var h = location.hash.replace(/^#/, '');
    var fromHash = h.indexOf('=') >= 0;
    var p = new URLSearchParams(fromHash ? h : location.search);
    if (LENS_NAME[p.get('lens')]) state.lens = p.get('lens');
    state.q = p.get('q') || '';
    if (p.get('sort') && COL[p.get('sort')]) {
      state.sort = p.get('sort');
      state.dir = p.get('dir') === 'asc' ? 1 : p.get('dir') === 'desc' ? -1 : (COL[state.sort].asc ? 1 : -1);
    }
    state.f = {};
    (p.get('f') || '').split(',').forEach(function (k) { if (FILTERS[k]) state.f[k] = true; });
    state.kind = KIND[p.get('kind')] ? p.get('kind') : 'all';
    state.cb = validCombo(p.get('cb')) ? p.get('cb') : '';
    state.hide = {};
    (p.get('hide') || '').split(',').forEach(function (k) { if (COL[k] && !COL[k].fixed) state.hide[k] = true; });
    state.sel = p.get(fromHash ? 'co' : 'expand') || null;
    state.rf = p.get('rf') || null;
    state.ry = p.get('ry') ? +p.get('ry') : null;
  }
  function writeUrl() {
    var p = [];
    function add(k, v) { p.push(k + '=' + encodeURIComponent(v)); }
    if (state.sel) add('co', state.sel);
    if (state.lens !== DEFAULT.lens) add('lens', state.lens);
    if (state.q.trim()) add('q', state.q.trim());
    var f = Object.keys(state.f).filter(function (k) { return state.f[k]; });
    if (f.length) add('f', f.join(','));
    if (state.kind !== 'all') add('kind', state.kind);
    if (state.cb) add('cb', state.cb);
    if (state.sort !== DEFAULT.sort || state.dir !== DEFAULT.dir) { add('sort', state.sort); add('dir', state.dir < 0 ? 'desc' : 'asc'); }
    var hide = Object.keys(state.hide).filter(function (k) { return state.hide[k]; });
    if (hide.length) add('hide', hide.join(','));
    if (state.sel && state.rf) add('rf', state.rf);
    if (state.sel && state.ry) add('ry', state.ry);
    // keep ?tab=; drop the older ledger query parameters now that the hash carries them
    var qs = new URLSearchParams(location.search);
    ['lens', 'q', 'sort', 'expand'].forEach(function (k) { qs.delete(k); });
    var s = qs.toString();
    var url = location.pathname + (s ? '?' + s : '') + (p.length ? '#' + p.join('&') : '');
    if (url !== location.pathname + location.search + location.hash) history.replaceState(null, '', url);
  }

  // ---------- KPI tiles ----------
  var KPI_SORT = { pen: 'pen', con: 'con', ocpf: 'ocpf', fec: 'fec', lob: 'firm', hold: 'hold' };
  function renderKpis() {
    var L = LEDGER.lenses[state.lens] || {};
    var t = { con: 0, nc: 0, ocpf: 0, fec: 0, lob: 0, nl: 0, hold: 0, nh: 0 };
    LEDGER.companies.forEach(function (c) {
      if (!inLens(c)) return;
      if (c.contracts.total) { t.con += c.contracts.total; t.nc++; }
      t.ocpf += c.donations.ocpf || 0;
      t.fec += c.donations.fec || 0;
      var lb = (c.lobbying.firm_fee || 0) + (c.lobbying.in_house || 0);
      if (lb) { t.lob += lb; t.nl++; }
      if (c.holdings.n) { t.hold += c.holdings.n; t.nh++; }
    });
    var lensShort = state.lens === 'ma_conduct' ? 'MA case lens' : state.lens === 'ma_hq' ? 'MA HQ lens' : 'all lenses';
    $('k-pen').textContent = money(L.counted);
    $('k-pen-g').textContent = 'gross ' + money(L.gross);
    $('k-pen-l').textContent = 'Penalties counted, ' + lensShort;
    $('k-con').textContent = money(t.con);
    $('k-con-g').textContent = int0.format(t.nc) + ' companies paid';
    $('k-ocpf').textContent = money(t.ocpf);
    $('k-ocpf-g').textContent = 'confirmed matches';
    $('k-fec').textContent = money(t.fec);
    $('k-fec-g').textContent = 'never added to state';
    $('k-lob').textContent = money(t.lob);
    $('k-lob-g').textContent = int0.format(t.nl) + ' companies';
    $('k-hold').textContent = int0.format(t.hold) + ' rows';
    $('k-hold-g').textContent = int0.format(t.nh) + ' companies, mortgages included, 2019 to 2025';
    document.querySelectorAll('.kpi').forEach(function (b) {
      b.setAttribute('aria-pressed', String(KPI_SORT[b.dataset.kpi] === state.sort));
    });
  }
  function kpiClick(k) {
    if (currentTabName() !== 'ledger') {
      showTab($('btn-ledger'), 'ledger');
      var qs = new URLSearchParams(location.search); qs.delete('tab');
      history.replaceState(null, '', location.pathname + (qs.toString() ? '?' + qs : '') + location.hash);
    }
    var target = { pen: 'ch-top', con: 'ch-pay', ocpf: 'ch-don', fec: 'ch-don', lob: 'ch-lob', hold: 'ledger' }[k];
    if (k === 'ocpf' || k === 'fec') state.f.don = true;
    if (k === 'lob') state.f.lob = true;
    state.sort = KPI_SORT[k]; state.dir = -1; state.shown = PAGE;
    render();
    var el = $(target);
    if (k === 'hold') el = el.closest('.table-card');
    scrollToEl(el);
    el.classList.remove('pulse'); void el.offsetWidth; el.classList.add('pulse');
  }
  function currentTabName() { return typeof currentTab === 'string' ? currentTab : 'ledger'; }
  function navH() { var n = document.querySelector('.tab-nav'); return n ? n.getBoundingClientRect().height : 0; }
  function scrollToEl(el, onlyIfHidden) {
    if (!el) return;
    var r = el.getBoundingClientRect();
    if (onlyIfHidden && r.top >= navH() && r.top < window.innerHeight - 120) return;
    window.scrollTo({ top: r.top + window.pageYOffset - navH() - 10, behavior: reduced() ? 'auto' : 'smooth' });
  }

  // ---------- table ----------
  function colOn(k) { return !state.hide[k]; }
  function headers() {
    var grp = $('grp'), tr = $('cols');
    grp.innerHTML = ''; tr.innerHTML = '';
    GROUPS.forEach(function (g) {
      var n = g[1].filter(colOn).length;
      if (!n) return;
      var th = document.createElement('th');
      th.colSpan = n;
      if (g[0]) { th.className = 'g'; th.textContent = g[0]; th.scope = 'colgroup'; }
      grp.appendChild(th);
    });
    COLS.forEach(function (col) {
      if (!colOn(col.key)) return;
      var th = document.createElement('th');
      th.scope = 'col';
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'sort';
      if (col.dot) {
        var d = document.createElement('span');
        d.className = 'cdot' + (col.hatch ? ' hatch' : '');
        d.style.setProperty('--c', 'var(' + col.dot + ')');
        d.setAttribute('aria-hidden', 'true');
        b.appendChild(d);
      }
      b.appendChild(document.createTextNode(col.key === 'pen' ? 'Counted, gross below' : col.label));
      b.dataset.key = col.key;
      b.addEventListener('click', function () { setSort(col.key); });
      th.appendChild(b);
      if (col.key === 'pen') {
        // one-line note under the penalties header: what the figure is, and where the rest is listed
        var note = document.createElement('span');
        note.className = 'hnote';
        note.innerHTML = 'Cash paid only. <a href="?tab=excluded">Amounts not counted</a>';
        th.appendChild(note);
      }
      tr.appendChild(th);
    });
    var gh = grp.getBoundingClientRect().height;
    if (gh) document.documentElement.style.setProperty('--grph', gh + 'px');
  }
  function sortOptions() {
    var sel = $('sortsel');
    sel.innerHTML = '';
    COLS.forEach(function (col) {
      var o = document.createElement('option');
      o.value = col.key;
      o.textContent = col.short;
      sel.appendChild(o);
    });
    sel.addEventListener('change', function () { setSort(sel.value, true); });
  }
  function colMenu() {
    var box = $('colmenu-list');
    box.innerHTML = '';
    COLS.forEach(function (col) {
      if (col.fixed) return;
      var l = document.createElement('label');
      var i = document.createElement('input');
      i.type = 'checkbox';
      i.checked = colOn(col.key);
      i.addEventListener('change', function () { state.hide[col.key] = !i.checked; render(); });
      l.appendChild(i);
      l.appendChild(document.createTextNode(col.short));
      box.appendChild(l);
    });
  }

  function setSort(key, fromSelect) {
    var col = COL[key];
    if (state.sort === key && !fromSelect) state.dir = -state.dir;
    else { state.sort = key; state.dir = col.asc ? 1 : -1; }
    state.shown = PAGE;
    render();
  }

  function cell(key, label, html) { return colOn(key) ? '<td data-label="' + esc(label) + '">' + html + '</td>' : ''; }
  function val(n, zeroText) {
    if (!n) return '<span class="v zero">' + (zeroText || '$0') + '</span>';
    return '<span class="v">' + esc(money(n)) + '</span>';
  }
  var FY0 = 2010, FY1 = 2027;
  function spark(c) {
    var by = c.contracts.by_year || {};
    var max = 0, y;
    for (y = FY0; y <= FY1; y++) max = Math.max(max, by[y] || 0);
    if (!max) return '';
    var w = 3, gap = 1, H = 16, out = '';
    for (y = FY0; y <= FY1; y++) {
      var v = Math.max(0, by[y] || 0);
      var h = v ? Math.max(1, Math.round(v / max * H)) : 0;
      out += h ? '<rect x="' + ((y - FY0) * (w + gap)) + '" y="' + (H - h) + '" width="' + w + '" height="' + h + '" fill="' + C.contract + '"/>' :
        '<rect x="' + ((y - FY0) * (w + gap)) + '" y="' + (H - 1) + '" width="' + w + '" height="1" fill="' + cssv('--border') + '"/>';
    }
    return '<svg class="spark" width="' + ((FY1 - FY0 + 1) * (w + gap)) + '" height="' + H + '" aria-hidden="true" focusable="false">' + out + '</svg>';
  }

  // A company whose case is one total shared with its owners or co-defendants, with no split in the source document, carries a
  // dagger; the footnote under the table says what that means and how much money it covers (data/manual/shared-allocations.csv).
  function sharedNone(c) {
    var g = (c.penalties && c.penalties.overlap_groups) || [];
    return g.some(function (x) { return /^shared-/.test(x); });
  }
  function sharedFootnote() {
    var box = $('shared-fn');
    if (!box || !LEDGER) return;
    var sh = ((LEDGER.excluded_amounts || {}).shared_totals || {}).by_basis || {};
    var ns = sh.not_stated;
    if (!ns || !ns.n) { box.hidden = true; return; }
    var cos = LEDGER.companies.filter(sharedNone).length;
    box.innerHTML = '<span class="fnmark" aria-hidden="true">†</span> <b>Shared totals, not counted.</b> For ' + int0.format(ns.n) +
      ' payments, ' + esc(money(ns.shared_total_not_counted)) + ' in all, a company and its owners or co-defendants paid one total and the source ' +
      'document does not say how it divides. No company’s counted penalties include these amounts (' + int0.format(cos) + ' companies carry the dagger). ' +
      'Each stays in the gross figure and is listed under <a href="?tab=excluded">Amounts not counted</a>, with the document it came from.';
    box.hidden = false;
  }

  function rowHtml(c) {
    var p = c.penalties, open = state.sel === c.company_id;
    var lensVal = penFor(c);
    var pen = '<span class="v">' + esc(money(lensVal)) + '</span>';
    if (c.excluded) {
      pen += '<a class="xmark" href="?tab=excluded&amp;xq=' + encodeURIComponent(c.company_id) + '" title="' +
        'Some amounts in this company&#39;s cases are not counted: a larger headline, a payment counted on another row, or a shared total; see Amounts not counted"><span aria-hidden="true">*</span>' +
        '<span class="sr">Some amounts in this company&#39;s cases are not counted; see Amounts not counted</span></a>';
    }
    if (sharedNone(c)) {
      pen += '<a class="fnmark" href="#shared-fn" title="A shared total with no split in the source document is not counted for this company; see the footnote under the table" onclick="event.stopPropagation()"><span aria-hidden="true">†</span>' +
        '<span class="sr">Shared total not counted for this company; see the footnote under the table</span></a>';
    }
    if (p.gross && p.gross !== p.counted) {
      pen += '<span class="sub">gross ' + esc(money(p.gross)) + (state.lens === 'all' ? '' : ' (all lenses)') +
        ', <a href="#overlaps" title="Why gross and counted differ" onclick="event.stopPropagation()">note</a></span>';
    }
    if (state.lens === 'all' && p.by_lens) {
      var parts = [];
      if (p.by_lens.ma_conduct) parts.push('case ' + money(p.by_lens.ma_conduct));
      if (p.by_lens.ma_hq) parts.push('HQ ' + money(p.by_lens.ma_hq));
      if (parts.length > 1) pen += '<span class="sub">' + esc(parts.join(', ')) + '</span>';
    }
    var a = p.admitted_share || {};
    var noadmit;
    if (!p.counted) noadmit = '<span class="v zero">no cash counted</span>';
    else if (a.unknown >= 0.999) noadmit = '<span class="v zero">unknown</span>';
    else {
      noadmit = '<span class="v">' + pct(a.no_or_neither || 0) + '</span>';
      if (a.unknown > 0) noadmit += '<span class="sub">' + (a.unknown < 0.005 ? 'under 1%' : pct(a.unknown)) + ' unknown</span>';
    }
    var h = c.holdings || {};
    var hold = h.n ? '<span class="v">' + int0.format(h.n) + (h.n === 1 ? ' row' : ' rows') + '</span><span class="sub">' + int0.format(h.officials) +
      (h.officials === 1 ? ' official' : ' officials') + '</span>' : '<span class="v zero">none</span>';
    var tag = '';
    if (c.kind && c.kind !== 'company') tag = '<span class="tag">' + esc(c.kind) + '</span>';
    if (p.criminal) tag += '<span class="tag">criminal case</span>';
    return '<tr class="row' + (open ? ' open' : '') + '" data-id="' + esc(c.company_id) + '">' +
      '<td class="co"><button type="button" class="co-btn" aria-expanded="' + open + '" aria-controls="co-panel">' +
      '<span class="dot" aria-hidden="true"></span><span>' + esc(c.name) + '</span></button>' + tag + inclHtml(c, 'incl') + '</td>' +
      cell('pen', 'Penalties counted', pen) +
      cell('noadmit', 'Without admitting fault', noadmit) +
      cell('con', 'State payments, FY2010 on', val(c.contracts.total) + spark(c)) +
      cell('ocpf', 'Employee donations, state (OCPF)', val(c.donations.ocpf)) +
      cell('fec', 'Employee donations, federal (FEC)', val(c.donations.fec)) +
      cell('firm', 'Lobbying firm fees, 2010 on', val(c.lobbying.firm_fee)) +
      cell('inhouse', 'Lobbying in-house, 2025 on', val(c.lobbying.in_house)) +
      cell('hold', "Officials' disclosed ties", hold) + '</tr>';
  }

  function lensSummary(n) {
    var el = $('lens-sum');
    var L = LEDGER.lenses[state.lens];
    var txt = '';
    if (L) {
      txt = '<b>' + esc(LENS_NAME[state.lens][0].toUpperCase() + LENS_NAME[state.lens].slice(1)) + '</b>' +
        (state.lens === 'all' ? '' : ' lens') + ': <span class="mono">' + esc(money(L.counted)) + '</span> in penalties counted across ' +
        int0.format(L.n_companies) + ' companies and institutions (<span class="mono">' + esc(money(L.gross)) +
        '</span> gross; <a href="#overlaps">counted and gross</a>).';
      var joint = L.counted_before_joint_dedupe - L.counted;
      if (joint > 0) txt += ' The total counts once a payment shared by companies in a joint settlement, so it is <span class="mono">' +
        esc(money(joint)) + '</span> below the sum of the rows.';
    }
    var f = Object.keys(state.f).filter(function (k) { return state.f[k]; }).map(function (k) { return FILTER_NAME[k]; });
    if (state.kind !== 'all') f.unshift(state.kind === 'inst' ? 'institutions only' : 'companies only');
    if (state.cb) f.unshift(state.cb === 'none' ? 'in none of the four other records' : 'in exactly these records: ' + comboLabel(state.cb));
    if (state.q.trim()) f.unshift('name contains "' + state.q.trim() + '"');
    txt += ' Showing ' + int0.format(n) + (n === 1 ? ' row' : ' rows') + (f.length ? ' (' + esc(f.join('; ')) + ')' : '') + '.';
    el.innerHTML = txt;
  }

  var LIST = [];
  function render() {
    LIST = visible();
    headers();
    var tbody = $('rows');
    var ncol = COLS.filter(function (c) { return colOn(c.key); }).length;
    tbody.innerHTML = LIST.length ? LIST.slice(0, state.shown).map(rowHtml).join('') :
      '<tr><td colspan="' + ncol + '" class="empty">No company matches these filters under this lens. Clear the search or filters, or choose All.</td></tr>';
    var foot = $('tc-foot');
    var shown = Math.min(state.shown, LIST.length);
    foot.innerHTML = '<span>Showing ' + int0.format(shown) + ' of ' + int0.format(LIST.length) + '</span>' +
      (LIST.length > shown ? '<button type="button" class="more" id="t-more" style="margin:0">Show ' + Math.min(PAGE, LIST.length - shown) +
        ' more</button><button type="button" class="linkbtn" id="t-all">Show all ' + int0.format(LIST.length) + '</button>' : '');
    if ($('t-more')) $('t-more').addEventListener('click', function () { state.shown += PAGE; render(); });
    if ($('t-all')) $('t-all').addEventListener('click', function () { state.shown = LIST.length; render(); });
    document.querySelectorAll('#cols .sort').forEach(function (b) {
      if (b.dataset.key === state.sort) b.setAttribute('aria-sort', state.dir < 0 ? 'descending' : 'ascending');
      else b.removeAttribute('aria-sort');
    });
    $('sortsel').value = state.sort;
    document.querySelectorAll('#lens button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.lens === state.lens)); });
    document.querySelectorAll('#kind button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.kind === state.kind)); });
    document.querySelectorAll('#fchips .fchip').forEach(function (b) { b.setAttribute('aria-pressed', String(!!state.f[b.dataset.f])); });
    document.querySelectorAll('#colmenu-list input').forEach(function (i, k) {
      var keys = COLS.filter(function (c) { return !c.fixed; });
      i.checked = colOn(keys[k].key);
    });
    if ($('q').value !== state.q) $('q').value = state.q;
    cbBox();
    lensSummary(LIST.length);
    renderKpis();
    selChip();
    renderCharts();
    writeUrl();
    notifyLens();
  }

  // ---------- shared SVG helpers ----------
  var SVGNS = 'http://www.w3.org/2000/svg';
  function hatchDef(id, color) {
    return '<pattern id="' + id + '" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">' +
      '<rect width="4" height="4" fill="#fff"/><rect width="2" height="4" fill="' + color + '"/></pattern>';
  }
  var tipEl = null;
  function tip(html, ev) {
    tipEl = tipEl || $('tip');
    if (!html) { tipEl.hidden = true; return; }
    tipEl.innerHTML = html;
    tipEl.hidden = false;
    var x, y;
    if (ev && ev.clientX !== undefined && ev.type.indexOf('mouse') === 0) { x = ev.clientX; y = ev.clientY; }
    else { var r = ev.target.getBoundingClientRect(); x = r.left + r.width / 2; y = r.top; }
    var w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    var left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8);
    var top = y - h - 12 < 8 ? y + 18 : y - h - 12;
    tipEl.style.left = left + 'px';
    tipEl.style.top = top + 'px';
  }
  // Wire tooltip, click and keyboard for every .mk inside a container. data-k indexes into handlers.
  function wireMarks(box, handlers) {
    box.querySelectorAll('.mk').forEach(function (g) {
      var hd = handlers[g.getAttribute('data-k')];
      if (!hd) return;
      g.addEventListener('mouseenter', function (e) { tip(hd.tip, e); if (hd.enter) hd.enter(); });
      g.addEventListener('mousemove', function (e) { tip(hd.tip, e); });
      g.addEventListener('mouseleave', function () { tip(null); if (hd.leave) hd.leave(); });
      g.addEventListener('focus', function (e) { tip(hd.tip, e); if (hd.enter) hd.enter(); });
      g.addEventListener('blur', function () { tip(null); if (hd.leave) hd.leave(); });
      if (hd.click) {
        g.addEventListener('click', function () { tip(null); hd.click(); });
        g.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tip(null); hd.click(); }
        });
      }
    });
  }
  function textW(s, px) { return String(s).length * px * 0.56; }

  // Vertical bars by year, stacked or grouped, one y scale. series: [{key,label,color,hatch,get(year)}]
  function vbars(box, o) {
    var W = Math.max(240, box.clientWidth || 0), H = o.height, padL = 44, padR = 6, padT = 8, padB = 20;
    var years = o.years, n = years.length;
    var band = (W - padL - padR) / n;
    var max = 0;
    years.forEach(function (y) {
      if (o.mode === 'stack') {
        var s = 0; o.series.forEach(function (se) { s += Math.max(0, se.get(y) || 0); }); max = Math.max(max, s);
      } else o.series.forEach(function (se) { max = Math.max(max, se.get(y) || 0); });
    });
    if (!max) { box.innerHTML = '<p class="empty-plot">' + esc(o.empty) + '</p>'; return; }
    var step = niceMax(max / 3), nt = Math.ceil(max / step), nice = step * nt, plotH = H - padT - padB;
    var yv = function (v) { return padT + plotH - v / nice * plotH; };
    var defs = '', out = '', id = box.id;
    o.series.forEach(function (se) { if (se.hatch) defs += hatchDef(id + '-' + se.key, se.color); });
    for (var t = 0; t <= nt; t++) {
      var v = step * t, yy = yv(v);
      out += '<line class="' + (t ? 'grid-l' : 'base-l') + '" x1="' + padL + '" x2="' + (W - padR) + '" y1="' + yy + '" y2="' + yy + '"/>' +
        '<text class="ax" x="' + (padL - 5) + '" y="' + (yy + 3) + '" text-anchor="end">' + esc(axisMoney(v)) + '</text>';
    }
    var every = band < 22 ? (band < 12 ? 3 : 2) : 1;
    var handlers = {};
    years.forEach(function (y, i) {
      var x0 = padL + i * band;
      var bw = o.mode === 'stack' ? Math.min(30, band - 3) : Math.min(14, (band - 4) / o.series.length);
      var gx = x0 + (band - (o.mode === 'stack' ? bw : bw * o.series.length + (o.series.length - 1))) / 2;
      var g = '<g class="mk" data-k="' + i + '" tabindex="0" role="' + (o.click ? 'button' : 'img') + '" aria-label="' + esc(o.aria(y)) + '">' +
        '<rect class="hit" x="' + x0 + '" y="' + padT + '" width="' + band + '" height="' + plotH + '"/>';
      var acc = 0;
      o.series.forEach(function (se, k) {
        var v = Math.max(0, se.get(y) || 0);
        if (!v) return;
        var fill = se.hatch ? 'url(#' + id + '-' + se.key + ')' : se.color;
        if (o.mode === 'stack') {
          var y1 = yv(acc), y2 = yv(acc + v);
          var hgt = Math.max(1, y1 - y2);
          g += '<rect x="' + gx + '" y="' + (y1 - hgt) + '" width="' + bw + '" height="' + hgt + '" fill="' + fill + '" stroke="' + (se.hatch ? se.color : C.surface) + '" stroke-width="1"/>';
          acc += v;
        } else {
          var yy2 = yv(v), hh = Math.max(1, padT + plotH - yy2);
          g += '<rect x="' + (gx + k * (bw + 1)) + '" y="' + (padT + plotH - hh) + '" width="' + bw + '" height="' + hh + '" rx="1" fill="' + fill + '"' +
            (se.hatch ? ' stroke="' + se.color + '" stroke-width="1"' : '') + '/>';
        }
      });
      g += '</g>';
      out += g;
      if (i % every === 0) out += '<text class="ax" x="' + (x0 + band / 2) + '" y="' + (H - 6) + '" text-anchor="middle">' + esc(o.xlab(y)) + '</text>';
      handlers[i] = { tip: o.tip(y), click: o.click ? function () { o.click(y); } : null };
    });
    box.innerHTML = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(o.label) + '">' +
      (defs ? '<defs>' + defs + '</defs>' : '') + out + '</svg>' + dataTable(o);
    wireMarks(box, handlers);
  }
  function niceMax(v) {
    var p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p;
    var s = m <= 1 ? 1 : m <= 1.5 ? 1.5 : m <= 2 ? 2 : m <= 3 ? 3 : m <= 4 ? 4 : m <= 5 ? 5 : m <= 6 ? 6 : m <= 8 ? 8 : 10;
    return s * p;
  }
  function dataTable(o) {
    var h = '<details class="dt"><summary>Data table</summary><div class="tscroll"><table class="mini"><thead><tr><th>' + esc(o.xname) + '</th>';
    o.series.forEach(function (se) { h += '<th>' + esc(se.label) + '</th>'; });
    h += '</tr></thead><tbody>';
    o.years.forEach(function (y) {
      h += '<tr><td>' + esc(o.xfull(y)) + '</td>';
      o.series.forEach(function (se) { h += '<td>' + esc(money(se.get(y) || 0)) + '</td>'; });
      h += '</tr>';
    });
    return h + '</tbody></table></div></details>';
  }
  function legend(box, items) {
    box.innerHTML = items.map(function (it) {
      return '<span class="lg"><span class="lg-sw' + (it.hatch ? ' hatch' : '') + '" style="--c:' + it.color + '"></span>' + esc(it.label) + '</span>';
    }).join('');
  }

  // ---------- charts ----------
  function scopeSet() { return state.sel && BYID[state.sel] ? [BYID[state.sel]] : LIST; }
  function scopeHtml(which) {
    var co = state.sel && BYID[state.sel];
    if (co) {
      return '<span class="nm" title="' + esc(co.name) + '">' + esc(co.name) + (which === 'top' ? ', highlighted' : '') + '</span>' +
        '<button type="button" data-clear="1" aria-label="Clear the selected company">&#215;</button>';
    }
    return anyFilter() ? 'Filtered: ' + int0.format(LIST.length) + ' companies' : 'All companies';
  }
  function scopes() {
    var co = state.sel && BYID[state.sel];
    document.querySelectorAll('[data-scope]').forEach(function (s) {
      s.className = 'scope' + (co ? ' co' : '');
      s.innerHTML = scopeHtml(s.getAttribute('data-scope'));
    });
  }
  // The "In exactly these records" chip, shown while the How it connects filter is on.
  function cbBox() {
    var box = $('cb-box');
    if (!box) return;
    box.hidden = !state.cb;
    if (state.cb) $('cb-nm').textContent = comboLabel(state.cb);
  }
  function selChip() {
    var c = state.sel && BYID[state.sel], el = $('selchip');
    if (c) {
      el.className = 'selchip';
      el.innerHTML = '<span class="nm" title="' + esc(c.name) + '">' + esc(trimTo(c.name, 34)) + '</span><button type="button" data-clear="1" aria-label="Clear the selected company">&#215;</button>';
    } else { el.className = 'selchip all'; el.textContent = 'All companies'; }
  }

  function renderCharts() {
    if (!LEDGER || currentTabName() !== 'ledger') return;
    scopes();
    drawTop();
    drawPay();
    drawDon();
    drawLob();
  }

  function drawTop() {
    var box = $('p-top');
    var list = LIST.filter(function (c) { return penFor(c) > 0; }).sort(function (a, b) { return penFor(b) - penFor(a); });
    var top = list.slice(0, 15);
    var sub = $('ch-top-sub');
    var rank = -1;
    if (state.sel) list.forEach(function (c, i) { if (c.company_id === state.sel) rank = i; });
    sub.textContent = 'Counted under the ' + (state.lens === 'all' ? 'all-lenses total' : LENS_NAME[state.lens] + ' lens') + '. Select a bar to open that company below.' +
      (state.sel && rank >= 15 ? ' The selected company ranks ' + (rank + 1) + ' of ' + list.length + '.' : '') +
      (state.sel && rank < 0 && BYID[state.sel] ? ' The selected company has no counted penalty in this view.' : '');
    if (!top.length) { box.innerHTML = '<p class="empty-plot">No company with a counted penalty matches these filters.</p>'; return; }
    // Beside the other charts (desktop) the card is two rows tall, so the bars take the height; stacked, they stay compact.
    var card = box.closest('.chart-card'), grid = $('charts');
    var beside = card && grid && card.getBoundingClientRect().width < grid.getBoundingClientRect().width * 0.6;
    var W = Math.max(260, box.clientWidth || 0), rowH = beside ? 29 : 23, padT = 2;
    var labW = Math.min(190, Math.round(W * 0.44)), valW = 52, x0 = labW + 8, maxW = W - x0 - valW;
    var max = penFor(top[0]);
    var H = padT + top.length * rowH + 4;
    var chars = Math.floor(labW / 6.1), bh = Math.min(17, rowH - 9);
    var out = '', handlers = {};
    top.forEach(function (c, i) {
      var v = penFor(c), y = padT + i * rowH, bw = Math.max(2, v / max * maxW), sel = c.company_id === state.sel;
      out += '<g class="mk' + (sel ? ' sel' : '') + '" data-k="' + i + '" data-id="' + esc(c.company_id) + '" tabindex="0" role="button" aria-label="' +
        esc(c.name + ', ' + money(v) + ' counted. Open this company') + '">' +
        '<rect class="hit" x="0" y="' + y + '" width="' + W + '" height="' + rowH + '" rx="4"/>' +
        '<text class="lab" x="' + labW + '" y="' + (y + rowH / 2 + 4) + '" text-anchor="end">' + esc(trimTo(c.name, chars)) + '</text>' +
        '<rect x="' + x0 + '" y="' + (y + (rowH - bh) / 2) + '" width="' + bw + '" height="' + bh + '" rx="2" fill="' + C.penalty + '"' +
        (sel ? ' stroke="' + cssv('--text') + '" stroke-width="1.5"' : '') + '/>' +
        '<text class="val" x="' + (x0 + bw + 5) + '" y="' + (y + rowH / 2 + 4) + '">' + esc(money(v)) + '</text></g>';
      handlers[i] = {
        tip: '<b>' + esc(c.name) + '</b><br>' + esc(money(v)) + ' counted' + (c.penalties.gross !== c.penalties.counted ? ', gross ' + esc(money(c.penalties.gross)) + ' (all lenses)' : '') +
          '<br>' + int0.format(c.penalties.n_cases) + ' penalty rows' + (c.penalties.criminal ? ', ' + c.penalties.criminal + ' criminal' : '') +
          '<span class="t-src">Source: corporate ledger table; select to list each release</span>',
        click: function () { select(c.company_id, true); },
        enter: function () { hlRow(c.company_id, true); },
        leave: function () { hlRow(c.company_id, false); }
      };
    });
    box.innerHTML = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="Top 15 companies by counted penalties">' +
      '<line class="base-l" x1="' + x0 + '" x2="' + x0 + '" y1="' + padT + '" y2="' + (H - 2) + '"/>' + out + '</svg>';
    wireMarks(box, handlers);
  }
  function hlRow(id, on) {
    var tr = document.querySelector('tr.row[data-id="' + cssEsc(id) + '"]');
    if (tr) tr.classList.toggle('hl', on);
  }
  function hlBar(id, on) {
    var g = document.querySelector('#p-top .mk[data-id="' + cssEsc(id) + '"]');
    if (g) g.classList.toggle('hl', on);
  }

  function chartHeight(box, dflt) {
    var w = box.clientWidth || 600;
    return w < 420 ? Math.max(150, dflt - 20) : dflt;
  }
  function yearRange(a, b) { var r = []; for (var y = a; y <= b; y++) r.push(y); return r; }
  function setName() { var co = state.sel && BYID[state.sel]; return co ? co.name : (anyFilter() ? 'the filtered companies' : 'all companies'); }

  function drawPay() {
    var box = $('p-pay');
    var lg = $('lg-pay');
    legend(lg, PAYERS.map(function (p) { return { label: PAYER_NAME[p], color: C.pay[p] }; }));
    if (!GD) { box.innerHTML = '<p class="empty-plot">Loading the payment records</p>'; return; }
    var by = {};
    scopeSet().forEach(function (c) {
      var m = GD.pay[c.company_id] || {};
      Object.keys(m).forEach(function (y) {
        by[y] = by[y] || {};
        Object.keys(m[y]).forEach(function (p) { by[y][p] = (by[y][p] || 0) + m[y][p]; });
      });
    });
    var years = yearRange(FY0, FY1);
    var who = setName();
    vbars(box, {
      height: chartHeight(box, 176), years: years, mode: 'stack', label: 'State payments by fiscal year for ' + who,
      empty: 'No state payment on record for ' + who + '.',
      series: PAYERS.map(function (p) { return { key: p, label: PAYER_NAME[p], color: C.pay[p], get: function (y) { return (by[y] || {})[p] || 0; } }; }),
      xlab: function (y) { return 'FY' + String(y).slice(2); }, xfull: function (y) { return 'FY' + y; }, xname: 'Fiscal year',
      aria: function (y) { return 'FY' + y + ': ' + money(sumObj(by[y])); },
      tip: function (y) {
        var b = by[y] || {}, t = '<b>FY' + y + (y === FY1 ? ' (partial)' : '') + '</b>, ' + esc(who);
        PAYERS.forEach(function (p) { if (b[p]) t += '<br>' + esc(PAYER_NAME[p]) + ': ' + esc(money(b[p])); });
        t += '<br>All payers: ' + esc(money(sumObj(b)));
        t += '<span class="t-src">Source: ' + esc(PAYERS.filter(function (p) { return b[p]; }).join(', ') || 'no payment') + ' payment records' +
          (state.sel ? '; select to list them' : '') + '</span>';
        return t;
      },
      click: state.sel ? function (y) { openRecords('contract', y); } : null
    });
  }
  function sumObj(o) { var s = 0; for (var k in (o || {})) s += o[k]; return s; }

  function drawDon() {
    var box = $('p-don');
    legend($('lg-don'), [{ label: 'State (OCPF)', color: C.donation }, { label: 'Federal (FEC)', color: C.donationFed, hatch: true }]);
    if (!GD) { box.innerHTML = '<p class="empty-plot">Loading the donation records</p>'; return; }
    var by = {};
    scopeSet().forEach(function (c) {
      var m = GD.don[c.company_id] || {};
      Object.keys(m).forEach(function (y) {
        by[y] = by[y] || { s: 0, f: 0 };
        by[y].s += m[y].s; by[y].f += m[y].f;
      });
    });
    var who = setName();
    var years = yearRange(2009, GD.donLast);
    vbars(box, {
      height: chartHeight(box, 150), years: years, mode: 'group', label: 'Confirmed donations by year for ' + who,
      empty: 'No confirmed donation on record for ' + who + '.',
      series: [
        { key: 's', label: 'State (OCPF)', color: C.donation, get: function (y) { return (by[y] || {}).s || 0; } },
        { key: 'f', label: 'Federal (FEC)', color: C.donationFed, hatch: true, get: function (y) { return (by[y] || {}).f || 0; } }
      ],
      xlab: function (y) { return "'" + String(y).slice(2); }, xfull: function (y) { return y === 2009 ? '2009 (July to December)' : String(y); }, xname: 'Year',
      aria: function (y) { var b = by[y] || {}; return y + ': state ' + money(b.s || 0) + ', federal ' + money(b.f || 0); },
      tip: function (y) {
        var b = by[y] || { s: 0, f: 0 };
        return '<b>' + (y === 2009 ? '2009, July to December' : y) + '</b>, ' + esc(who) + '<br>State (OCPF): ' + esc(money(b.s)) +
          '<br>Federal (FEC): ' + esc(money(b.f)) + '<br>Kept apart; never added together.' +
          '<span class="t-src">Source: OCPF and FEC contribution files' + (state.sel ? '; select to list the gifts' : '') + '</span>';
      },
      click: state.sel ? function (y) { openRecords('donation', y); } : null
    });
  }

  function drawLob() {
    var box = $('p-lob');
    legend($('lg-lob'), [{ label: 'Firm fees', color: C.lobbying }, { label: 'In-house', color: C.lobbyingIn, hatch: true }]);
    var by = {};
    scopeSet().forEach(function (c) {
      var m = c.lobbying.by_year || {};
      Object.keys(m).forEach(function (y) {
        by[y] = by[y] || { f: 0, i: 0 };
        by[y].f += m[y].firm_fee || 0; by[y].i += m[y].in_house || 0;
      });
    });
    var who = setName();
    var last = +String((LEDGER.coverage.lobbying || {}).to || 2026);
    vbars(box, {
      height: chartHeight(box, 150), years: yearRange(2010, last), mode: 'stack', label: 'Lobbying by year for ' + who,
      empty: 'No lobbying on record for ' + who + ' (firm fees from 2010, in-house from 2025).',
      series: [
        { key: 'f', label: 'Firm fees', color: C.lobbying, get: function (y) { return (by[y] || {}).f || 0; } },
        { key: 'i', label: 'In-house', color: C.lobbyingIn, hatch: true, get: function (y) { return (by[y] || {}).i || 0; } }
      ],
      xlab: function (y) { return "'" + String(y).slice(2); }, xfull: function (y) { return String(y); }, xname: 'Year',
      aria: function (y) { var b = by[y] || {}; return y + ': firm fees ' + money(b.f || 0) + ', in-house ' + money(b.i || 0); },
      tip: function (y) {
        var b = by[y] || { f: 0, i: 0 };
        return '<b>' + y + (y === last ? ' (partial)' : '') + '</b>, ' + esc(who) + '<br>Firm fees: ' + esc(money(b.f)) + '<br>In-house: ' + esc(money(b.i)) +
          '<br>Together: ' + esc(money(b.f + b.i)) +
          '<span class="t-src">Source: Secretary of the Commonwealth lobbying disclosures' + (state.sel ? '; select to list them' : '') + '</span>';
      },
      click: state.sel ? function (y) { openRecords('lobbying', y); } : null
    });
  }

  // ---------- company panel ----------
  function select(id, scroll) {
    if (!BYID[id]) return;
    state.sel = id; state.rf = null; state.ry = null;
    render();
    panel(scroll);
  }
  function clearSel() {
    state.sel = null; state.rf = null; state.ry = null;
    render();
    panel(false);
  }
  function examples() {
    var top = LIST.filter(function (c) { return penFor(c) > 0; }).sort(function (a, b) { return penFor(b) - penFor(a); }).slice(0, 3);
    var box = $('cp-examples');
    if (!box) return;
    box.innerHTML = top.map(function (c) {
      return '<button type="button" class="fchip" data-pick="' + esc(c.company_id) + '">' + esc(trimTo(c.name, 40)) + '</button>';
    }).join(' ');
  }
  function panel(scroll) {
    var body = $('cp-body');
    var co = state.sel && BYID[state.sel];
    if (!co) {
      body.innerHTML = '<div class="cp-empty"><span>Select a company (a bar above or a row below) to see its penalties, state payments, donations, lobbying and disclosed ties on one timeline, with every record and its source. For example:</span><span id="cp-examples"></span></div>';
      examples();
      return;
    }
    var p = co.penalties;
    body.innerHTML = '<div class="cp-head"><div><h2 id="cp-title">' + esc(co.name) + '</h2>' +
      (co.kind && co.kind !== 'company' ? '<span class="tag">' + esc(co.kind) + '</span> ' : '') +
      '<div class="cp-facts">' +
        '<span><span class="cdot" style="--c:var(--s-penalty)"></span>Counted <b>' + esc(money(penFor(co))) + '</b> (' + esc(LENS_NAME[state.lens]) + '), gross <b>' + esc(money(p.gross)) + '</b></span>' +
        '<span><span class="cdot" style="--c:var(--s-contract)"></span>State payments <b>' + esc(money(co.contracts.total || 0)) + '</b></span>' +
        '<span><span class="cdot" style="--c:var(--s-donation)"></span>Employee donations, state <b>' + esc(money(co.donations.ocpf || 0)) + '</b></span>' +
        '<span><span class="cdot hatch" style="--c:var(--s-donation-fed)"></span>Employee donations, federal <b>' + esc(money(co.donations.fec || 0)) + '</b></span>' +
        '<span><span class="cdot" style="--c:var(--s-lobbying)"></span>Lobbying <b>' + esc(money((co.lobbying.firm_fee || 0) + (co.lobbying.in_house || 0))) + '</b></span>' +
        '<span><span class="cdot" style="--c:var(--s-holding)"></span>Disclosed ties <b>' + int0.format(co.holdings.n || 0) + '</b></span>' +
      '</div></div><div class="cp-actions"><a class="more" href="?tab=cases&case=' + encodeURIComponent(co.company_id) + '" style="margin:0;text-decoration:none">Open the data profile</a> ' +
        '<button type="button" class="more" data-clear="1" style="margin:0">Clear selection</button></div></div>' +
      '<figure class="chart-card tline" id="ch-tl"><div class="ch-head"><h3>All five streams by year: ' + esc(co.name) + '</h3>' +
        '<span class="scope co"><span class="nm">' + esc(co.name) + '</span><button type="button" data-clear="1" aria-label="Clear the selected company">&#215;</button></span></div>' +
        '<div class="legend" id="lg-tl"></div><div class="plot" id="p-tl"><p class="empty-plot">Loading records</p></div>' +
        '<p class="source">Source: company records file (data/companies/' + esc(co.company_id) + '.json): agency penalty releases, CTHRU, MBTA, Massport and MSBA payment records, OCPF and FEC contribution files, Secretary of the Commonwealth lobbying disclosures and officials\' Statements of Financial Interest. Each mark names its sources; select it to list the records with links.</p></figure>' +
      '<div class="tl" id="cp-records" data-tl="' + esc(co.company_id) + '">Loading records</div>';
    legend($('lg-tl'), [
      { label: 'Penalty rows (gross, sized by amount)', color: C.penalty },
      { label: 'State payments (fiscal years, July to June)', color: C.contract },
      { label: 'Employee donations, state', color: C.donation },
      { label: 'Employee donations, federal', color: C.donationFed, hatch: true },
      { label: 'Lobbying firm fees', color: C.lobbying },
      { label: 'Lobbying in-house', color: C.lobbyingIn, hatch: true },
      { label: 'Disclosed ties (filings that year)', color: C.holding }
    ]);
    if (scroll) scrollToEl($('co-panel'), true);
    var id = co.company_id;
    loadCompany(id).then(function (d) {
      if (state.sel !== id) return;
      drawTimeline(d);
      drawRecords(d, $('cp-records'));
      document.documentElement.dataset.panelReady = id;
    }).catch(function () {
      var b = $('cp-records');
      if (b) b.textContent = 'The records for this company could not be loaded (data/companies/' + id + '.json). Reload the page to try again.';
      var t = $('p-tl'); if (t) t.innerHTML = '';
    });
  }
  function loadCompany(id) {
    if (!cache[id]) cache[id] = fetch('data/corporate-ledger/companies/' + encodeURIComponent(id) + '.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
    cache[id].catch(function () { delete cache[id]; });
    return cache[id];
  }

  // The year a record belongs to: fiscal year for state payments (from the label), calendar year for the rest.
  function itemYear(it) {
    if (it.stream === 'contract') {
      var m = /\(FY(\d{4}),/.exec(it.label || '');
      if (m) return +m[1];
      var d = new Date(it.date + 'T00:00:00');
      return d.getMonth() >= 6 ? d.getFullYear() + 1 : d.getFullYear();
    }
    return +String(it.date).slice(0, 4);
  }
  function itemPayer(it) { var m = /, ([A-Z]+)\)$/.exec(it.label || ''); return m ? m[1] : ''; }
  function isFed(it) { return /^FEC/.test(it.detail || ''); }
  function lobKind(it) { return /^in_house/.test(it.detail || '') ? 'i' : 'f'; }
  function frac(date) {
    var d = new Date(date + 'T00:00:00'), y = d.getFullYear();
    var start = Date.UTC(y, 0, 1), end = Date.UTC(y + 1, 0, 1);
    return y + (Date.UTC(y, d.getMonth(), d.getDate()) - start) / (end - start);
  }
  function hostsOf(items) {
    var h = {};
    items.forEach(function (it) { var u = safeUrl(it.source_url); if (u) h[host(u)] = (h[host(u)] || 0) + 1; });
    var k = Object.keys(h).sort(function (a, b) { return h[b] - h[a]; });
    return k.length ? k.slice(0, 3).join(', ') + (k.length > 3 ? ' and ' + (k.length - 3) + ' more' : '') : 'no source link';
  }

  // The lane's scale, written out: the largest single row (penalties), year (money lanes) or count (ties).
  function laneMax(k, list) {
    if (!list.length) return '';
    if (k === 'penalty') return 'largest row ' + axisMoney(Math.max.apply(null, list.map(function (it) { return it.amount || 0; })));
    var agg = {};
    list.forEach(function (it) {
      var y = itemYear(it), a = agg[y] = agg[y] || { t: 0, s: 0, f: 0, n: 0 };
      a.n++; a.t += it.amount || 0;
      if (k === 'donation') { if (isFed(it)) a.f += it.amount || 0; else a.s += it.amount || 0; }
    });
    var mx = 0;
    Object.keys(agg).forEach(function (y) {
      var a = agg[y];
      mx = Math.max(mx, k === 'donation' ? Math.max(a.s, a.f) : k === 'holding' ? a.n : a.t);
    });
    return k === 'holding' ? 'most in a year: ' + mx : 'tallest bar ' + axisMoney(mx);
  }

  // Combined timeline: one shared year axis, one lane per stream, each lane on its own scale (small multiples,
  // never a second axis on one plot). Penalties are every row on record (gross), sized by amount.
  function drawTimeline(d) {
    var box = $('p-tl');
    if (!box) return;
    var items = (d.items || []).filter(function (it) { return it.match_tier === 'confirmed' || it.stream === 'penalty'; });
    var X0 = 2009.5, X1 = FY1 + 0.5;
    var W = Math.max(300, box.clientWidth || 0), narrow = W < 640;
    var gut = narrow ? 8 : 168, padR = 12, laneH = 44, labH = narrow ? 16 : 0, gapL = 8;
    var lanes = [
      { k: 'penalty', name: 'Penalties', note: 'rows on record, gross' },
      { k: 'contract', name: 'State payments', note: 'by fiscal year' },
      { k: 'donation', name: 'Employee donations', note: 'state solid, federal hatched' },
      { k: 'lobbying', name: 'Lobbying', note: 'firm fees and in-house' },
      { k: 'holding', name: 'Disclosed ties', note: 'filings per year' }
    ];
    var xs = function (v) { return gut + (v - X0) / (X1 - X0) * (W - gut - padR); };
    var byS = {};
    items.forEach(function (it) { (byS[it.stream] = byS[it.stream] || []).push(it); });
    var defs = hatchDef('tl-fed', C.donationFed) + hatchDef('tl-inh', C.lobbyingIn);
    var out = '', handlers = {}, hk = 0, y = 4;
    var nameOf = (d.company || {}).name || '';
    function mark(inner, aria, tipHtml, stream, year) {
      var k = 'm' + (hk++);
      handlers[k] = { tip: tipHtml, click: function () { openRecords(stream, year); } };
      return '<g class="mk" data-k="' + k + '" tabindex="0" role="button" aria-label="' + esc(aria) + '">' + inner + '</g>';
    }
    lanes.forEach(function (ln) {
      var top = y + labH, base = top + laneH, list = byS[ln.k] || [];
      out += '<line class="grid-l" x1="' + gut + '" x2="' + (W - padR) + '" y1="' + base + '" y2="' + base + '"/>';
      var maxNote = laneMax(ln.k, list);
      if (narrow) out += '<text class="lab" x="' + gut + '" y="' + (y + 11) + '" style="font-weight:600">' + esc(ln.name) + '</text>' +
        '<text class="note-t" x="' + (gut + textW(ln.name, 11.5) + 8) + '" y="' + (y + 11) + '">' + esc(ln.note + (maxNote ? '; ' + maxNote : '')) + '</text>';
      else out += '<text class="lab" x="0" y="' + (top + 13) + '" style="font-weight:600">' + esc(ln.name) + '</text>' +
        '<text class="note-t" x="0" y="' + (top + 26) + '">' + esc(ln.note) + '</text>' +
        (maxNote ? '<text class="note-t" x="0" y="' + (top + 39) + '">' + esc(maxNote) + '</text>' : '');
      if (!list.length) {
        out += '<text class="ax" x="' + (gut + 4) + '" y="' + (base - 6) + '">none on record</text>';
      } else if (ln.k === 'penalty') {
        var maxA = Math.max.apply(null, list.map(function (it) { return it.amount || 0; })) || 1;
        list.slice().sort(function (a, b) { return (b.amount || 0) - (a.amount || 0); }).forEach(function (it) {
          var r = 3 + 11 * Math.sqrt((it.amount || 0) / maxA), cx = xs(Math.max(X0, frac(it.date))), cy = top + laneH / 2;
          var u = safeUrl(it.source_url);
          out += mark('<circle class="hit" cx="' + cx + '" cy="' + cy + '" r="' + Math.max(r + 3, 9) + '"/>' +
            '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="' + C.penalty + '" fill-opacity=".82" stroke="' + C.surface + '" stroke-width="1.5"/>',
            it.date + ', ' + it.label + ', ' + money(it.amount),
            '<b>' + esc(it.date) + '</b>: ' + esc(trimTo(it.label, 90)) + '<br>' + esc(money(it.amount)) + ' on record' +
              '<span class="t-src">Source: ' + esc(u ? host(u) : 'no source link') + '</span>', 'penalty', itemYear(it));
        });
      } else {
        var agg = {};
        list.forEach(function (it) {
          var yr = itemYear(it), a = agg[yr] = agg[yr] || { t: 0, s: 0, f: 0, i: 0, n: 0, items: [], pay: {} };
          var amt = it.amount || 0;
          a.n++; a.items.push(it); a.t += amt;
          if (ln.k === 'donation') { if (isFed(it)) a.f += amt; else a.s += amt; }
          if (ln.k === 'lobbying') { if (lobKind(it) === 'i') a.i += amt; else a.f += amt; }
          if (ln.k === 'contract') { var p = itemPayer(it); a.pay[p] = (a.pay[p] || 0) + amt; }
        });
        var yrs = Object.keys(agg).map(Number);
        var mx = 0;
        yrs.forEach(function (yr) {
          var a = agg[yr];
          mx = Math.max(mx, ln.k === 'donation' ? Math.max(a.s, a.f) : ln.k === 'holding' ? a.n : Math.max(0, a.t));
        });
        mx = mx || 1;
        yrs.forEach(function (yr) {
          var a = agg[yr], aria, tp, inner = '';
          var srcs = '<span class="t-src">Source: ' + esc(hostsOf(a.items)) + ' (' + a.n + (a.n === 1 ? ' record' : ' records') + ')</span>';
          var bx0, bx1;
          if (ln.k === 'contract') { bx0 = xs(yr - 0.5) + 1; bx1 = xs(yr + 0.5) - 1; }
          else { bx0 = xs(Math.max(X0, yr)) + 1; bx1 = xs(Math.min(X1, yr + 1)) - 1; }
          var bw = Math.max(2, bx1 - bx0), hmax = laneH - 12;
          inner += '<rect class="hit" x="' + bx0 + '" y="' + top + '" width="' + bw + '" height="' + laneH + '"/>';
          if (ln.k === 'contract') {
            var h = Math.max(1, Math.max(0, a.t) / mx * hmax);
            inner += '<rect x="' + bx0 + '" y="' + (base - h) + '" width="' + bw + '" height="' + h + '" fill="' + C.contract + '"/>';
            aria = 'FY' + yr + ' state payments ' + money(a.t);
            tp = '<b>FY' + yr + '</b> state payments: ' + esc(money(a.t)) + Object.keys(a.pay).map(function (p) { return '<br>' + esc(PAYER_NAME[p] || p) + ': ' + esc(money(a.pay[p])); }).join('');
          } else if (ln.k === 'donation') {
            var half = Math.max(1, bw / 2 - 1);
            var hs = a.s ? Math.max(1, a.s / mx * hmax) : 0, hf = a.f ? Math.max(1, a.f / mx * hmax) : 0;
            if (hs) inner += '<rect x="' + bx0 + '" y="' + (base - hs) + '" width="' + half + '" height="' + hs + '" fill="' + C.donation + '"/>';
            if (hf) inner += '<rect x="' + (bx0 + half + 2) + '" y="' + (base - hf) + '" width="' + half + '" height="' + hf + '" fill="url(#tl-fed)" stroke="' + C.donationFed + '" stroke-width="1"/>';
            aria = yr + ' donations: state ' + money(a.s) + ', federal ' + money(a.f);
            tp = '<b>' + (yr === 2009 ? '2009, July to December' : yr) + '</b> donations<br>State (OCPF): ' + esc(money(a.s)) + '<br>Federal (FEC): ' + esc(money(a.f)) + '<br>Kept apart; never added together.';
          } else if (ln.k === 'lobbying') {
            var h1 = a.f ? Math.max(1, a.f / mx * hmax) : 0, h2 = a.i ? Math.max(1, a.i / mx * hmax) : 0;
            if (h1) inner += '<rect x="' + bx0 + '" y="' + (base - h1) + '" width="' + bw + '" height="' + h1 + '" fill="' + C.lobbying + '" stroke="' + C.surface + '" stroke-width="1"/>';
            if (h2) inner += '<rect x="' + bx0 + '" y="' + (base - h1 - h2) + '" width="' + bw + '" height="' + h2 + '" fill="url(#tl-inh)" stroke="' + C.lobbyingIn + '" stroke-width="1"/>';
            aria = yr + ' lobbying ' + money(a.t);
            tp = '<b>' + yr + '</b> lobbying: ' + esc(money(a.t)) + '<br>Firm fees: ' + esc(money(a.f)) + '<br>In-house: ' + esc(money(a.i));
          } else {
            var r2 = 3 + 6 * Math.sqrt(a.n / mx), cx2 = (bx0 + bx1) / 2, cy2 = top + laneH / 2 + 2;
            inner += '<circle cx="' + cx2 + '" cy="' + cy2 + '" r="' + r2 + '" fill="' + C.holding + '" stroke="' + C.surface + '" stroke-width="1.5"/>' +
              (bw > 22 ? '<text class="val" x="' + cx2 + '" y="' + (top + 9) + '" text-anchor="middle">' + a.n + '</text>' : '');
            aria = yr + ': ' + a.n + ' disclosed ties';
            tp = '<b>' + yr + '</b>: ' + a.n + (a.n === 1 ? ' disclosure row names ' : ' disclosure rows name ') + esc(trimTo(nameOf, 40));
          }
          out += mark(inner, aria + '. List these records', tp + srcs + '<span class="t-src">Select to list them with links</span>', ln.k, yr);
        });
      }
      y = base + gapL;
    });
    var axisY = y + 2;
    for (var yr = 2010; yr <= FY1; yr++) {
      var xx = xs(yr);
      out += '<line class="grid-l" x1="' + xx + '" x2="' + xx + '" y1="4" y2="' + (axisY - 4) + '" stroke-dasharray="1 3"/>';
      if (!narrow || yr % 2 === 0) out += '<text class="ax" x="' + xx + '" y="' + (axisY + 9) + '" text-anchor="middle">' + (narrow ? "'" + String(yr).slice(2) : yr) + '</text>';
    }
    var H = axisY + 14;
    box.innerHTML = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="Timeline of all five streams for ' + esc(nameOf) + '">' +
      '<defs>' + defs + '</defs>' + out + '</svg>' +
      '<p class="ch-sub" style="margin-top:4px">Each lane has its own scale. Penalty circles are every penalty row on record (gross, before overlaps are removed), sized by amount; the list marks rows another agency\'s row restates. State payments are fiscal years, drawn across the July to June span. Probable matches are left out of the bars and shown in the list.</p>';
    wireMarks(box, handlers);
  }

  function openRecords(stream, year) {
    state.rf = stream; state.ry = year || null;
    var box = $('cp-records');
    writeUrl();
    if (!box || !state.sel) return;
    loadCompany(state.sel).then(function (d) {
      box.dataset.shown = REC_PAGE;
      drawRecords(d, box);
      scrollToEl(box);
      var h = box.querySelector('h3');
      if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
    });
  }

  function itemAmount(it) {
    if (it.stream === 'holding') return 'disclosed';
    return money(it.amount);
  }

  function evHtml(it, canon) {
    var u = safeUrl(it.source_url);
    var mn = matchedName(it);
    var mchip = mn && differs(mn, canon) ? ' <span class="mchip">matched as: ' + esc(mn) + '</span>' : '';
    var tier = it.match_tier && it.match_tier !== 'confirmed' ? ' <span class="tag" style="margin:0">' + esc(it.match_tier) + ' match</span>' : '';
    return '<li class="ev s-' + esc(it.stream) + '">' +
      '<time class="mono" datetime="' + esc(it.date) + '">' + esc(it.date) + '</time>' +
      '<span class="chip"><span class="sw" aria-hidden="true"></span>' + esc(STREAM_LABEL[it.stream] || it.stream) + '</span>' +
      '<span class="amt">' + esc(itemAmount(it)) + '</span>' +
      '<span class="what"><b>' + esc(it.label) + '</b>' + tier + mchip + (it.detail ? '<span class="det">' + esc(it.detail) + '</span>' : '') + '</span>' +
      (u ? '<a class="src" href="' + esc(u) + '" target="_blank" rel="noopener">Source: ' + esc(host(u)) + '</a>' : '<span class="src muted">no source link</span>') +
      '</li>';
  }

  // Records for one company: per-stream tabs, an optional year filter set from the charts, the not-counted box,
  // the record list with sources, and the proximity table.
  function drawRecords(d, box) {
    var items = (d.items || []).slice().sort(function (a, b) {
      return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
    });
    var counts = {};
    items.forEach(function (it) { counts[it.stream] = (counts[it.stream] || 0) + 1; });
    var filter = state.rf || ((counts.donation || 0) > 50 ? 'nodon' : 'all');
    if (filter !== 'all' && filter !== 'nodon' && !counts[filter]) filter = 'all';
    var shown = +(box.dataset.shown || REC_PAGE);
    var list = filter === 'all' ? items : items.filter(function (it) {
      return filter === 'nodon' ? it.stream !== 'donation' : it.stream === filter;
    });
    if (state.ry) list = list.filter(function (it) { return itemYear(it) === state.ry; });

    var chips = '<button type="button" data-f="all" aria-pressed="' + (filter === 'all') + '">all ' + int0.format(items.length) + '</button>';
    if (counts.donation && counts.donation < items.length) {
      chips += '<button type="button" data-f="nodon" aria-pressed="' + (filter === 'nodon') + '">all but donations ' +
        int0.format(items.length - counts.donation) + '</button>';
    }
    STREAMS.forEach(function (s) {
      if (!counts[s[0]]) return;
      chips += '<button type="button" class="s-' + s[0] + '" data-f="' + s[0] + '" aria-pressed="' + (filter === s[0]) + '">' +
        '<span class="sw" aria-hidden="true"></span>' + esc(s[1]) + ' ' + int0.format(counts[s[0]]) + '</button>';
    });

    var co = d.company || {};
    var incl = co.entities && co.entities.length > 1 ? '<p class="note incl-note"><b>Includes:</b> ' + esc(co.entities.join('; ')) + '. ' +
      esc(co.entities_note || '') + ' A "matched as" tag marks a record filed under a name other than the company name above.</p>' : '';
    var yr = state.ry ? '<span class="yrchip">' + (filter === 'contract' ? 'Fiscal year ' : 'Year ') + state.ry + ', ' + int0.format(list.length) +
      (list.length === 1 ? ' record' : ' records') + ' <button type="button" data-ry="clear" aria-label="Show every year">&#215;</button></span>' : '';
    var html = '<h3>Records for ' + esc(co.name || '') + ', by date</h3>' + incl + xboxHtml(co, d.excluded_amounts || []) +
      '<p class="note">Each record links to its source. Donations are gifts by people who name the company as employer. State payment dates are the first day of the fiscal year.</p>' +
      '<div class="chips" role="group" aria-label="Show records of type">' + chips + '</div>' + yr +
      '<ol class="events">' + list.slice(0, shown).map(function (it) { return evHtml(it, co.name); }).join('') + '</ol>';
    if (!list.length) html += '<p class="note" style="margin-top:8px">No record of this type in that year.</p>';
    if (list.length > shown) {
      html += '<button type="button" class="more" data-more="1">Show ' + Math.min(REC_PAGE, list.length - shown) + ' more of ' +
        int0.format(list.length - shown) + ' remaining</button>';
    }
    html += proxHtml(d.proximity || []);
    box.innerHTML = html;

    box.querySelectorAll('.chips button').forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        state.rf = b.dataset.f;
        box.dataset.shown = REC_PAGE;
        drawRecords(d, box);
        writeUrl();
        var nb = box.querySelector('.chips button[data-f="' + b.dataset.f + '"]');
        if (nb) nb.focus();
      });
    });
    var clr = box.querySelector('[data-ry]');
    if (clr) clr.addEventListener('click', function () { state.ry = null; drawRecords(d, box); writeUrl(); });
    var more = box.querySelector('[data-more]');
    if (more) more.addEventListener('click', function (e) {
      e.stopPropagation();
      box.dataset.shown = shown + REC_PAGE;
      drawRecords(d, box);
    });
  }

  // Parts of this company's cases that are not counted under the cash-only rule (register rows from the company file).
  function xboxHtml(co, rows) {
    var x = co.excluded;
    if (!x || !rows.length) return '';
    var head = x.headline_total > 0 ?
      "Headline figures for this company's cases were larger: counted" + ' <span class="mono">' + esc(money(x.counted_total)) + '</span> of <span class="mono">' +
        esc(money(x.headline_total)) + '</span> headline' :
      "Parts of this company's cases are not counted";
    if (x.not_counted_total > 0 && !(x.headline_total > 0 && Math.abs(x.headline_total - x.counted_total - x.not_counted_total) < 1)) {
      head += ' (<span class="mono">' + esc(money(x.not_counted_total)) + '</span> not counted in all)';
    }
    var out = '<div class="xbox"><p>' + head + '; see <a href="?tab=excluded&amp;xq=' + encodeURIComponent(co.company_id) + '">Amounts not counted</a>.</p><ul>';
    rows.forEach(function (r) {
      var u = safeUrl(r.source_url);
      out += '<li><span class="mono">' + esc(r.date) + '</span> ' + esc(r.agency) + ': counted <span class="mono">' + esc(money(r.counted_amount || 0)) +
        '</span>, headline <span class="mono">' + (r.headline_amount ? esc(money(r.headline_amount)) : 'not entered') + '</span>, not counted <span class="mono">' +
        (r.not_counted_amount !== null && r.not_counted_amount !== undefined ? esc(money(r.not_counted_amount)) : 'no dollar value stated') + '</span> (' +
        esc(r.category_label) + ')' + (u ? ' <a class="src" href="' + esc(u) + '" target="_blank" rel="noopener">Source: ' + esc(host(u)) + '</a>' : '') + '</li>';
    });
    return out + '</ul></div>';
  }

  function proxHtml(prox) {
    if (!prox.length) return '';
    var out = '<div class="prox"><h3>Donations near case dates: dates and amounts only</h3>' +
      '<p class="note">For each penalty, the recipients of employer-matched donations, the gift nearest the case date and the days between them (minus means before the case date). The table states timing and amounts; it does not state a reason for any gift.</p>';
    prox.forEach(function (p, i) {
      var c = p.case || {};
      var rows = (p.rows || []).slice().sort(function (a, b) { return Math.abs(a.days_to_case) - Math.abs(b.days_to_case); });
      out += '<details' + (i === 0 ? ' open' : '') + '><summary><span class="mono">' + esc(c.date) + '</span><span>' + esc(c.agency) + ' ' +
        esc(c.case_type) + '</span><span class="mono">' + esc(money(c.amount)) + '</span><span>' + int0.format(rows.length) +
        (rows.length === 1 ? ' recipient' : ' recipients') + '</span></summary>';
      out += '<div class="tscroll"><table class="pt"><thead><tr><th>Recipient</th><th>Office</th><th>Gifts</th><th>Total</th>' +
        '<th>Nearest gift</th><th>Days to case</th><th>Gifts in the 365 days before</th><th>Their total</th></tr></thead><tbody>';
      rows.forEach(function (r) {
        out += '<tr><td>' + esc(r.recipient_name) + '</td><td>' + esc(r.office) + '</td><td data-label="Gifts">' + int0.format(r.n) +
          '</td><td data-label="Total">' + esc(money(r.total)) + '</td><td data-label="Nearest gift">' + esc(r.nearest_donation_date) +
          '</td><td data-label="Days to case">' + esc(r.days_to_case) + '</td><td data-label="Gifts, 365 days before">' +
          int0.format(r.n_within_365_before || 0) + '</td><td data-label="Their total">' + esc(money(r.total_within_365_before || 0)) + '</td></tr>';
      });
      out += '</tbody></table></div></details>';
    });
    return out + '<p class="source">Source: company records file (data/companies/&lt;id&gt;.json, proximity block), from the penalty rows and OCPF and FEC contribution files.</p></div>';
  }

  // ---------- graph.json: payments by payer and donations by year, per company ----------
  function loadGraph() {
    fetch('data/corporate-ledger/graph.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (g) {
      var pay = {}, don = {}, last = 2009;
      g.edges.forEach(function (e) {
        if (e.type === 'contract') {
          var p = e.target.replace(/^payer:/, ''), a = pay[e.source] = pay[e.source] || {};
          a[e.year] = a[e.year] || {};
          a[e.year][p] = (a[e.year][p] || 0) + e.amount;
        } else if (e.type === 'donation') {
          var b = don[e.source] = don[e.source] || {};
          b[e.year] = b[e.year] || { s: 0, f: 0 };
          if (/^rec:C/.test(e.target)) b[e.year].f += e.amount; else b[e.year].s += e.amount;
          if (e.year > last) last = e.year;
        }
      });
      GD = { pay: pay, don: don, donLast: last };
      if (LEDGER) renderCharts();
      document.documentElement.dataset.graphReady = '1';
    }).catch(function () {
      ['p-pay', 'p-don'].forEach(function (id) { $(id).innerHTML = '<p class="empty-plot">The connections file (data/graph.json) could not be loaded. Reload the page to try again.</p>'; });
    });
  }

  // ---------- API for assets/connects.js (the How it connects tab) ----------
  var readyCbs = [], lensCbs = [], lastLens = null;
  function notifyLens() {
    if (state.lens === lastLens) return;
    lastLens = state.lens;
    lensCbs.slice().forEach(function (cb) { cb(state.lens); });
  }
  function toLedgerTab() {
    if (currentTabName() === 'ledger') return;
    showTab($('btn-ledger'), 'ledger');
    var qs = new URLSearchParams(location.search); qs.delete('tab');
    history.replaceState(null, '', location.pathname + (qs.toString() ? '?' + qs : '') + location.hash);
  }
  window.LEDGER_API = {
    whenReady: function (cb) { if (LEDGER) cb(LEDGER); else readyCbs.push(cb); },
    onLens: function (cb) { lensCbs.push(cb); },
    lens: function () { return state.lens; },
    setLens: function (lens) {
      if (!LENS_NAME[lens] || lens === state.lens) return;
      state.lens = lens; state.shown = PAGE; render();
      if (state.sel) panel(false);
    },
    recordFlags: recordFlags,
    comboKey: comboKey,
    comboLabel: comboLabel,
    inLens: inLens,
    byId: function (id) { return BYID[id] || null; },
    // Open the Ledger tab on exactly the companies that appear in these records (key like "payments+donations", or "none").
    openCombo: function (key) {
      if (!validCombo(key)) return;
      state.cb = key; state.f = {}; state.kind = 'all'; state.q = ''; state.sel = null; state.rf = null; state.ry = null; state.shown = PAGE;
      toLedgerTab();
      render(); panel(false);
      scrollToEl($('rows').closest('.table-card'));
      // keyboard and screen-reader users land on the line that says what the table now shows
      var ls = $('lens-sum');
      ls.setAttribute('tabindex', '-1');
      ls.focus({ preventScroll: true });
    },
    // Open one company's panel in the Ledger tab.
    openCompany: function (id) {
      var c = BYID[id];
      if (!c) return;
      if (!inLens(c)) state.lens = 'all';
      state.cb = '';
      toLedgerTab();
      select(id, true);
      $('co-panel').focus({ preventScroll: true });
    }
  };

  // ---------- wiring ----------
  function init() {
    readColours();
    readUrl();
    sortOptions();
    colMenu();
    var setNav = function () {
      document.documentElement.style.setProperty('--navh', navH() + 'px');
    };
    setNav();
    window.addEventListener('resize', setNav);
    $('q').value = state.q;
    $('q').addEventListener('input', function (e) { state.q = e.target.value; state.shown = PAGE; render(); });
    document.querySelectorAll('#lens button').forEach(function (b) {
      b.addEventListener('click', function () { state.lens = b.dataset.lens; state.shown = PAGE; render(); if (state.sel) panel(false); });
    });
    document.querySelectorAll('#kind button').forEach(function (b) {
      b.addEventListener('click', function () { state.kind = b.dataset.kind; state.shown = PAGE; render(); });
    });
    document.querySelectorAll('#fchips .fchip').forEach(function (b) {
      b.addEventListener('click', function () { state.f[b.dataset.f] = !state.f[b.dataset.f]; state.shown = PAGE; render(); });
    });
    document.querySelectorAll('.kpi').forEach(function (b) { b.addEventListener('click', function () { kpiClick(b.dataset.kpi); }); });
    $('reset').addEventListener('click', function () {
      state.lens = DEFAULT.lens; state.q = ''; state.sort = DEFAULT.sort; state.dir = DEFAULT.dir; state.f = {}; state.kind = 'all'; state.cb = '';
      state.hide = {}; state.shown = PAGE; state.sel = null; state.rf = null; state.ry = null;
      render(); panel(false);
    });
    $('cb-clear').addEventListener('click', function () { state.cb = ''; state.shown = PAGE; render(); });
    // clear-selection chips and example picks anywhere on the tab
    document.addEventListener('click', function (e) {
      var c = e.target.closest && e.target.closest('[data-clear]');
      if (c) { e.preventDefault(); clearSel(); return; }
      var p = e.target.closest && e.target.closest('[data-pick]');
      if (p) select(p.getAttribute('data-pick'), true);
    });
    var rows = $('rows');
    rows.addEventListener('click', function (e) {
      if (e.target.closest('a')) return;
      var tr = e.target.closest('tr.row');
      if (!tr) return;
      if (state.sel === tr.dataset.id) clearSel(); else select(tr.dataset.id, true);
    });
    rows.addEventListener('mouseover', function (e) {
      var tr = e.target.closest('tr.row');
      document.querySelectorAll('#p-top .mk.hl').forEach(function (g) { if (!tr || g.getAttribute('data-id') !== tr.dataset.id) g.classList.remove('hl'); });
      if (tr) hlBar(tr.dataset.id, true);
    });
    rows.addEventListener('mouseleave', function () { document.querySelectorAll('#p-top .mk.hl').forEach(function (g) { g.classList.remove('hl'); }); });
    window.addEventListener('hashchange', function () {
      if (location.hash.indexOf('=') < 0 || !LEDGER) return;
      var was = state.sel;
      readUrl();
      if (state.sel && !BYID[state.sel]) state.sel = null;
      render();
      if (state.sel !== was) panel(false);
    });
    window.addEventListener('scroll', function () { tip(null); }, { passive: true });
    var lastW = 0, t = null;
    window.addEventListener('resize', function () {
      clearTimeout(t);
      t = setTimeout(function () {
        var w = $('charts').clientWidth;
        if (w === lastW) return;
        lastW = w;
        renderCharts();
        if (state.sel && cache[state.sel]) cache[state.sel].then(function (d) { drawTimeline(d); });
      }, 150);
    });
    window.TAB_INIT = window.TAB_INIT || {};
    TAB_INIT.ledger = function () {
      renderCharts();
      if (state.sel && cache[state.sel]) cache[state.sel].then(function (d) { drawTimeline(d); });
    };

    loadGraph();   // in parallel with the ledger; the charts that need it draw when it lands
    fetch('data/corporate-ledger/ledger.json').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      LEDGER = d;
      d.companies.forEach(function (c) { BYID[c.company_id] = c; });
      sharedFootnote();
      var fy = /FY(\d{4})/.exec((d.coverage.contracts || {}).to || '');
      if (fy) FY1 = +fy[1];
      $('updated-date').textContent = d.generated + ' (data vintage: penalties to ' +
        d.coverage.penalties.to + ', state donations to ' + d.coverage.donations_ocpf.to + ')';
      if (state.sel && !BYID[state.sel]) state.sel = null;
      if (state.sel && !inLens(BYID[state.sel])) state.lens = 'all';
      render();
      panel(!!state.sel);
      document.documentElement.dataset.ledgerReady = '1';
      readyCbs.splice(0).forEach(function (cb) { cb(LEDGER); });
    }).catch(function () {
      $('rows').innerHTML = '<tr><td colspan="9" class="empty">The ledger file (data/ledger.json) could not be loaded. Reload the page to try again.</td></tr>';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
