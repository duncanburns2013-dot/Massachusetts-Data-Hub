/* Explorer tab, "pull the thread": a force layout (d3-force, from the pinned d3 bundle) over data/graph.json.
   Nothing is drawn until a company or official is chosen. Choosing one shows it and its connections (at most 40 per
   expand, "show more" adds 40); selecting a connected node expands it the same way. Edges are summed per pair and
   type through the year on the slider. Clicking or pressing Enter on an edge lists the underlying records from
   data/companies/<company>.json with their source links. A list view mirrors the graph for keyboard and screen
   readers. Colour is never the only cue: each edge type also has its own dash pattern, and nodes differ by shape.
   URL parameters: ?tab=explorer&node=<id>&year=<yyyy>&view=list */
(function () {
  'use strict';

  var TYPES = ['penalty', 'contract', 'donation', 'lobbying', 'holding'];
  var TYPE = {
    penalty: { name: 'Penalty', plural: 'Penalties', color: '#A81733', dash: '' },
    contract: { name: 'State payment', plural: 'State payments', color: '#14558F', dash: '12 5' },
    donation: { name: 'Employee donation', plural: 'Employee donations', color: '#388557', dash: '1.5 4' },
    lobbying: { name: 'Lobbying', plural: 'Lobbying', color: '#B07C20', dash: '9 4 2 4' },
    holding: { name: 'Disclosed tie', plural: 'Disclosed ties', color: '#D0559A', dash: '5 3' }
  };
  var NODE_KIND = { company: 'Company or institution', official: 'Official or committee', agency: 'Agency',
    payer: 'Payer', firm: 'Lobbying firm' };
  var CAP = 40;
  var FIRST = 2010;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  var G = null;          // graph.json
  var NODE = {};         // id -> node
  var ADJ = {};          // id -> [edge] raw yearly edges touching the node
  var LAST = FIRST;
  var S = {              // scene state
    year: null, expanded: [], shown: {}, selected: null, view: 'graph', playing: null, edge: null
  };
  var pos = {};          // id -> {x, y, vx, vy, fx, fy} persisted between redraws
  var sim = null, svg = null, gEdges = null, gNodes = null, gLabels = null, W = 800, H = 560;
  var inited = false;
  var cache = {};

  // ---------- formatting ----------
  var usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  var sig3 = new Intl.NumberFormat('en-US', { minimumSignificantDigits: 3, maximumSignificantDigits: 3 });
  var int0 = new Intl.NumberFormat('en-US');
  function money(n) {
    var a = Math.abs(n), s = n < 0 ? '-' : '';
    if (a >= 1e9) return s + '$' + sig3.format(a / 1e9) + 'B';
    if (a >= 1e6) return s + '$' + sig3.format(a / 1e6) + 'M';
    return usd0.format(n);
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function sv(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function $(id) { return document.getElementById(id); }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return 'link'; } }
  function getJSON(url) {
    if (!cache[url]) cache[url] = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
    return cache[url];
  }
  function trim(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '...' : s; }
  function narrow() { return window.innerWidth < 640; }

  // ---------- lifecycle ----------
  window.TAB_INIT = window.TAB_INIT || {};
  window.TAB_CLEANUP = window.TAB_CLEANUP || {};
  TAB_INIT.explorer = function () {
    if (!inited) { inited = true; boot(); } else if (S.expanded.length) { redraw(); }
  };
  TAB_CLEANUP.explorer = function () {
    stopPlay();
    if (sim) { sim.stop(); sim = null; }
    hideTip();
  };

  function boot() {
    legend();
    helpSwatches();
    controls();
    var st = $('ex-status');
    st.textContent = 'Loading the connections file';
    getJSON('data/corporate-ledger/graph.json').then(function (g) {
      G = g;
      g.nodes.forEach(function (n) { NODE[n.id] = n; ADJ[n.id] = []; });
      g.edges.forEach(function (e) {
        ADJ[e.source].push(e); ADJ[e.target].push(e);
        if (e.year > LAST) LAST = e.year;
      });
      var p = new URLSearchParams(location.search);
      var yr = parseInt(p.get('year'), 10);
      S.year = yr >= FIRST && yr <= LAST ? yr : LAST;
      var slider = $('ex-year');
      slider.min = FIRST; slider.max = LAST; slider.value = S.year;
      $('ex-year-min').textContent = FIRST;
      $('ex-year-max').textContent = yl(LAST);
      showYear();
      if (p.get('view') === 'list') setView('list');
      var start = p.get('node');
      if (start && NODE[start]) choose(start);
      else { st.textContent = 'Find a company or official above to start. ' + int0.format(g.nodes.length) + ' names and ' + int0.format(g.edges.length) + ' yearly records are in the data.'; ready(); }
    }).catch(function (e) { st.textContent = 'The connections file did not load (' + e.message + ').'; ready(); });
  }
  function ready() { document.documentElement.dataset.explorerReady = '1'; }

  // ---------- controls ----------
  function legend() {
    var box = $('ex-legend');
    TYPES.forEach(function (t) {
      var s = el('span', 'lg');
      var svgEl = sv('svg', { width: 34, height: 10, 'aria-hidden': 'true' });
      svgEl.appendChild(sv('line', { x1: 1, y1: 5, x2: 33, y2: 5, stroke: TYPE[t].color, 'stroke-width': 3,
        'stroke-dasharray': TYPE[t].dash, 'stroke-linecap': t === 'donation' ? 'round' : 'butt' }));
      s.appendChild(svgEl);
      s.appendChild(document.createTextNode(TYPE[t].plural));
      box.appendChild(s);
    });
    var shapes = [['company', 'Company'], ['official', 'Official or committee'], ['agency', 'Agency, payer or firm']];
    shapes.forEach(function (k) {
      var s = el('span', 'lg');
      var svgEl = sv('svg', { width: 14, height: 14, 'aria-hidden': 'true' });
      svgEl.appendChild(shape(k[0], 7, 7, 5));
      s.appendChild(svgEl);
      s.appendChild(document.createTextNode(k[1]));
      box.appendChild(s);
    });
  }

  // The picture key in "How to read this picture" is drawn from the same TYPE table and shape() as the graph itself.
  function helpSwatches() {
    document.querySelectorAll('#ex-help .ex-sw').forEach(function (sw) {
      if (sw.firstChild) return;
      var t = sw.getAttribute('data-t'), k = sw.getAttribute('data-k');
      if (t) {
        var svgEl = sv('svg', { width: 34, height: 12, 'aria-hidden': 'true' });
        svgEl.appendChild(sv('line', { x1: 1, y1: 6, x2: 33, y2: 6, stroke: TYPE[t].color, 'stroke-width': 3,
          'stroke-dasharray': TYPE[t].dash, 'stroke-linecap': t === 'donation' ? 'round' : 'butt' }));
        sw.appendChild(svgEl);
      } else if (k) {
        var s2 = sv('svg', { width: 16, height: 16, 'aria-hidden': 'true' });
        s2.appendChild(shape(k, 8, 8, 6));
        sw.appendChild(s2);
      }
    });
  }

  function controls() {
    var q = $('ex-q'), lb = $('ex-suggest');
    var matches = [], active = -1;
    function close() { lb.hidden = true; q.setAttribute('aria-expanded', 'false'); q.removeAttribute('aria-activedescendant'); active = -1; }
    function paint() {
      lb.innerHTML = '';
      matches.forEach(function (m, i) {
        var li = el('li', 'opt' + (i === active ? ' on' : ''));
        li.id = 'ex-opt-' + i;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', String(i === active));
        li.appendChild(el('span', '', m.label));
        li.appendChild(el('span', 'opt-k', NODE_KIND[m.type] + ', ' + int0.format(ADJ[m.id].length) + ' yearly records'));
        li.addEventListener('mousedown', function (ev) { ev.preventDefault(); pick(i); });
        lb.appendChild(li);
      });
      lb.hidden = !matches.length;
      q.setAttribute('aria-expanded', String(!!matches.length));
      if (active >= 0) q.setAttribute('aria-activedescendant', 'ex-opt-' + active); else q.removeAttribute('aria-activedescendant');
    }
    function pick(i) { var m = matches[i]; close(); if (m) { q.value = m.label; choose(m.id); } }
    q.addEventListener('input', function () {
      if (!G) return;
      var t = q.value.trim().toLowerCase();
      active = -1;
      if (t.length < 2) { matches = []; paint(); return; }
      var starts = [], has = [];
      G.nodes.forEach(function (n) {
        if (n.type !== 'company' && n.type !== 'official') return;
        var l = n.label.toLowerCase();
        var inEnt = (n.entities || []).some(function (x) { return x.toLowerCase().indexOf(t) >= 0; });
        if (l.indexOf(t) === 0 || n.id === t) starts.push(n); else if (l.indexOf(t) > 0 || inEnt) has.push(n);
      });
      var byDeg = function (a, b) { return ADJ[b.id].length - ADJ[a.id].length; };
      matches = starts.sort(byDeg).concat(has.sort(byDeg)).slice(0, 8);
      paint();
    });
    q.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); if (matches.length) { active = (active + 1) % matches.length; paint(); } }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); if (matches.length) { active = (active - 1 + matches.length) % matches.length; paint(); } }
      else if (ev.key === 'Enter') { ev.preventDefault(); pick(active >= 0 ? active : 0); }
      else if (ev.key === 'Escape') close();
    });
    q.addEventListener('blur', function () { setTimeout(close, 120); });

    $('ex-year').addEventListener('input', function (ev) { stopPlay(); setYear(+ev.target.value); });
    $('ex-prev').addEventListener('click', function () { stopPlay(); setYear(Math.max(FIRST, S.year - 1)); });
    $('ex-next').addEventListener('click', function () { stopPlay(); setYear(Math.min(LAST, S.year + 1)); });
    var play = $('ex-play');
    if (reduce) play.hidden = true;
    play.addEventListener('click', function () { if (S.playing) stopPlay(); else startPlay(); });
    document.querySelectorAll('#ex-viewseg button').forEach(function (b) {
      b.addEventListener('click', function () { setView(b.dataset.view); });
    });
    $('ex-reset').addEventListener('click', function () {
      Object.keys(pos).forEach(function (k) { pos[k].fx = pos[k].fy = null; });
      redraw(true);
    });
    var rt;
    window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { if (S.expanded.length && $('tab-explorer').classList.contains('active')) redraw(); }, 200); });
  }

  function startPlay() {
    if (reduce) return;
    var b = $('ex-play');
    b.textContent = 'Pause';
    b.setAttribute('aria-pressed', 'true');
    if (S.year >= LAST) setYear(FIRST);
    S.playing = setInterval(function () {
      if (S.year >= LAST) { stopPlay(); return; }
      setYear(S.year + 1);
    }, 1100);
  }
  function stopPlay() {
    if (!S.playing) return;
    clearInterval(S.playing);
    S.playing = null;
    var b = $('ex-play');
    b.textContent = 'Play from ' + FIRST;
    b.setAttribute('aria-pressed', 'false');
  }
  function setYear(y) {
    S.year = y;
    $('ex-year').value = y;
    showYear();
    if (S.expanded.length) redraw();
  }
  // A year after the current calendar year can only be a fiscal year (state payments); say so instead of printing a
  // future year as if it were a date.
  function yl(y) { return y > new Date().getFullYear() ? 'fiscal ' + y : String(y); }
  // State payments are summed by fiscal year; label them so a future fiscal year never reads as a date.
  function yrsText(e) {
    var f = e.type === 'contract' ? function (y) { return 'FY' + y; } : String;
    return e.y0 === e.y1 ? f(e.y0) : f(e.y0) + ' to ' + f(e.y1);
  }
  function showYear() {
    $('ex-year-out').textContent = S.year === LAST ? 'All years, ' + FIRST + ' to ' + yl(LAST) : 'Through ' + yl(S.year);
    $('ex-prev').disabled = S.year <= FIRST;
    $('ex-next').disabled = S.year >= LAST;
  }
  function setView(v) {
    S.view = v;
    document.querySelectorAll('#ex-viewseg button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === v)); });
    $('ex-graph').hidden = v !== 'graph';
    $('ex-list').hidden = v !== 'list';
    if (S.expanded.length) redraw();
  }

  // ---------- model ----------
  // Pairs (other end, type) summed through the slider year. Edges dated 2009 (July to December 2009, the first half of
  // fiscal 2010) count from the first step.
  function pairsOf(id) {
    var m = {};
    ADJ[id].forEach(function (e) {
      if (e.year > S.year) return;
      var other = e.source === id ? e.target : e.source;
      var k = other + '|' + e.type;
      var p = m[k] || (m[k] = { key: [e.source, e.target, e.type].join('|'), source: e.source, target: e.target, other: other,
        type: e.type, amount: 0, n: 0, y0: e.year, y1: e.year });
      p.amount += e.amount; p.n += e.n;
      if (e.year < p.y0) p.y0 = e.year;
      if (e.year > p.y1) p.y1 = e.year;
    });
    var sorted = Object.keys(m).map(function (k) { return m[k]; }).sort(function (a, b) {
      return b.amount - a.amount || b.n - a.n || (NODE[a.other].label < NODE[b.other].label ? -1 : 1);
    });
    // Round-robin across types (largest first within each type), so a cap of 40 never hides a whole type:
    // disclosed ties carry no amount and would otherwise always sort last.
    var byType = {}, out = [];
    sorted.forEach(function (p) { (byType[p.type] = byType[p.type] || []).push(p); });
    for (var i = 0; out.length < sorted.length; i++) {
      TYPES.forEach(function (t) { if (byType[t] && byType[t][i]) out.push(byType[t][i]); });
    }
    return out;
  }
  function scene() {
    var nodes = {}, edges = {}, more = [];
    S.expanded.forEach(function (id) {
      nodes[id] = true;
      var ps = pairsOf(id);
      var k = S.shown[id] || CAP;
      ps.slice(0, k).forEach(function (p) { nodes[p.other] = true; edges[p.key] = p; });
      if (ps.length > k) more.push({ id: id, left: ps.length - k, total: ps.length });
      S.total = S.total || {};
      S.total[id] = ps.length;
    });
    return { nodes: Object.keys(nodes), edges: Object.keys(edges).map(function (k) { return edges[k]; }), more: more };
  }

  function choose(id) {
    S.expanded = [id];
    S.shown = {};
    S.selected = id;
    S.edge = null;
    pos = {};
    $('ex-records').hidden = true;
    var url = new URL(location.href);
    url.searchParams.set('tab', 'explorer');
    url.searchParams.set('node', id);
    history.replaceState(null, '', url);
    redraw(true);
  }
  function expand(id) {
    S.selected = id;
    if (S.expanded.indexOf(id) < 0) S.expanded.push(id);
    redraw(true);
  }

  // ---------- drawing ----------
  function redraw(reheat) {
    var sc = scene();
    status(sc);
    moreButtons(sc);
    list(sc);
    if (S.view === 'graph') draw(sc, reheat); else if (sim) sim.stop();
    ready();
  }

  function status(sc) {
    var root = S.expanded[0];
    var parts = [];
    S.expanded.forEach(function (id) {
      var shown = Math.min(S.shown[id] || CAP, S.total[id]);
      parts.push(NODE[id].label + ': ' + shown + ' of ' + S.total[id] + ' connections shown');
    });
    var byType = {};
    sc.edges.forEach(function (e) { byType[e.type] = (byType[e.type] || 0) + 1; });
    var tl = TYPES.filter(function (t) { return byType[t]; }).map(function (t) { return byType[t] + ' ' + (byType[t] === 1 ? TYPE[t].name : TYPE[t].plural).toLowerCase(); });
    $('ex-status').textContent = parts.join('. ') + (S.year < LAST ? ', through ' + S.year : '') + '. ' +
      (sc.edges.length ? 'Lines on screen: ' + tl.join(', ') + '.' : 'No connections on record through ' + S.year + '.');
    var ib = $('ex-incl');
    if (ib) {
      ib.innerHTML = '';
      if (S.view === 'graph') S.expanded.forEach(function (id) { var p = inclP(id); if (p) ib.appendChild(p); });
    }
    $('ex-status').dataset.edges = sc.edges.length;
    $('ex-status').dataset.root = root || '';
  }

  // A company node that groups several defendant entities says so (graph.json company nodes carry entities).
  function inclP(id) {
    var nd = NODE[id];
    if (!nd || !nd.entities || nd.entities.length < 2) return null;
    var p = el('p', 'ex-incl', 'Includes: ' + nd.entities.join('; ') + '. ' + (nd.entities_note || ''));
    p.title = nd.entities_note || '';
    return p;
  }

  function moreButtons(sc) {
    var box = $('ex-more');
    box.innerHTML = '';
    sc.more.forEach(function (m) {
      var b = el('button', 'more', 'Show ' + Math.min(CAP, m.left) + ' more names connected to ' + NODE[m.id].label + ' (' + m.left + ' more not drawn yet)');
      b.type = 'button';
      b.addEventListener('click', function () { S.shown[m.id] = (S.shown[m.id] || CAP) + CAP; redraw(true); });
      box.appendChild(b);
    });
    S.expanded.forEach(function (id) {
      if ((S.shown[id] || CAP) > CAP) {
        var b = el('button', 'more', 'Show fewer of ' + NODE[id].label + "'s connections");
        b.type = 'button';
        b.addEventListener('click', function () { S.shown[id] = CAP; redraw(true); });
        box.appendChild(b);
      }
    });
  }

  function shape(type, x, y, r, extra) {
    var s;
    if (type === 'company') s = sv('circle', { cx: x, cy: y, r: r, class: 'n-co' });
    else if (type === 'official') s = sv('circle', { cx: x, cy: y, r: r, class: 'n-of' });
    else s = sv('rect', { x: x - r, y: y - r, width: 2 * r, height: 2 * r, rx: 1.5, class: 'n-ag' });
    if (extra) s.setAttribute('class', s.getAttribute('class') + ' ' + extra);
    return s;
  }

  function draw(sc, reheat) {
    var box = $('ex-graph');
    W = box.clientWidth || 800;
    H = narrow() ? 460 : 580;
    if (!svg) {
      svg = sv('svg', { class: 'ex-svg', role: 'group', 'aria-label': 'Connections graph. The list view holds the same connections as text.' });
      gEdges = sv('g', {}); gNodes = sv('g', {}); gLabels = sv('g', { 'aria-hidden': 'true' });
      svg.appendChild(gEdges); svg.appendChild(gLabels); svg.appendChild(gNodes);
      box.appendChild(svg);
    }
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);

    var maxA = 0;
    sc.edges.forEach(function (e) { if (e.amount > maxA) maxA = e.amount; });
    var nodes = sc.nodes.map(function (id) {
      var p = pos[id];
      if (!p) {
        var anchor = null;
        sc.edges.some(function (e) { if (e.other === id && pos[e.source === id ? e.target : e.source]) { anchor = pos[e.source === id ? e.target : e.source]; return true; } return false; });
        var a = Math.random() * Math.PI * 2;
        p = pos[id] = anchor ? { x: anchor.x + Math.cos(a) * 60, y: anchor.y + Math.sin(a) * 60 } : { x: W / 2 + Math.cos(a) * 20, y: H / 2 + Math.sin(a) * 20 };
      }
      p.id = id;
      return p;
    });
    if (S.expanded.length === 1 && pos[S.expanded[0]] && pos[S.expanded[0]].fx == null) {
      pos[S.expanded[0]].x = W / 2; pos[S.expanded[0]].y = H / 2;
    }
    var links = sc.edges.map(function (e) { return { source: e.source, target: e.target, e: e }; });

    // edges
    gEdges.innerHTML = '';
    var linkEls = links.map(function (l) {
      var e = l.e, t = TYPE[e.type];
      var w = e.amount > 0 && maxA > 0 ? 1.5 + 6 * Math.sqrt(e.amount / maxA) : 1.5;
      var g = sv('g', { class: 'edge' + (S.edge === e.key ? ' on' : ''), tabindex: 0, role: 'button',
        'aria-label': edgeText(e).join('. ') + '. Press Enter to list the records.' });
      var hit = sv('line', { class: 'e-hit' });
      var line = sv('line', { class: 'e-line', stroke: t.color, 'stroke-width': w.toFixed(2),
        'stroke-dasharray': t.dash, 'stroke-linecap': e.type === 'donation' ? 'round' : 'butt' });
      g.appendChild(hit); g.appendChild(line);
      g.addEventListener('pointerenter', function (ev) { tip(edgeText(e), ev.clientX, ev.clientY); });
      g.addEventListener('pointermove', function (ev) { tip(edgeText(e), ev.clientX, ev.clientY); });
      g.addEventListener('pointerleave', hideTip);
      g.addEventListener('focus', function () { var r = line.getBoundingClientRect(); tip(edgeText(e), r.left + r.width / 2, r.top + r.height / 2); });
      g.addEventListener('blur', hideTip);
      g.addEventListener('click', function () { openRecords(e); });
      g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openRecords(e); } });
      gEdges.appendChild(g);
      return { g: g, hit: hit, line: line, l: l };
    });

    // nodes and labels
    gNodes.innerHTML = '';
    gLabels.innerHTML = '';
    var labelled = labelSet(sc);
    var nodeEls = nodes.map(function (n) {
      var nd = NODE[n.id];
      var isExp = S.expanded.indexOf(n.id) >= 0;
      var r = isExp ? 10 : nd.type === 'company' ? 7 : 5.5;
      var g = sv('g', { class: 'node' + (isExp ? ' exp' : '') + (S.selected === n.id ? ' sel' : ''), tabindex: 0, role: 'button',
        'aria-label': nd.label + ', ' + NODE_KIND[nd.type] + (isExp ? ', expanded' : '. Press Enter to show its connections.') });
      g.appendChild(sv('circle', { r: 16, class: 'n-hit' }));
      g.appendChild(shape(nd.type, 0, 0, r));
      var lab = null;
      if (labelled[n.id]) {
        lab = sv('text', { class: 'n-lab' + (isExp ? ' exp' : ''), 'text-anchor': 'middle', dy: -(r + 5) });
        lab.textContent = trim(nd.label, isExp ? 40 : 26);
        gLabels.appendChild(lab);
      }
      g.addEventListener('pointerenter', function (ev) { tip([nd.label, NODE_KIND[nd.type] + ': ' + int0.format(ADJ[n.id].length) + ' yearly records in the data. Select to open its connections.'], ev.clientX, ev.clientY); });
      g.addEventListener('pointerleave', hideTip);
      g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); expand(n.id); } });
      g.addEventListener('focus', function () { var b = g.getBoundingClientRect(); tip([nd.label, NODE_KIND[nd.type]], b.left + b.width / 2, b.top); });
      g.addEventListener('blur', hideTip);
      dragNode(g, n);
      gNodes.appendChild(g);
      return { g: g, n: n, lab: lab };
    });

    function tick() {
      nodes.forEach(function (n) {
        n.x = Math.max(14, Math.min(W - 14, n.x));
        n.y = Math.max(20, Math.min(H - 12, n.y));
      });
      linkEls.forEach(function (o) {
        var s = o.l.source, t = o.l.target;
        [o.hit, o.line].forEach(function (ln) {
          ln.setAttribute('x1', s.x.toFixed(1)); ln.setAttribute('y1', s.y.toFixed(1));
          ln.setAttribute('x2', t.x.toFixed(1)); ln.setAttribute('y2', t.y.toFixed(1));
        });
      });
      nodeEls.forEach(function (o) {
        o.g.setAttribute('transform', 'translate(' + o.n.x.toFixed(1) + ',' + o.n.y.toFixed(1) + ')');
        if (o.lab) { o.lab.setAttribute('x', o.n.x.toFixed(1)); o.lab.setAttribute('y', o.n.y.toFixed(1)); }
      });
    }

    if (sim) sim.stop();
    var dist = Math.max(70, Math.min(W, H) * (narrow() ? 0.3 : 0.34));
    sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(function (d) { return d.id; }).distance(function (l) {
        return S.expanded.indexOf(l.source.id || l.source) >= 0 && S.expanded.indexOf(l.target.id || l.target) >= 0 ? dist * 1.6 : dist;
      }).strength(0.7))
      .force('charge', d3.forceManyBody().strength(narrow() ? -110 : -220))
      .force('collide', d3.forceCollide(narrow() ? 9 : 13))
      .force('x', d3.forceX(W / 2).strength(0.04))
      .force('y', d3.forceY(H / 2).strength(narrow() ? 0.09 : 0.06))
      .on('tick', tick);
    if (reduce) { sim.stop(); for (var i = 0; i < 300; i++) sim.tick(); tick(); }
    else { sim.alpha(reheat ? 0.9 : 0.35).restart(); }
    S.sim = sim;
  }

  // Which nodes carry a visible name: always the expanded ones; on wider screens also the largest few connections.
  function labelSet(sc) {
    var on = {};
    S.expanded.forEach(function (id) { on[id] = true; });
    if (narrow()) return on;
    // the two largest connections of each type
    TYPES.forEach(function (t) {
      var k = 0;
      sc.edges.filter(function (e) { return e.type === t; }).sort(function (a, b) { return b.amount - a.amount || b.n - a.n; })
        .forEach(function (e) { if (k < 2 && !on[e.other]) { on[e.other] = true; k++; } });
    });
    return on;
  }

  function dragNode(g, n) {
    var start = null;
    g.addEventListener('pointerdown', function (ev) {
      if (ev.button !== 0) return;
      start = { x: ev.clientX, y: ev.clientY, moved: false };
      g.setPointerCapture(ev.pointerId);
      hideTip();
    });
    g.addEventListener('pointermove', function (ev) {
      if (!start) return;
      if (!start.moved && Math.hypot(ev.clientX - start.x, ev.clientY - start.y) < 4) return;
      start.moved = true;
      var pt = svgPoint(ev);
      n.fx = pt.x; n.fy = pt.y;
      if (sim) sim.alphaTarget(0.25).restart();
    });
    function end(ev) {
      if (!start) return;
      var moved = start.moved;
      start = null;
      if (sim) sim.alphaTarget(0);
      if (reduce && sim && moved) { sim.stop(); for (var i = 0; i < 60; i++) sim.tick(); }
      if (!moved && ev.type === 'pointerup') expand(n.id);
    }
    g.addEventListener('pointerup', end);
    g.addEventListener('pointercancel', end);
  }
  function svgPoint(ev) {
    var r = svg.getBoundingClientRect();
    return { x: (ev.clientX - r.left) * W / r.width, y: (ev.clientY - r.top) * H / r.height };
  }

  // ---------- tooltip ----------
  function edgeText(e) {
    var co = NODE[e.source].label, other = NODE[e.target].label;
    var yrs = yrsText(e);
    var amt = e.type === 'holding' ? '' : money(e.amount) + ', ';
    // a donation line is a gift by individuals who report the company as employer, never a company-to-official payment
    var head = e.type === 'donation' ? 'Employee donations: employees of ' + co + ' to ' + other : TYPE[e.type].name + ': ' + co + ' and ' + other;
    return [head, yrs, amt + int0.format(e.n) + (e.n === 1 ? ' record' : ' records')];
  }
  function tip(lines, x, y) {
    var t = $('ex-tip');
    t.innerHTML = '';
    lines.forEach(function (l, i) { t.appendChild(el(i ? 'span' : 'strong', '', l)); });
    t.hidden = false;
    var r = t.getBoundingClientRect();
    var left = Math.min(window.innerWidth - r.width - 8, Math.max(8, x + 12));
    var top = y - r.height - 12 < 8 ? y + 16 : y - r.height - 12;
    t.style.left = left + 'px';
    t.style.top = top + 'px';
  }
  function hideTip() { var t = $('ex-tip'); if (t) t.hidden = true; }

  // ---------- list view (mirrors the graph) ----------
  function list(sc) {
    var box = $('ex-list');
    box.innerHTML = '';
    S.expanded.forEach(function (id) {
      var sec = el('section', 'xl-node');
      var h = el('h3', '', NODE[id].label);
      sec.appendChild(h);
      var ip = inclP(id);
      if (ip) sec.appendChild(ip);
      sec.appendChild(el('p', 'muted', NODE_KIND[NODE[id].type] + '. ' + Math.min(S.shown[id] || CAP, S.total[id]) + ' of ' + S.total[id] + ' connections listed' + (S.year < LAST ? ', through ' + S.year : '') + '.'));
      var mine = sc.edges.filter(function (e) { return e.source === id || e.target === id; });
      TYPES.forEach(function (t) {
        var es = mine.filter(function (e) { return e.type === t; }).sort(function (a, b) { return b.amount - a.amount || b.n - a.n; });
        if (!es.length) return;
        var tsum = 0;
        es.forEach(function (e) { tsum += e.amount; });
        var gh = el('h4', '');
        var sw = el('span', 'xl-sw');
        sw.style.setProperty('--c', TYPE[t].color);
        sw.style.setProperty('--d', t === 'penalty' ? 'solid' : t === 'donation' ? 'dotted' : 'dashed');
        gh.appendChild(sw);
        gh.appendChild(document.createTextNode(TYPE[t].plural + ' (' + es.length + (t === 'holding' ? '' : ', ' + money(tsum)) + ')'));
        sec.appendChild(gh);
        var ul = el('ul', 'xl');
        es.forEach(function (e) {
          var li = el('li');
          var o = e.other === id ? (e.source === id ? e.target : e.source) : e.other;
          var name = el('button', 'xl-name', NODE[o].label);
          name.type = 'button';
          name.title = S.expanded.indexOf(o) >= 0 ? 'Already expanded' : 'Show its connections';
          name.addEventListener('click', function () { expand(o); });
          li.appendChild(name);
          var yrs = yrsText(e);
          li.appendChild(el('span', 'xl-meta mono', (t === 'holding' ? '' : money(e.amount) + ', ') + e.n + (e.n === 1 ? ' record, ' : ' records, ') + yrs));
          var rb = el('button', 'xl-rec', 'Records');
          rb.type = 'button';
          rb.setAttribute('aria-label', 'Records for ' + edgeText(e)[0]);
          rb.addEventListener('click', function () { openRecords(e); });
          li.appendChild(rb);
          ul.appendChild(li);
        });
        sec.appendChild(ul);
      });
      box.appendChild(sec);
    });
  }

  // ---------- records behind an edge ----------
  var norm = function (s) { return String(s).toUpperCase().replace(/&/g, ' AND ').replace(/[^A-Z0-9]+/g, ' ').trim(); };
  function itemYear(it) {
    if (it.stream === 'contract') { var m = /\(FY(\d{4}), /.exec(it.label); return m ? +m[1] : +it.date.slice(0, 4); }
    return +it.date.slice(0, 4);
  }
  function matcher(e, loose) {
    var other = NODE[e.target], tid = e.target;
    return function (it) {
      if (it.stream !== e.type) return false;
      var y = itemYear(it);
      if (y > S.year || y < e.y0 || y > e.y1) return false;
      var L = it.label;
      switch (e.type) {
        case 'penalty': return L.indexOf(tid.replace(/^agency:/, '') + ' ') === 0;
        case 'contract': var cm = /\(FY\d{4}, ([A-Z]+)\)$/.exec(L); return !!cm && cm[1] === tid.replace(/^payer:/, '');
        case 'donation':
          if ((it.detail.indexOf('FEC') === 0) !== /^rec:C/.test(tid)) return false;
          L = L.split('; employer ')[0];
          return loose ? L.split(' (')[0] === other.label.split(' (')[0] : L === other.label;
        case 'lobbying':
          var f = L.slice(L.lastIndexOf(' to ') + 4);
          if (tid === 'in-house') return f === 'in-house';
          var nf = norm(f), nid = norm(tid.replace(/^firm:/, ''));
          return nf === norm(other.label) || nf === nid || (loose && (nf + ' ').indexOf(nid + ' ') === 0);
        case 'holding': return it.detail.indexOf(other.label + ';') === 0;
      }
      return false;
    };
  }
  function openRecords(e) {
    S.edge = e.key;
    document.querySelectorAll('#ex-graph .edge').forEach(function (g) { g.classList.remove('on'); });
    var box = $('ex-records');
    box.hidden = false;
    box.innerHTML = '';
    var h = el('h3', '', edgeText(e)[0]);
    h.tabIndex = -1;
    box.appendChild(h);
    box.appendChild(el('p', 'muted', edgeText(e).slice(1).join(', ') + (S.year < LAST ? ', through ' + S.year : '') + '.'));
    var body = el('div', '', 'Loading records');
    box.appendChild(body);
    box.scrollIntoView({ block: 'nearest' });
    h.focus({ preventScroll: true });
    getJSON('data/corporate-ledger/companies/' + e.source + '.json').then(function (c) {
      var items = c.items.filter(matcher(e, false));
      var counted = function (it) { return !(e.type === 'penalty' && /Not counted in the total/.test(it.detail)); };
      var sum = function (xs) { return xs.filter(counted).reduce(function (s, it) { return s + it.amount; }, 0); };
      if (items.filter(counted).length !== e.n || Math.abs(sum(items) - e.amount) > 0.5) {
        var loose = c.items.filter(matcher(e, true));
        if (loose.filter(counted).length === e.n && Math.abs(sum(loose) - e.amount) <= 0.5) items = loose;
      }
      items.sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
      body.innerHTML = '';
      var nOk = items.filter(counted).length;
      if (nOk !== e.n || Math.abs(sum(items) - e.amount) > 0.5) {
        body.appendChild(el('p', 'cfig-warn', 'The company file lists records by name, not by committee or firm number, so this list (' +
          nOk + ' records, ' + money(sum(items)) + ') does not exactly match the connection (' + e.n + ' records, ' + money(e.amount) +
          '). A committee or firm with the same name may be mixed in.'));
      }
      var ol = el('ol', 'events');
      items.forEach(function (it) {
        var li = el('li', 'ev s-' + it.stream);
        li.appendChild(el('time', '', it.date));
        var chip = el('span', 'chip s-' + it.stream);
        chip.appendChild(el('span', 'sw'));
        chip.appendChild(document.createTextNode(TYPE[it.stream].name.toLowerCase()));
        li.appendChild(chip);
        li.appendChild(el('span', 'amt', it.stream === 'holding' ? '' : money(it.amount)));
        var what = el('span', 'what');
        what.appendChild(el('b', '', it.label));
        var det = el('span', 'det', it.detail + (counted(it) ? '' : ' (not in this connection\'s sum)'));
        what.appendChild(det);
        li.appendChild(what);
        var src = el('span', 'src');
        if (/^https?:\/\//i.test(it.source_url || '')) {
          var a = el('a', '', 'Source: ' + host(it.source_url));
          a.href = it.source_url;
          a.rel = 'noopener';
          src.appendChild(a);
        } else src.textContent = 'Source: not linked';
        li.appendChild(src);
        ol.appendChild(li);
      });
      if (!items.length) body.appendChild(el('p', 'muted', 'No matching records were found in the company file.'));
      body.appendChild(ol);
    }).catch(function (err) { body.textContent = 'The company file did not load (' + err.message + ').'; });
  }
})();
