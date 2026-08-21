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

    <section class="abio">
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

    <blockquote class="acreed">
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

    <h2 class="asub">This started in print</h2>
    <p class="panel-body">The questions on this site are not new ones. They ran
    in <em>The Valley Patriot</em> first, and the dashboards exist because a
    column can make an argument but cannot show you the arithmetic.</p>
    <ul class="acols">
      <li>How Beacon Hill Is Bankrupting the Merrimack Valley</li>
      <li>H-1B Foreign Workers Are Destroying Merrimack Valley Economy</li>
      <li>Akamai Uses Tax Breaks to Hire H1B Foreign Workers</li>
      <li>The Battle of Unequitable Liberty in Massachusetts</li>
    </ul>
    <p class="panel-note"><a href="https://valleypatriot.com/category/op-eds-editorials/duncan-burns/"
       target="_blank" rel="noopener">The full archive, 2016 to 2026 &nearr;</a></p>

    <h2 class="asub">How the figures are handled</h2>
    <p class="panel-body">Every figure is traceable. Nothing is modelled,
    estimated or smoothed unless the dashboard says so in plain language and
    names the method. Where two official sources disagree, both are shown rather
    than averaged. The instrument on the front page carries all 351
    municipalities at their real geometry; the dashboards behind it hold the
    detail, each with its own source vintage.</p>

    <h2 class="asub">And how they stay current</h2>
    <p class="panel-body">There is no site-wide &ldquo;updated&rdquo; date,
    because one would only tell you when a script last ran. Nine pipelines
    refresh on their own clocks, matched to when each source actually publishes.</p>
    <dl class="afeeds">
      <div><dt>MLS figures</dt><dd>daily, 07:00</dd></div>
      <div><dt>New Hampshire figures</dt><dd>daily, 07:20</dd></div>
      <div><dt>Census ACS</dt><dd>monthly, 20th</dd></div>
      <div><dt>CBP encounters</dt><dd>monthly, 25th</dd></div>
      <div><dt>IRS SOI migration</dt><dd>monthly, 1st</dd></div>
      <div><dt>Consumer prices</dt><dd>monthly, 10th&ndash;16th</dd></div>
      <div><dt>Energy</dt><dd>2nd and 26th</dd></div>
      <div><dt>Employment</dt><dd>monthly, Fridays</dd></div>
      <div><dt>This site</dt><dd>every 3 hours</dd></div>
    </dl>
    <p class="panel-note">Built and maintained in the open. The full source, the
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
  border-radius:16px;border:1px solid rgba(104,10,29,.20);
  border-left:4px solid var(--cranberry);
  background:linear-gradient(180deg,rgba(104,10,29,.055),rgba(104,10,29,.02))}
.acreed p{font-family:var(--font-display);font-weight:400;
  font-size:clamp(16px,1.55vw,22px);line-height:1.5;letter-spacing:-.012em;
  color:rgba(11,17,19,.90);margin:0 0 14px;max-width:74ch}
.acreed p:last-of-type{margin-bottom:16px}
.acreed cite{display:block;font-family:var(--font-mono);font-style:normal;
  font-size:10.5px;font-weight:700;letter-spacing:.17em;text-transform:uppercase;
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
  background:rgba(255,255,255,.5);border:1px solid rgba(11,17,19,.07);
  border-left:3px solid var(--cranberry)}

.afeeds{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(268px,1fr));
  margin:16px 0 0;text-align:left}
.afeeds > div{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  padding:9px 13px;border-radius:9px;background:rgba(255,255,255,.5);
  border:1px solid rgba(11,17,19,.07)}
.afeeds dt{font-family:var(--font-text);font-size:13.5px;color:rgba(11,17,19,.84)}
.afeeds dd{margin:0;font-family:var(--font-mono);font-size:11.5px;font-weight:600;
  letter-spacing:.04em;color:var(--bay-blue);white-space:nowrap}

@media (max-width:640px){
  .abio{grid-template-columns:1fr;justify-items:center;text-align:center}
  .abio-text h2{text-align:center}
}
"""

s = io.open('about.html', encoding='utf-8-sig').read().replace(chr(13) + NL, NL)

m = re.search(r'(<div class="doc-in">)(.*?)(\n  </div>\n</main>)', s, re.S)
assert m, 'doc-in block not found'
s = s[:m.start(2)] + BODY + s[m.end(2):]

assert s.count('</style>') == 2, s.count('</style>')
i = s.rindex('</style>')
s = s[:i] + CSS + NL + s[i:]

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
"""
assert s.count('</body>') == 1
s = s.replace('</body>', LIGHTBOX + '</body>')

io.open('about.html', 'w', encoding='utf-8', newline=NL).write(s)
print('about.html rebuilt: %.1f KB' % (len(s) / 1024.0))
print('outbound links: %d | column titles: %d | feed rows: %d'
      % (len(re.findall(r'href="https?://(?!fonts|use\.typekit)', s)),
         len(re.findall(r'<li>[A-Z]', s)),
         len(re.findall(r'<div><dt>', s))))
