/* Case files tab: two case cards from data/cases/<id>.json; opening one renders its sections and three Chart.js
   charts. Charts are built only when their figure scrolls into view (IntersectionObserver) and all of them are
   destroyed when the tab is left (TAB_CLEANUP), per the Hub template's SOLVED BUGS.
   Chart data:
   - Penalties: figures.penalties.rows (one bar per row, labelled by date and agency; rows left out of the counted
     total by an overlap are hatched).
   - State payments: graph.json contract edges for the company (payer and fiscal year), each year checked against
     figures.contracts.by_year; a mismatch is shown on the page, not hidden.
   - Donations: graph.json donation edges summed per recipient committee (state and federal as separate series),
     checked against figures.donations.<source>.top_recipients and the source totals.
   Case text is the build step's escaped HTML (pipeline/build_site.py); the figure tags inside it are hidden behind
   a toggle and stay reachable through it and through each marker's title.
   Layout (from 1000 px): each section is one flow of blocks, chart first. layoutSection tries a short list of
   arrangements (single column, balanced columns, chart across the top, tables across the page, a two-track packing),
   measures the empty space each leaves and keeps the first that leaves no large empty block; see compose() and
   layoutSection() below. It runs again on resize, when source tags are shown or hidden, and when the donations chart
   is opened out to every recipient.
   URL parameters: ?tab=cases&case=<id>  ?tags=1 (show tags) */
(function () {
  'use strict';

  var CASES = [
    { id: 'suffolk-construction', short: 'Suffolk Construction' },
    { id: 'state-street', short: 'State Street' }
  ];
  // Stack order: darkest step of the Bay Blue payments ramp at the base. Colours come from the page's CSS variables
  // (--s-* and --pay-*), the one stream mapping shared with the Ledger and the Explorer.
  var PAYERS = ['CTHRU', 'MBTA', 'MASSPORT', 'MSBA'];
  var PAYER_NAME = { CTHRU: 'CTHRU (state agencies)', MASSPORT: 'Massport', MBTA: 'MBTA', MSBA: 'MSBA (school building authority)' };
  function cssv(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  var PAYER_COLOR = {}, PEN_COLOR = '', DON_COLOR = {};
  function readColours() {
    PAYER_COLOR = { CTHRU: cssv('--pay-cthru'), MBTA: cssv('--pay-mbta'), MASSPORT: cssv('--pay-massport'), MSBA: cssv('--pay-msba') };
    PEN_COLOR = cssv('--s-penalty');
    DON_COLOR = { state: cssv('--s-donation'), federal: cssv('--s-donation-fed') };
  }
  var CAP = 12;

  var cache = {};
  var graph = null;
  var charts = [];
  var observer = null;
  var current = null;
  var showTags = new URLSearchParams(location.search).get('tags') === '1';

  // ---------- formatting (same rules as the Ledger tab) ----------
  var usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  var sig3 = new Intl.NumberFormat('en-US', { minimumSignificantDigits: 3, maximumSignificantDigits: 3 });
  function money(n) {
    if (n === null || n === undefined || isNaN(n)) return '';
    var a = Math.abs(n), s = n < 0 ? '-' : '';
    if (a >= 1e9) return s + '$' + sig3.format(a / 1e9) + 'B';
    if (a >= 1e6) return s + '$' + sig3.format(a / 1e6) + 'M';
    return usd0.format(n);
  }
  function axisMoney(n) {
    var a = Math.abs(n);
    if (a >= 1e9) return '$' + (n / 1e9) + 'B';
    if (a >= 1e6) return '$' + (n / 1e6) + 'M';
    if (a >= 1e3) return '$' + (n / 1e3) + 'K';
    return '$' + n;
  }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function getJSON(url) {
    if (!cache[url]) cache[url] = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
    return cache[url];
  }
  // The two written case files live in data/cases; every other company has a generated data-only profile in
  // data/profiles (pipeline/build_profiles.py).
  function isWritten(id) { return CASES.some(function (c) { return c.id === id; }); }
  function dataUrl(id) { return (isWritten(id) ? 'data/corporate-ledger/cases/' : 'data/corporate-ledger/profiles/') + encodeURIComponent(id) + '.json'; }
  function validId(id) { return /^[a-z0-9][a-z0-9-]*$/.test(id || ''); }
  function loadGraph() { return graph ? Promise.resolve(graph) : getJSON('data/corporate-ledger/graph.json').then(function (g) { graph = g; return g; }); }

  // ---------- tab lifecycle ----------
  function init() {
    var p = new URLSearchParams(location.search).get('case');
    var root = document.getElementById('cases-root');
    if (!root.dataset.built) { buildCards(root); buildPicker(); }
    open(validId(p) ? p : current, false);
  }
  function cleanup() {
    charts.forEach(function (c) { c.destroy(); });
    charts = [];
    if (observer) { observer.disconnect(); observer = null; }
    document.querySelectorAll('#case-view canvas').forEach(function (cv) { cv.dataset.built = ''; });
  }
  window.TAB_INIT = window.TAB_INIT || {};
  window.TAB_CLEANUP = window.TAB_CLEANUP || {};
  TAB_INIT.cases = init;
  TAB_CLEANUP.cases = cleanup;

  // ---------- case cards ----------
  function buildCards(root) {
    root.dataset.built = '1';
    var list = document.getElementById('case-cards');
    CASES.forEach(function (c) {
      var b = el('button', 'case-card');
      b.type = 'button';
      b.dataset.id = c.id;
      b.setAttribute('aria-pressed', 'false');
      b.appendChild(el('span', 'cc-name', c.short));
      b.appendChild(el('span', 'cc-facts mono', 'Loading figures'));
      b.addEventListener('click', function () { open(c.id, true); });
      list.appendChild(b);
      getJSON(dataUrl(c.id)).then(function (d) {
        var f = d.figures;
        var pen = f.penalties.counted.value, gross = f.penalties.gross.value;
        var facts = b.querySelector('.cc-facts');
        facts.textContent = '';
        [['Penalties counted', money(pen) + (gross !== pen ? ' (gross ' + money(gross) + ')' : '')],
         ['State payments', money(f.contracts.total.value)],
         ['Donations, state / federal', money(f.donations.ocpf.total.value) + ' / ' + money(f.donations.fec.total.value)]
        ].forEach(function (kv) {
          var s = el('span', 'cc-fact');
          s.appendChild(el('span', 'cc-k', kv[0]));
          s.appendChild(el('span', 'cc-v', kv[1]));
          facts.appendChild(s);
        });
      }).catch(function () { b.querySelector('.cc-facts').textContent = 'Figures did not load.'; });
    });
  }


  // ---------- profile picker: a data-only profile for every company in the ledger ----------
  var profiles = null;
  function buildPicker() {
    var q = document.getElementById('pf-q'), list = document.getElementById('pf-list'), n = document.getElementById('pf-n');
    if (!q || !list) return;
    function fill(term) {
      if (!profiles) return;
      var t = term.trim().toLowerCase();
      var hits = profiles.filter(function (e) { return !t || e.name.toLowerCase().indexOf(t) >= 0; });
      if (!t) hits = hits.slice().sort(function (a, b) { return (b.counted || 0) - (a.counted || 0) || (a.name < b.name ? -1 : 1); });
      list.innerHTML = '';
      hits.slice(0, t ? 16 : 9).forEach(function (e) {
        var li = el('li'), a = el('a');
        a.href = '?tab=cases&case=' + encodeURIComponent(e.id);
        a.appendChild(el('span', 'pf-name', e.name));
        a.appendChild(el('span', 'pf-sub', e.counted ? money(e.counted) + ' counted' : (e.kind && e.kind !== 'company' ? e.kind : 'no penalty counted')));
        li.appendChild(a);
        list.appendChild(li);
      });
      if (!hits.length) list.appendChild(el('li', 'pf-empty', 'No company matches that name.'));
      else if (hits.length > list.children.length) list.appendChild(el('li', 'pf-empty', (hits.length - list.children.length) + ' more: type more of the name.'));
    }
    getJSON('data/corporate-ledger/profiles/index.json').then(function (ix) {
      profiles = ix.profiles;
      if (n) n.textContent = String(profiles.length);
      fill(q.value);
    }).catch(function () { list.appendChild(el('li', 'pf-empty', 'The profile list did not load. Reload the page to try again.')); });
    q.addEventListener('input', function () { fill(q.value); });
    list.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;
      e.preventDefault();
      e.stopPropagation();
      open(new URLSearchParams(a.getAttribute('href').slice(1)).get('case'), true);
    });
  }

  function open(id, scroll) {
    document.querySelectorAll('.case-card').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.id === id)); });
    var view = document.getElementById('case-view');
    if (!id) { view.innerHTML = ''; view.hidden = true; markReady(); return; }
    cleanup();
    current = id;
    view.hidden = false;
    view.innerHTML = '<p class="placeholder">Loading the case file</p>';
    var url = new URL(location.href);
    url.searchParams.set('tab', 'cases');
    url.searchParams.set('case', id);
    history.replaceState(null, '', url);
    Promise.all([getJSON(dataUrl(id)), loadGraph()]).then(function (res) {
      if (current !== id) return;
      render(view, res[0], res[1]);
      if (scroll) view.scrollIntoView({ block: 'start' });
      markReady();
    }).catch(function (e) {
      view.innerHTML = '';
      view.appendChild(el('p', 'placeholder', 'The case file did not load (' + e.message + ').'));
      markReady();
    });
  }
  function markReady() { document.documentElement.dataset.casesReady = '1'; }

  // ---------- case page ----------
  function render(view, d, g) {
    readColours();
    view.innerHTML = '';
    var f = d.figures;
    var head = el('div', 'case-head');
    head.appendChild(el('h3', 'case-title', d.title));
    var meta = el('p', 'case-meta');
    meta.appendChild(el('span', 'mono', 'Updated ' + f.generated));
    if (!isWritten(d.id)) meta.appendChild(el('span', '', 'Data profile: computed from the ledger tables, no written analysis'));
    var fl = el('a', '', 'Figures file (JSON)');
    fl.href = dataUrl(d.id);
    meta.appendChild(fl);
    head.appendChild(meta);
    var tg = el('label', 'tag-toggle');
    var cb = el('input');
    cb.type = 'checkbox';
    cb.checked = showTags;
    cb.addEventListener('change', function () { showTags = cb.checked; view.classList.toggle('tags-on', showTags); layoutAll(); });
    tg.appendChild(cb);
    tg.appendChild(document.createTextNode(' Show source tags'));
    head.appendChild(tg);
    head.appendChild(el('p', 'tag-note', 'Each figure in the text carries a tag naming the table and row filter it was counted from. Tags are hidden to keep the text readable; the small s after a figure shows its tag on hover, and the checkbox shows them all.'));
    view.appendChild(head);
    view.classList.toggle('tags-on', showTags);
    // The cash-only amount rule, the same box as on the Ledger tab (static text in the page, id amount-rule).
    var rule = document.getElementById('amount-rule');
    if (rule) {
      var rb = rule.cloneNode(true);
      rb.removeAttribute('id');
      rb.style.marginTop = '14px';
      view.appendChild(rb);
    }

    var anchors = {};
    d.sections.forEach(function (s) {
      var sec = el('section', 'case-sec');
      if (/^Opinion/i.test(s.heading)) {
        sec.className += ' opinion';
        sec.appendChild(el('h4', '', "Opinion (the owner's)"));
      } else if (s.heading) {
        sec.appendChild(el('h4', '', s.heading));
      }
      var body = el('div', 'case-body');
      body.innerHTML = s.html;  // escaped at build time (pipeline/build_site.py), checked by checks/test_site.py
      body.querySelectorAll('span.ref').forEach(function (r) {
        r.setAttribute('title', r.textContent);
        var m = el('span', 'ref-mark', 's');
        m.setAttribute('title', r.textContent);
        m.setAttribute('aria-hidden', 'true');
        r.parentNode.insertBefore(m, r);
      });
      body.querySelectorAll('a[href]').forEach(function (a) {
        if (!/^https?:\/\//i.test(a.getAttribute('href'))) a.removeAttribute('href');
        else if (a.textContent === a.getAttribute('href')) { a.textContent = shortUrl(a.textContent); a.title = a.getAttribute('href'); }
      });
      compose(body);
      var flow = el('div', 'cs-flow');
      flow.appendChild(body);
      sec.appendChild(flow);
      view.appendChild(sec);
      anchors[s.heading] = { sec: sec, flow: flow, body: body };
    });

    var penFig = penaltyFigure(d, f);
    var payFig = paymentsFigure(d, f, g);
    var donFig = donationsFigure(d, f, g);
    place(anchors, 'Penalties', penFig, view);
    place(anchors, 'Money from the state', payFig, view);
    place(anchors, 'Money to officials', donFig, view);
    layoutAll();
    watch(view);
  }
  function place(anchors, heading, fig, view) {
    var a = anchors[heading];
    if (a) a.flow.insertBefore(fig, a.body); else view.appendChild(fig);
  }
  function shortUrl(u) {
    try {
      var x = new URL(u);
      var path = x.pathname.length > 28 ? x.pathname.slice(0, 26) + '...' : x.pathname;
      return x.hostname.replace(/^www\./, '') + path;
    } catch (e) { return u; }
  }

  function figure(id, heading, sub, source) {
    var fig = el('figure', 'cfig');
    fig.id = id;
    var h = el('h5', 'cfig-h', heading);
    h.id = id + '-h';
    fig.appendChild(h);
    if (sub) fig.appendChild(el('p', 'cfig-sub', sub));
    var legend = el('div', 'cfig-legend');
    fig.appendChild(legend);
    var wrap = el('div', 'cwrap');
    var cv = el('canvas');
    cv.setAttribute('role', 'img');
    cv.setAttribute('aria-labelledby', id + '-h');
    wrap.appendChild(cv);
    fig.appendChild(wrap);
    var src = el('p', 'source', 'Source: ' + source);
    fig.appendChild(src);
    return { fig: fig, canvas: cv, wrap: wrap, legend: legend, src: src };
  }
  function legendItem(box, color, label, hatch) {
    var s = el('span', 'lg');
    var sw = el('span', 'lg-sw' + (hatch ? ' hatch' : ''));
    sw.style.setProperty('--c', color);
    s.appendChild(sw);
    s.appendChild(document.createTextNode(label));
    box.appendChild(s);
  }

  // ---------- chart 1: penalties, one bar per row ----------
  function penaltyFigure(d, f) {
    var P = f.penalties;
    var rows = P.rows.slice().sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : b.amount - a.amount; });
    var counted = P.counted.value, gross = P.gross.value;
    var heading = 'Penalties by date and agency: ' + money(counted) + ' counted' + (gross !== counted ? ', ' + money(gross) + ' gross' : '');
    var L = P.counted_by_lens || {};
    var lensTxt = L.ma_conduct && L.ma_hq ? 'Counted under the Massachusetts case lens ' + money(L.ma_conduct.value) + ', under the Massachusetts headquarters lens ' + money(L.ma_hq.value) + '; the chart shows both. ' : '';
    var nShared = rows.filter(function (r) { return !r.counted && /^shared-/.test(r.overlap_group || ''); }).length;
    var nPossible = rows.filter(function (r) { return !r.counted && /^possible-/.test(r.overlap_group || ''); }).length;
    var nRestated = rows.filter(function (r) { return !r.counted; }).length - nShared - nPossible;
    var why = [];
    if (nRestated) why.push('rows another row already covers (the same money listed twice)');
    if (nPossible) why.push('a possible duplicate, counted once until verified');
    if (nShared) why.push('one payment shared by several defendants that the source does not split between them');
    var sub = rows.length + ' government penalty rows, fiscal 2010 on. ' + lensTxt +
      (gross !== counted ? 'Hatched bars are ' + why.join(' and ') + '; they are in gross and left out of counted.' : 'Every row is counted; none overlaps another.');
    var x = figure('cfig-pen-' + d.id, heading, sub,
      'case figures file (' + d.id + '.json, penalties rows), built from the agencies\' own releases and orders (linked in the list below) and the Corporate Prosecution Registry.');
    legendItem(x.legend, PEN_COLOR, 'Counted');
    if (gross !== counted) legendItem(x.legend, PEN_COLOR, 'Not counted', true);
    x.wrap.style.height = Math.max(160, rows.length * (isNarrow() ? 36 : 30) + 50) + 'px';
    x.canvas._build = function () {
      var labels = rows.map(function (r) { return isNarrow() ? [r.agency, r.date] : r.date + '  ' + r.agency; });
      var hatch = hatchPattern(x.canvas, PEN_COLOR);
      return new Chart(x.canvas, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            { label: 'Counted', data: rows.map(function (r) { return r.counted ? r.amount : null; }), backgroundColor: PEN_COLOR },
            { label: 'Not counted', data: rows.map(function (r) { return r.counted ? null : r.amount; }), backgroundColor: hatch, borderColor: PEN_COLOR, borderWidth: 1 }
          ]
        },
        options: barOptions({
          indexAxis: 'y',
          stacked: true,
          tooltip: function (ctx) {
            var r = rows[ctx.dataIndex];
            return [money(r.amount) + (r.counted ? ' counted' : /^shared-/.test(r.overlap_group || '') ? ' not counted: one total shared by several defendants, not split' : /^possible-/.test(r.overlap_group || '') ? ' not counted: possible duplicate, counted once until verified' : ' not counted: the same payment is counted once on another row (' + r.overlap_group + ')'),
              r.case_type + ', ' + (r.lens === 'ma_conduct' ? 'Massachusetts case' : 'Massachusetts headquarters')];
          }
        })
      });
    };
    return x.fig;
  }

  // ---------- chart 2: state payments by fiscal year, stacked by payer ----------
  function paymentsFigure(d, f, g) {
    var by = {}, payersSeen = {};
    g.edges.forEach(function (e) {
      if (e.source !== d.id || e.type !== 'contract') return;
      var p = e.target.replace(/^payer:/, '');
      payersSeen[p] = 1;
      by[e.year] = by[e.year] || {};
      by[e.year][p] = (by[e.year][p] || 0) + e.amount;
    });
    var fy = Object.keys(f.contracts.by_year).map(Number);
    var first = f.window.first_fiscal_year, last = Math.max.apply(null, fy);
    var years = [];
    for (var y = first; y <= last; y++) years.push(y);
    var mism = [];
    years.forEach(function (y) {
      var want = f.contracts.by_year[y] ? f.contracts.by_year[y].value : 0;
      var got = 0;
      Object.keys(by[y] || {}).forEach(function (p) { got += by[y][p]; });
      if (Math.abs(want - got) > 0.5) mism.push('FY' + y + ' figures ' + money(want) + ', graph ' + money(got));
    });
    var payers = PAYERS.filter(function (p) { return payersSeen[p]; });
    var x = figure('cfig-pay-' + d.id,
      'State payments by fiscal year, by payer: ' + money(f.contracts.total.value) + ' since fiscal ' + first,
      'Net payments recorded by each payer' + (('FY' + last) === f.coverage.contracts.to ? '; fiscal ' + last + ' is partial' : '; the newest year with a payment is fiscal ' + last + ', and the records run to ' + f.coverage.contracts.to.replace('FY', 'fiscal ')) + '. Years with no bar have no payment on record; very small years are drawn at a minimum height (hover for the amount).',
      'case figures file (' + d.id + '.json, contracts by year) and graph.json contract links, from CTHRU (Comptroller), MBTA, Massport and MSBA payment records.');
    payers.forEach(function (p) { legendItem(x.legend, PAYER_COLOR[p], PAYER_NAME[p]); });
    if (mism.length) x.fig.insertBefore(el('p', 'cfig-warn', 'Check failed, chart may be wrong: ' + mism.join('; ')), x.wrap);
    x.wrap.style.height = '300px';
    x.canvas._build = function () {
      return new Chart(x.canvas, {
        type: 'bar',
        data: {
          labels: years.map(function (y) { return 'FY' + y; }),
          datasets: payers.map(function (p) {
            return { label: PAYER_NAME[p], data: years.map(function (y) { return (by[y] || {})[p] || null; }),
              backgroundColor: PAYER_COLOR[p], borderColor: '#FFFFFF', borderWidth: { top: 2 }, borderSkipped: 'bottom', minBarLength: 3 };
          })
        },
        options: barOptions({
          stacked: true,
          tooltip: function (ctx) { return ctx.dataset.label + ': ' + money(ctx.raw); },
          footer: function (items) {
            var y = years[items[0].dataIndex];
            return 'All payers FY' + y + ': ' + money(f.contracts.by_year[y] ? f.contracts.by_year[y].value : 0);
          }
        })
      });
    };
    return x.fig;
  }

  // ---------- chart 3: donations by recipient, state and federal as separate series ----------
  function donationsFigure(d, f, g) {
    var labels = {};
    g.nodes.forEach(function (n) { labels[n.id] = n.label; });
    var agg = {};
    g.edges.forEach(function (e) {
      if (e.source !== d.id || e.type !== 'donation') return;
      var a = agg[e.target] || (agg[e.target] = { id: e.target, total: 0, n: 0, fed: /^rec:C/.test(e.target) });
      a.total += e.amount;
      a.n += e.n;
    });
    var all = Object.keys(agg).map(function (k) { return agg[k]; }).sort(function (a, b) { return b.total - a.total || (labels[a.id] < labels[b.id] ? -1 : 1); });
    // check against the figures file: source totals and every listed top recipient
    var bad = [];
    [['ocpf', false], ['fec', true]].forEach(function (s) {
      var D = f.donations[s[0]], sum = 0, n = 0;
      all.forEach(function (a) { if (a.fed === s[1]) { sum += a.total; n++; } });
      if (Math.abs(sum - D.total.value) > 0.5) bad.push(s[0].toUpperCase() + ' total');
      if (n !== D.n_recipients) bad.push(s[0].toUpperCase() + ' recipient count');
      D.top_recipients.forEach(function (r) {
        var a = agg['rec:' + r.recipient_id];
        if (!a || Math.abs(a.total - r.total.value) > 0.5 || a.n !== r.n) bad.push(r.recipient_name);
      });
    });
    var x = figure('cfig-don-' + d.id,
      'Donations by employees, by recipient: ' + money(f.donations.ocpf.total.value) + ' state, ' + money(f.donations.fec.total.value) + ' federal',
      'Gifts from people who name the company as employer, summed per recipient committee, ' + f.donations.ocpf.n_recipients + ' state and ' + f.donations.fec.n_recipients + ' federal recipients. State and federal are separate series and are never added together. They are personal gifts, not company money.',
      'case figures file (' + d.id + '.json, donations) and graph.json donation links, from OCPF (state) and FEC (federal) contribution files, confirmed employer matches only.');
    legendItem(x.legend, DON_COLOR.state, 'State (OCPF)');
    legendItem(x.legend, DON_COLOR.federal, 'Federal (FEC)', true);
    if (bad.length) x.fig.insertBefore(el('p', 'cfig-warn', 'Check against the figures file failed for: ' + bad.join(', ')), x.wrap);
    var shown = Math.min(CAP, all.length);
    function setHeight() { x.wrap.style.height = Math.max(160, shown * (isNarrow() ? 36 : 26) + 50) + 'px'; }
    setHeight();
    var chart = null;
    x.canvas._build = function () {
      var rows = all.slice(0, shown);
      chart = new Chart(x.canvas, {
        type: 'bar',
        data: {
          labels: rows.map(function (a) {
            if (!isNarrow()) return trim(labels[a.id], 34);
            var m = /^(.*) \((.*)\)$/.exec(labels[a.id] || '');
            return m ? [trim(m[1], 20), trim(m[2], 20)] : trim(labels[a.id], 20);
          }),
          datasets: [
            { label: 'State (OCPF)', data: rows.map(function (a) { return a.fed ? null : a.total; }), backgroundColor: DON_COLOR.state },
            { label: 'Federal (FEC)', data: rows.map(function (a) { return a.fed ? a.total : null; }), backgroundColor: hatchPattern(x.canvas, DON_COLOR.federal), borderColor: DON_COLOR.federal, borderWidth: 1 }
          ]
        },
        options: barOptions({
          indexAxis: 'y',
          stacked: true,
          title: function (items) { return labels[rows[items[0].dataIndex].id]; },
          tooltip: function (ctx) { var a = rows[ctx.dataIndex]; return ctx.dataset.label + ': ' + money(a.total) + ' in ' + a.n + (a.n === 1 ? ' gift' : ' gifts'); }
        })
      });
      return chart;
    };
    if (all.length > CAP) {
      var btn = el('button', 'more', 'Show all ' + all.length + ' recipients');
      btn.type = 'button';
      btn.setAttribute('aria-controls', x.fig.id);
      btn.addEventListener('click', function () {
        shown = shown === all.length ? CAP : all.length;
        btn.textContent = shown === all.length ? 'Show the top ' + CAP + ' only' : 'Show all ' + all.length + ' recipients';
        note.textContent = shown === all.length ? 'Showing all ' + all.length + ' recipients by amount; the amount axis is at the foot of the chart.' : 'Showing the top ' + CAP + ' of ' + all.length + ' recipients by amount.';
        setHeight();
        layoutFor(x.fig);
        if (chart) {
          var i = charts.indexOf(chart);
          chart.destroy();
          var c2 = x.canvas._build();
          if (i >= 0) charts[i] = c2; else charts.push(c2);
        }
      });
      var note = el('p', 'cfig-sub', 'Showing the top ' + CAP + ' of ' + all.length + ' recipients by amount.');
      note.setAttribute('aria-live', 'polite');
      x.fig.insertBefore(btn, x.src);
      x.fig.insertBefore(note, x.wrap);
    }
    return x.fig;
  }
  function isNarrow() { return window.innerWidth < 640; }
  function trim(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '...' : s; }

  // ---------- layout: each section is one flow of blocks, chart first ----------
  // A table goes in a scrolling wrapper (.tw): a table that is genuinely wide scrolls there and never the page, a narrow
  // one fills its cell. A paragraph that introduces a table or a list is grouped with it (.cu), so the two are never
  // separated by a column break or by the packing below.
  // the text a reader sees: without the figure tags, which are hidden unless the checkbox is ticked
  function plainText(node) {
    var c = node.cloneNode(true);
    Array.prototype.forEach.call(c.querySelectorAll('.ref, .ref-mark'), function (r) { r.remove(); });
    return c.textContent;
  }
  function compose(body) {
    Array.prototype.slice.call(body.children).forEach(function (c) {
      if (c.tagName !== 'TABLE') return;
      var w = el('div', 'tw');
      body.replaceChild(w, c);
      w.appendChild(c);
    });
    Array.prototype.slice.call(body.children).forEach(function (c) {
      var n = c.nextElementSibling;
      if (c.tagName !== 'P' || !n) return;
      var tbl = n.classList.contains('tw');
      if (!tbl && n.tagName !== 'UL' && n.tagName !== 'OL') return;
      // a short list stays whole with its lead-in (.cu-keep); a long one may run on into the next column
      var short = !tbl && n.children.length <= 4 && plainText(n).length < 400;
      var u = el('div', 'cu ' + (tbl ? 'cu-tbl' : 'cu-lst') + (short ? ' cu-keep' : ''));
      body.insertBefore(u, c);
      u.appendChild(c);
      u.appendChild(n);
    });
    // dates, years, counts and amounts never wrap inside their cell
    Array.prototype.forEach.call(body.querySelectorAll('td'), function (td) {
      if (/^[\d$,.\-%]+$/.test(plainText(td).trim())) td.classList.add('nw');
    });
    Array.prototype.slice.call(body.children).forEach(function (c) {
      if (!c.classList.contains('tw')) return;
      var u = el('div', 'cu cu-tbl');
      body.insertBefore(u, c);
      u.appendChild(c);
    });
    // a short paragraph or list item is never split between two columns (.kp)
    Array.prototype.forEach.call(body.querySelectorAll('p, li'), function (n) {
      if (plainText(n).length <= (n.tagName === 'P' ? 640 : 520)) n.classList.add('kp');
    });
  }

  var WIDE = window.matchMedia('(min-width: 1000px)');
  // In order of preference. lay-cols: balanced columns with the chart at the head of the first; lay-grow: the chart is
  // made taller to fill the first column when the text column runs longer; lay-span: the chart across the full width;
  // lay-tw: tables across the full width between column bands; lay-mason: two tracks, each block placed in the shorter
  // one. '' is the plain single column (text lines capped at 80ch).
  var LAYOUTS = ['', 'lay-cols lay-grow', 'lay-cols', 'lay-cols lay-span', 'lay-cols lay-tw', 'lay-cols lay-span lay-tw',
    'lay-mason', 'lay-mason lay-span', 'lay-mason lay-tw', 'lay-mason lay-span lay-tw'];
  var EMPTY_PASS = 150;      // px: an arrangement passes when no empty block this tall is a quarter of the width (page rule: 200)
  var EMPTY_WIDTH = 0.25;    // share of the section width an empty area must reach to count
  var SHORT = 120;           // px: a section this short stays a single column
  var TRACK_GAP = 14;        // px between blocks in the two-track packing

  function unitsOf(flow) {
    var fig = flow.querySelector(':scope > .cfig'), body = flow.querySelector(':scope > .case-body');
    return (fig ? [fig] : []).concat(Array.prototype.slice.call(body.children));
  }
  function isWide(u, flow) {
    return (u.classList.contains('cfig') && flow.classList.contains('lay-span')) ||
      (u.classList.contains('cu-tbl') && flow.classList.contains('lay-tw'));
  }
  // lay-mason: heights are measured in the grid, then every block gets an explicit track and row span (rows are 1 px high).
  function pack(flow, units) {
    units.forEach(function (u) { u.style.gridColumn = isWide(u, flow) ? '1 / -1' : ''; u.style.gridRow = ''; });
    var hs = units.map(function (u) { return Math.max(1, Math.ceil(u.getBoundingClientRect().height)); });
    var bottom = [0, 0];
    units.forEach(function (u, i) {
      var start;
      if (isWide(u, flow)) {
        start = Math.max(bottom[0], bottom[1]);
        bottom[0] = bottom[1] = start + hs[i] + TRACK_GAP;
        u.style.gridColumn = '1 / -1';
      } else {
        var t = bottom[0] <= bottom[1] ? 0 : 1;
        start = bottom[t];
        bottom[t] = start + hs[i] + TRACK_GAP;
        u.style.gridColumn = String(t + 1);
      }
      u.style.gridRow = (start + 1) + ' / span ' + hs[i];
    });
  }
  // Every line of text, every table row and every chart card, as boxes relative to the flow.
  function inkBoxes(flow) {
    var r0 = flow.getBoundingClientRect(), out = [];
    function add(r) {
      if (r.width > 0 && r.height > 0) out.push([r.left - r0.left, r.top - r0.top, r.right - r0.left, r.bottom - r0.top]);
    }
    var walker = document.createTreeWalker(flow, NodeFilter.SHOW_TEXT, null), range = document.createRange(), n;
    while ((n = walker.nextNode())) {
      if (!/\S/.test(n.nodeValue)) continue;
      range.selectNodeContents(n);
      Array.prototype.forEach.call(range.getClientRects(), add);
    }
    Array.prototype.forEach.call(flow.querySelectorAll('figure, tr'), function (e) { add(e.getBoundingClientRect()); });
    return { w: r0.width, h: r0.height, boxes: out };
  }
  // Height in px of the tallest empty rectangle that is at least EMPTY_WIDTH of the flow wide (6 px cells).
  function emptyHeight(info) {
    var C = 6, cols = Math.max(1, Math.ceil(info.w / C)), rows = Math.max(1, Math.ceil(info.h / C));
    var occ = new Uint8Array(cols * rows);
    info.boxes.forEach(function (b) {
      var x0 = Math.max(0, Math.floor(b[0] / C)), x1 = Math.min(cols, Math.ceil(b[2] / C));
      var y0 = Math.max(0, Math.floor(b[1] / C)), y1 = Math.min(rows, Math.ceil(b[3] / C));
      for (var y = y0; y < y1; y++) occ.fill(1, y * cols + x0, y * cols + x1);
    });
    var win = Math.min(cols, Math.max(1, Math.ceil(info.w * EMPTY_WIDTH / C)));
    var up = new Uint16Array(cols), best = 0, dq = new Int32Array(cols);
    for (var yy = 0; yy < rows; yy++) {
      var head = 0, tail = 0;
      for (var x = 0; x < cols; x++) {
        up[x] = occ[yy * cols + x] ? 0 : up[x] + 1;
        while (tail > head && up[dq[tail - 1]] >= up[x]) tail--;
        dq[tail++] = x;
        if (dq[head] <= x - win) head++;
        if (x >= win - 1 && up[dq[head]] > best) best = up[dq[head]];
      }
    }
    return best * C;
  }
  // A table must never be broken across two columns.
  function tableSplit(flow) {
    var split = false;
    Array.prototype.forEach.call(flow.querySelectorAll('.cu-tbl table'), function (t) {
      var lo = 1e9, hi = -1e9;
      Array.prototype.forEach.call(t.querySelectorAll('tr'), function (r) {
        var l = r.getBoundingClientRect().left;
        lo = Math.min(lo, l);
        hi = Math.max(hi, l);
      });
      if (hi - lo > 60) split = true;
    });
    return split;
  }
  // lay-grow: when the first column (chart and the text under it) ends above the second, the chart takes the difference.
  function growFigure(flow, fig) {
    var info = inkBoxes(flow), mid = info.w / 2, left = 0, right = 0;
    info.boxes.forEach(function (b) {
      if ((b[0] + b[2]) / 2 < mid) left = Math.max(left, b[3]); else right = Math.max(right, b[3]);
    });
    var fh = fig.getBoundingClientRect().height, gap = right - left;
    if (gap < 12 || gap > fh * 0.5) return;
    fig.classList.add('is-grown');
    fig.style.minHeight = Math.round(fh + gap) + 'px';
  }
  function arrange(flow, name) {
    var fig = flow.querySelector(':scope > .cfig');
    if (fig) { fig.classList.remove('is-grown'); fig.style.minHeight = ''; }
    flow.className = 'cs-flow' + (name ? ' ' + name : '');
    var units = unitsOf(flow);
    if (name.indexOf('lay-mason') >= 0) pack(flow, units);
    else units.forEach(function (u) { u.style.gridColumn = ''; u.style.gridRow = ''; });
    if (fig && name.indexOf('lay-grow') >= 0) growFigure(flow, fig);
    return emptyHeight(inkBoxes(flow)) + (tableSplit(flow) ? 5000 : 0);
  }
  function layoutSection(sec) {
    var flow = sec.querySelector(':scope > .cs-flow');
    if (!flow) return;
    if (!WIDE.matches) {
      flow.className = 'cs-flow';
      unitsOf(flow).forEach(function (u) { u.style.gridColumn = ''; u.style.gridRow = ''; });
      delete flow.dataset.lay;
      return;
    }
    var hasFig = !!flow.querySelector(':scope > .cfig'), hasTbl = !!flow.querySelector('.cu-tbl');
    var tried = [];
    for (var i = 0; i < LAYOUTS.length; i++) {
      var name = LAYOUTS[i];
      if (((!hasFig) && (name.indexOf('lay-span') >= 0 || name.indexOf('lay-grow') >= 0)) || (!hasTbl && name.indexOf('lay-tw') >= 0)) continue;
      var score = arrange(flow, name);
      tried.push({ name: name, score: score, h: flow.getBoundingClientRect().height });
      if (!name && score <= EMPTY_PASS && tried[0].h <= SHORT) break;
    }
    // Among the arrangements that pass, the most compact wins; an arrangement earlier in LAYOUTS (simpler, reading order
    // kept) wins over a later one that is only a little more compact. If none passes, the least empty one is used.
    var ok = tried.filter(function (t) { return t.score <= EMPTY_PASS; }), best;
    if (ok.length) {
      var minH = Math.min.apply(null, ok.map(function (t) { return t.h; }));
      best = ok.filter(function (t) { return t.h <= minH * 1.06 + 12; })[0];
    } else {
      best = tried.reduce(function (a, t) { return t.score < a.score ? t : a; });
    }
    if (best !== tried[tried.length - 1]) arrange(flow, best.name);
    flow.dataset.lay = best.name || 'flat';
    flow.dataset.empty = String(Math.round(best.score));
  }
  function layoutAll() {
    var view = document.getElementById('case-view');
    if (!view || view.hidden || !view.offsetParent) return;
    Array.prototype.forEach.call(view.querySelectorAll('.case-sec'), layoutSection);
  }
  function layoutFor(node) {
    var sec = node.closest('.case-sec');
    if (sec) layoutSection(sec);
  }
  window.__casesLayout = layoutAll;   // for the capture and measuring scripts
  var layoutTimer = 0;
  window.addEventListener('resize', function () {
    clearTimeout(layoutTimer);
    layoutTimer = setTimeout(layoutAll, 120);
  });
  if (document.fonts) {
    if (document.fonts.ready) document.fonts.ready.then(layoutAll);
    if (document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', layoutAll);  // a late web font changes line breaks
  }

  // ---------- chart plumbing ----------
  function barOptions(o) {
    var horiz = o.indexAxis === 'y';
    var valueAxis = {
      stacked: !!o.stacked, beginAtZero: true,
      grid: { color: '#E3E7E6' }, border: { display: false },
      ticks: { color: '#5A6467', font: { size: 12 }, callback: function (v) { return axisMoney(v); }, maxTicksLimit: isNarrow() ? 4 : 6, maxRotation: 0 }
    };
    var catAxis = {
      stacked: !!o.stacked, grid: { display: false }, border: { color: '#0B1113' },
      ticks: { color: '#3E4A4D', font: { size: 12 }, autoSkip: !horiz, maxRotation: horiz ? 0 : 50 }
    };
    return {
      indexAxis: o.indexAxis || 'x',
      responsive: true,
      maintainAspectRatio: false,
      animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 300 },
      datasets: { bar: { maxBarThickness: horiz ? 18 : 34, borderRadius: 2, borderSkipped: 'start' } },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: function (it) { return it.raw !== null; },
          callbacks: { label: o.tooltip, footer: o.footer, title: o.title }
        }
      },
      scales: horiz ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis }
    };
  }
  function hatchPattern(canvas, color) {
    var c = document.createElement('canvas');
    c.width = c.height = 8;
    var x = c.getContext('2d');
    x.fillStyle = '#FFFFFF';
    x.fillRect(0, 0, 8, 8);
    x.strokeStyle = color;
    x.lineWidth = 2;
    x.beginPath();
    x.moveTo(0, 8); x.lineTo(8, 0);
    x.moveTo(-2, 2); x.lineTo(2, -2);
    x.moveTo(6, 10); x.lineTo(10, 6);
    x.stroke();
    return canvas.getContext('2d').createPattern(c, 'repeat');
  }
  function chartFont() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = '#3E4A4D';
  }
  function watch(view) {
    chartFont();
    var cvs = view.querySelectorAll('canvas');
    function build(cv) {
      if (cv.dataset.built === '1' || !cv._build || typeof Chart === 'undefined') return;
      cv.dataset.built = '1';
      charts.push(cv._build());
    }
    if (!('IntersectionObserver' in window)) { cvs.forEach(build); return; }
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { build(en.target); observer && observer.unobserve(en.target); } });
    }, { rootMargin: '200px 0px' });
    cvs.forEach(function (cv) { observer.observe(cv); });
  }
  // for the capture script: build every chart now (the screenshot cannot scroll)
  window.__casesBuildAll = function () {
    document.querySelectorAll('#case-view canvas').forEach(function (cv) {
      if (cv.dataset.built === '1' || !cv._build) return;
      cv.dataset.built = '1';
      charts.push(cv._build());
    });
    return charts.length;
  };
})();
