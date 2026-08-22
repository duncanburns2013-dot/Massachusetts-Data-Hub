# -*- coding: utf-8 -*-
"""Build the About page.

Everything asserted here was read from a source rather than assumed. The bio
facts come from the Bentley's Real Estate team page; the column titles and the
2016-2026 span come from the Valley Patriot author archive; the refresh
cadences come from the cron lines in this repository's own workflows. LinkedIn
returns 999 to any automated client, so that link is published without being
read - it is a link, not a citation.
"""
import io, re

NL = chr(10)

BODY = '''
    <h1>About</h1>
    <span class="ramp" aria-hidden="true"></span>

    <p class="panel-lede">Massachusetts Data Hub is a public record of what the
    Commonwealth charges, spends and reports &mdash; assembled from primary
    government sources and published so anyone can check the arithmetic.</p>

    <section class="abio rv">
      <a class="abio-facelink" href="assets/duncan-burns.jpg"
         aria-label="Enlarge the portrait of Duncan Burns">
        <img class="abio-face" src="assets/duncan-burns.jpg" width="400" height="400"
             alt="Duncan Burns" loading="eager" fetchpriority="high" decoding="async">
      </a>
      <div class="abio-text">
        <h2>Duncan Burns</h2>
        <p>A U.S. Air Force veteran and UMass graduate. Operations Manager at
        Bentley&rsquo;s Real Estate in Greater Newburyport, where ten years of
        marketing, compliance and training sit behind a brokerage that has held
        first place in its market for seven consecutive years, took Essex County
        in 2022, and appears in <em>The Wall Street Journal</em>&rsquo;s
        REALTRENDS &ldquo;The Thousand&rdquo;. A licensed Massachusetts real
        estate agent and Notary Public.</p>
        <p>He has written op-eds for <em>The Valley Patriot</em> since 2016 and
        took its Editor&rsquo;s Choice Award that year. A North Shore native, he
        lives in the Merrimack Valley.</p>
      </div>
    </section>

    <blockquote class="acreed rv">
      <p>I believe in liberty, and there can&rsquo;t be liberty without an equal
      rule of law. I built this data hub of public information to use as a shield
      and a sword against the enemies within.</p>
      <p>Information like this should always be free, and the public should always
      have access to it as a means to keep checks and balances upon their own
      government. Unfortunately for Massachusetts residents, our government has
      made Massachusetts the most opaque, and arguably the most corrupt
      (pay-to-play), in the nation.</p>
      <cite>Duncan Burns</cite>
    </blockquote>

    <h2 class="asub rv">This started in print</h2>
    <p class="panel-body rv">The questions on this site are not new ones. They ran
    in <em>The Valley Patriot</em> first, and the dashboards exist because a
    column can make an argument but cannot show you the arithmetic.</p>
    <ul class="acols rv">
      <li>How Beacon Hill Is Bankrupting the Merrimack Valley</li>
      <li>H-1B Foreign Workers Are Destroying Merrimack Valley Economy</li>
      <li>Akamai Uses Tax Breaks to Hire H1B Foreign Workers</li>
      <li>The Battle of Unequitable Liberty in Massachusetts</li>
    </ul>
    <p class="panel-note rv"><a href="https://valleypatriot.com/category/op-eds-editorials/duncan-burns/"
       target="_blank" rel="noopener">The full archive, 2016 to 2026 &nearr;</a></p>

    <h2 class="asub rv">How the figures are handled</h2>
    <p class="panel-body rv">Every figure is traceable. Nothing is modelled,
    estimated or smoothed unless the dashboard says so in plain language and
    names the method. Where two official sources disagree, both are shown rather
    than averaged. The instrument on the front page carries all 351
    municipalities at their real geometry; the dashboards behind it hold the
    detail, each with its own source vintage.</p>

    <h2 class="asub rv">And how they stay current</h2>
    <p class="panel-body rv">There is no site-wide &ldquo;updated&rdquo; date,
    because one would only tell you when a script last ran. Nine pipelines
    refresh on their own clocks, matched to when each source actually publishes.</p>
    <div class="feeds rv">
      <div class="feed-group">
        <div class="feed-axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div>
        <ul>
          <li><b>MLS figures</b><span class="ftrack" aria-hidden="true"><i style="left:29.2%"></i></span><em>daily, 07:00</em></li>
          <li><b>New Hampshire figures</b><span class="ftrack" aria-hidden="true"><i style="left:30.6%"></i></span><em>daily, 07:20</em></li>
          <li><b>This site redeploys</b><span class="ftrack" aria-hidden="true"><i style="left:0%"></i><i style="left:12.5%"></i><i style="left:25%"></i><i style="left:37.5%"></i><i style="left:50%"></i><i style="left:62.5%"></i><i style="left:75%"></i><i style="left:87.5%"></i></span><em>every 3 hours</em></li>
        </ul>
      </div>
      <div class="feed-group">
        <div class="feed-axis"><span>1st</span><span>8th</span><span>15th</span><span>22nd</span><span>31st</span></div>
        <ul>
          <li><b>IRS SOI migration</b><span class="ftrack" aria-hidden="true"><i style="left:0%"></i></span><em>1st</em></li>
          <li><b>Energy</b><span class="ftrack" aria-hidden="true"><i style="left:3.3%"></i><i style="left:83.3%"></i></span><em>2nd and 26th</em></li>
          <li><b>Consumer prices</b><span class="ftrack" aria-hidden="true"><b class="fspan" style="left:30%;width:20%"></b></span><em>10th&ndash;16th</em></li>
          <li><b>Employment</b><span class="ftrack" aria-hidden="true"><b class="fspan" style="left:0%;width:20%"></b><b class="fspan" style="left:46.7%;width:20%"></b></span><em>the Friday in each window</em></li>
          <li><b>Census ACS</b><span class="ftrack" aria-hidden="true"><i style="left:63.3%"></i></span><em>20th</em></li>
          <li><b>CBP encounters</b><span class="ftrack" aria-hidden="true"><i style="left:80%"></i></span><em>25th</em></li>
        </ul>
      </div>
    </div>
    <p class="panel-note rv">Built and maintained in the open. The full source, the
    data files and every revision are in the
    <a href="https://github.com/duncanburns2013-dot/Massachusetts-Data-Hub"
       target="_blank" rel="noopener">GitHub repository</a>.</p>
'''

CSS = """
/* ---- About ---------------------------------------------------------------
   Same head treatment as Videos: centred, heavier, with a warm-to-cool wash
   across the top of the panel. The bio is the one block set left, because a
   portrait beside centred ragged text reads as an accident. */
.doc-in{position:relative;overflow:hidden;text-align:center}
.doc-in::before{content:'';position:absolute;left:0;right:0;top:0;height:270px;
  pointer-events:none;z-index:0;
  background:radial-gradient(78% 120% at 6% 0%,rgba(104,10,29,.11),transparent 62%),
             radial-gradient(72% 120% at 94% 4%,rgba(20,85,143,.12),transparent 60%)}
.doc-in > *{position:relative;z-index:1}
.doc h1{justify-content:center;font-size:clamp(34px,5vw,72px)}
.doc .ramp{height:3px;margin:20px auto 26px;max-width:none}
.doc .panel-lede{font-size:clamp(17px,1.5vw,24px);line-height:1.45;max-width:none}
.doc .panel-body{max-width:none;font-size:15px;line-height:1.72}
.doc .panel-note{max-width:none;font-size:13px;line-height:1.65}

/* His words, and they should not look like the rest of the page, which is
   written about him rather than by him. */
.acreed{margin:26px 0 0;padding:24px clamp(20px,2.6vw,34px);text-align:left;
  border-radius:16px;border:1px solid rgba(104,10,29,.22);
  background:linear-gradient(180deg,rgba(104,10,29,.055),rgba(104,10,29,.02))}
.acreed p{font-family:var(--font-display);font-weight:400;
  font-size:clamp(16px,1.55vw,22px);line-height:1.5;letter-spacing:-.012em;
  color:rgba(11,17,19,.90);margin:0 0 14px;max-width:74ch}
.acreed p:last-of-type{margin-bottom:16px}
.acreed cite{display:block;font-family:var(--font-mono);font-style:normal;
  font-size:11px;font-weight:700;letter-spacing:.17em;text-transform:uppercase;
  color:var(--cranberry)}
.acreed cite::before{content:"— "}
.asub{font-family:var(--font-display);font-weight:700;letter-spacing:-.02em;
  font-size:clamp(17px,1.6vw,23px);color:var(--ink);margin:40px 0 10px;
  padding-top:22px;border-top:1px solid rgba(11,17,19,.10)}

.abio{display:grid;grid-template-columns:180px 1fr;gap:clamp(20px,2.6vw,34px);
  align-items:start;text-align:left;margin:30px 0 4px;padding:24px clamp(18px,2.2vw,28px);
  border-radius:16px;background:rgba(255,255,255,.55);
  border:1px solid rgba(11,17,19,.07)}
.abio-face{width:180px;height:180px;border-radius:14px;object-fit:cover;display:block;
  box-shadow:0 6px 22px rgba(11,17,19,.16)}
.abio-facelink{display:block;width:180px;border-radius:14px;cursor:zoom-in;
  transition:transform .35s cubic-bezier(.19,1,.22,1),box-shadow .35s}
.abio-facelink:hover{transform:scale(1.03)}
.abio-facelink:focus-visible{outline:2px solid var(--bay-blue);outline-offset:3px}
/* `hidden` is display:none from the UA sheet and a class beats it, so
   without this the overlay stays laid out and eats every click */
.lbox[hidden]{display:none}
.lbox{position:fixed;inset:0;z-index:90;display:flex;align-items:center;
  justify-content:center;padding:24px;opacity:0;transition:opacity .2s;
  background:rgba(6,9,11,.74);backdrop-filter:blur(6px);
  -webkit-backdrop-filter:blur(6px);cursor:zoom-out}
.lbox.on{opacity:1}
/* capped at the source's own 400px: enlarging past that would only show
   the compression, and the studio frame exists at no larger size */
.lbox img{width:min(400px,82vw);height:auto;border-radius:16px;display:block;
  box-shadow:0 24px 70px rgba(0,0,0,.55);transform:scale(.96);
  transition:transform .25s cubic-bezier(.19,1,.22,1)}
.lbox.on img{transform:scale(1)}
.lbox-x{position:absolute;top:18px;right:20px;width:40px;height:40px;
  border-radius:10px;border:1px solid rgba(255,255,255,.28);cursor:pointer;
  background:rgba(255,255,255,.10);color:#fff;font-size:24px;line-height:1;
  transition:background .2s}
.lbox-x:hover{background:rgba(255,255,255,.2)}
@media (prefers-reduced-motion: reduce){
  .abio-facelink,.lbox,.lbox img{transition:none}
  .abio-facelink:hover{transform:none} .lbox img{transform:none}}
.abio-text h2{font-family:var(--font-display);font-weight:700;letter-spacing:-.025em;
  font-size:clamp(21px,2vw,30px);color:var(--cranberry);margin:0 0 10px}
.abio-text p{font-family:var(--font-text);font-size:14.5px;line-height:1.68;
  color:rgba(11,17,19,.84);margin:0 0 10px}

.acols{list-style:none;margin:14px auto 0;padding:0;display:grid;gap:8px;
  grid-template-columns:repeat(auto-fit,minmax(330px,1fr));text-align:left}
.acols li{font-family:var(--font-text);font-size:14px;line-height:1.45;
  color:rgba(11,17,19,.84);padding:11px 14px;border-radius:10px;
  background:rgba(255,255,255,.5);border:1px solid rgba(11,17,19,.10)}


/* ---- the refresh schedule, drawn rather than listed ---------------------
   Nine pipelines on nine different clocks is the actual argument for having no
   single site-wide "updated" date, and a list of times does not show it. Each
   track is one cycle - a day on the first group, a month on the second - with a
   mark where that feed fires. The rhythm is the point. */
.feeds{margin:18px 0 0;text-align:left;display:grid;gap:18px}
.feed-group{padding:14px 16px 6px;border-radius:12px;
  background:rgba(255,255,255,.5);border:1px solid rgba(11,17,19,.07)}
.feed-axis{display:flex;justify-content:space-between;margin:0 0 8px;
  padding-left:min(38%,190px);font-family:var(--font-mono);font-size:11px;
  letter-spacing:.06em;color:rgba(11,17,19,.45)}
.feed-group ul{list-style:none;margin:0;padding:0}
.feed-group li{display:grid;grid-template-columns:min(38%,190px) 1fr auto;
  align-items:center;gap:12px;padding:7px 0;border-top:1px solid rgba(11,17,19,.06)}
.feed-group li:first-child{border-top:0}
.feed-group li>b{font-family:var(--font-text);font-size:13.5px;font-weight:500;
  color:rgba(11,17,19,.86)}
.feed-group li>em{font-family:var(--font-mono);font-style:normal;font-size:11px;
  font-weight:600;color:var(--bay-blue);white-space:nowrap}
.ftrack{position:relative;display:block;height:14px;border-radius:7px;
  background:linear-gradient(90deg,rgba(11,17,19,.05),rgba(11,17,19,.09))}
.ftrack::after{content:'';position:absolute;left:0;right:0;top:50%;height:1px;
  background:rgba(11,17,19,.10)}
.ftrack i{position:absolute;top:50%;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;
  border-radius:50%;background:var(--cranberry);
  box-shadow:0 0 0 3px rgba(104,10,29,.14)}
.ftrack .fspan{position:absolute;top:50%;height:7px;margin-top:-3.5px;border-radius:4px;
  background:linear-gradient(90deg,rgba(104,10,29,.75),rgba(20,85,143,.6))}
@media (max-width:620px){
  .feed-axis{padding-left:0;font-size:11px}
  .feed-group li{grid-template-columns:1fr auto;gap:6px 10px}
  .feed-group li>b{grid-column:1}
  .feed-group li>em{grid-column:2;justify-self:end}
  .ftrack{grid-column:1 / -1}
}
/* ---- the same reveal the front page uses, so About moves like the rest --- */
.rv{opacity:0;transform:translateY(14px);
  transition:opacity .7s cubic-bezier(.19,1,.22,1),transform .7s cubic-bezier(.19,1,.22,1)}
.rv.vis{opacity:1;transform:none}
@media (prefers-reduced-motion: reduce){ .rv{opacity:1;transform:none;transition:none} }
@media (max-width:640px){
  .abio{grid-template-columns:1fr;justify-items:center;text-align:center}
  .abio-text h2{text-align:center}
}
"""

s = io.open('about.html', encoding='utf-8-sig').read().replace(chr(13) + NL, NL)

m = re.search(r'(<div class="doc-in">)(.*?)(\n  </div>\n</main>)', s, re.S)
assert m, 'doc-in block not found'
s = s[:m.start(2)] + BODY + s[m.end(2):]

# the CSS is appended, not replaced, so a second run onto an already-built
# page would stack a duplicate block and let the stale rules keep winning

C0, C1 = '/* == about:css start == */', '/* == about:css end == */'
FENCED = C0 + NL + CSS.strip(NL) + NL + C1 + NL
if C0 in s:                       # rebuild: replace the fence, keep everything else
    a = s.index(C0); b = s.index(C1) + len(C1) + 1
    s = s[:a] + FENCED + s[b:]
else:
    i = s.rindex('</style>')
    s = s[:i] + FENCED + s[i:]

LIGHTBOX = """
<div class="lbox" id="lbox" hidden aria-hidden="true" role="dialog" aria-modal="true"
     aria-label="Portrait of Duncan Burns">
  <button class="lbox-x" type="button" aria-label="Close">&times;</button>
  <img src="assets/duncan-burns.jpg" width="400" height="400" alt="Duncan Burns">
</div>
<script>
/* The portrait is a real link to the file, so with scripting off a click still
   opens the image. Here that is intercepted and shown in place instead. The
   source is 400px square and the panel is capped there, so it is never upscaled. */
(function(){
  var link = document.querySelector('.abio-facelink');
  var box  = document.getElementById('lbox');
  if (!link || !box) return;
  var last = null;

  function open(e){
    e.preventDefault();
    last = document.activeElement;
    box.hidden = false;
    box.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(function(){ box.classList.add('on'); });
    box.querySelector('.lbox-x').focus();
    document.body.style.overflow = 'hidden';
  }
  function close(){
    box.classList.remove('on');
    box.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    setTimeout(function(){ box.hidden = true; }, 200);
    if (last) last.focus();
  }
  link.addEventListener('click', open);
  box.addEventListener('click', function(e){
    if (e.target === box || e.target.classList.contains('lbox-x')) close();
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && !box.hidden) close();
  });
})();
</script>
<script>
/* Sections arrive as you reach them, staggered, matching the front page. Anything
   already on screen at load is shown immediately rather than fading in under the
   reader. */
(function(){
  var els = [].slice.call(document.querySelectorAll('.rv'));
  if (!els.length) return;
  if (!('IntersectionObserver' in window) ||
      matchMedia('(prefers-reduced-motion: reduce)').matches){
    els.forEach(function(e){ e.classList.add('vis'); });
    return;
  }
  var io = new IntersectionObserver(function(rows){
    rows.forEach(function(r, i){
      if (!r.isIntersecting) return;
      var el = r.target;
      setTimeout(function(){ el.classList.add('vis'); }, i * 70);
      io.unobserve(el);
    });
  }, {rootMargin: '0px 0px -8% 0px', threshold: 0.06});
  els.forEach(function(e){
    if (e.getBoundingClientRect().top < innerHeight) e.classList.add('vis');
    else io.observe(e);
  });
  setTimeout(function(){ els.forEach(function(e){ e.classList.add('vis'); }); }, 6000);
})();
</script>
"""
J0, J1 = '<!-- == about:js start == -->', '<!-- == about:js end == -->'
BLOCK = J0 + NL + LIGHTBOX.strip(NL) + NL + J1 + NL
if J0 in s:
    a = s.index(J0); b = s.index(J1) + len(J1) + 1
    s = s[:a] + BLOCK + s[b:]
else:
    assert s.count('</body>') == 1
    s = s.replace('</body>', BLOCK + '</body>')


# an early version of this script appended its CSS instead of replacing it, and
# the copy it left behind sat above the fence carrying rules the fence no longer
# has. Both shipped for weeks, and build_method.py uses this page as its shell,
# so the stale block was being copied onto Method too. One block, or stop.
_css = s.count('---- About ---')
assert _css == 1, 'the About CSS appears %d times; a stale copy is loose' % _css
_box = s.count('<div class="lbox"')
assert _box == 1, 'the lightbox appears %d times; duplicate id=lbox' % _box

# Dashboards is an anchor on the front page, not on this one
s = s.replace('<a href="#dashboards">Dashboards</a>',
              '<a href="index.html#dashboards">Dashboards</a>')
assert '"#dashboards"' not in s, 'a bare #dashboards link survives'

io.open('about.html', 'w', encoding='utf-8', newline=NL).write(s)
print('about.html rebuilt: %.1f KB' % (len(s) / 1024.0))
print('outbound links: %d | column titles: %d | schedule rows: %d'
      % (len(re.findall(r'href="https?://(?!fonts|use)', s)),
         len(re.findall(r'<li>[A-Z]', s)),
         len(re.findall(r'class="ftrack"', s))))
