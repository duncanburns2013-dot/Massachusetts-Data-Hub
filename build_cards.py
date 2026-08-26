# -*- coding: utf-8 -*-
"""Render one social card per page.

Every page used to share a single og-image.png, so a link to the Energy
dashboard and a link to the Pension dashboard produced the same picture. The
card also lost the old one's structure when it was restyled: the description
and the address moved out of the lower left and the artwork ended up centred,
pale and empty across its bottom third, which is what makes a shared post read
as a dead image rather than a designed one.

This puts the old card's bones back under the current identity. The wordmark,
headline, rule, description and address all anchor to the left column exactly
as they did before; the palette, the type and the map are the ones the site
actually uses now, so a reader who clicks through lands somewhere that looks
like the card they clicked.

Text is not written here. Each card takes the og:title and og:description that
seo.py already curated for that page, so the card cannot disagree with the page
it points at, and fixing a description in one place fixes it in both.

Nothing dated, no count, no address baked into artwork that a domain move would
falsify: the previous card carried the github.io URL and said "15 DASHBOARDS"
when there were 16, and went stale twice over. 351 is fixed by statute and the
domain is the one thing on the card that is now permanent.

Re-runnable. Renders through headless Chrome, which is what makes the site's
real webfont and the live instrument's map available to the artwork.
"""
import io, os, re, sys, html, glob, shutil, subprocess, tempfile
from PIL import Image

NL = chr(10)
ROOT = os.path.dirname(os.path.abspath(__file__))
CARDS = 'cards'                      # published at /cards/<page>.jpg
MAP = 'assets/card-map.png'          # cut out of a real instrument render
DEFAULT = 'og-image.png'             # the hub card, kept at its historic path

CHROME = os.environ.get('CHROME_BIN') or next(
    (p for p in (
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ) if os.path.exists(p)), None)

# pages that are deliberately not indexed have no card either
SKIP = {'404.html', 'template.html', 'tax-burden-nh-comparison.html'}

SITE = 'Massachusetts Data Hub'
DOMAIN = 'massachusettsdatahub.com'


TEMPLATE = u"""<meta charset="utf-8">
<link rel="stylesheet" href="https://use.typekit.net/irk1bar.css">
<style>
  /* Tokens are the site's own. A card that invents its own palette drifts from
     the page it advertises within one restyle. */
  :root{
    --paper:#E9EBEA; --ink:#0B1113; --cranberry:#680A1D; --bay:#14558F;
    --muted:#4E585B;
    --display:'halyard-display',system-ui,sans-serif;
    --text:'halyard-text',system-ui,sans-serif;
    --mono:'ibm-plex-mono',ui-monospace,monospace;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1200px;height:630px;overflow:hidden}
  body{
    background:
      radial-gradient(58% 100% at 2% 0%, rgba(104,10,29,.15), transparent 62%),
      radial-gradient(70% 116% at 99% 8%, rgba(20,85,143,.17), transparent 64%),
      var(--paper);
    font-family:var(--text); color:var(--ink); position:relative;
  }

  /* The state sits off the right edge rather than under the type. Centred, it
     forced every line to fight the artwork for contrast, which is how the old
     rebuild ended up washed out. Held right, the left column keeps clean paper
     and the silhouette still reads - the Cape is never cropped, because it is
     the feature that makes the shape recognisable as Massachusetts. */
  .map{
    position:absolute; right:-34px; top:50%; transform:translateY(-50%);
    width:762px; height:auto; display:block;
    opacity:.42; mix-blend-mode:multiply;
    -webkit-mask-image:linear-gradient(90deg, transparent 0%, rgba(0,0,0,.32) 20%, #000 52%);
            mask-image:linear-gradient(90deg, transparent 0%, rgba(0,0,0,.32) 20%, #000 52%);
  }

  /* A hairline of the site's own colour ramp along the top edge. It gives the
     card a decided border in a feed, where a pale image against a pale
     timeline is what reads as "failed to load". */
  .edge{
    position:absolute; left:0; top:0; width:100%; height:7px;
    background:linear-gradient(90deg,#12467F,#3D82BC,#8FB9D6,#CFC7B4,#F2A65A,#DC5127,#8E0B22);
  }

  .col{
    position:absolute; left:72px; top:64px; bottom:60px; width:660px;
    display:flex; flex-direction:column; align-items:flex-start;
  }
  .eyebrow{
    font-family:var(--mono); font-size:15px; font-weight:600;
    letter-spacing:.30em; text-transform:uppercase; color:var(--bay);
  }
  h1{
    font-family:var(--display); font-weight:700; line-height:.98;
    letter-spacing:-.035em; color:var(--cranberry); margin:20px 0 0;
    /* the wordmark must stay legible where it crosses the map */
    text-shadow:0 0 30px rgba(233,235,234,.92), 0 0 10px rgba(233,235,234,.86);
  }
  .ramp{
    display:block; width:262px; height:4px; border-radius:2px; margin:26px 0 0;
    background:linear-gradient(90deg,#12467F,#3D82BC,#8FB9D6,#CFC7B4,#F2A65A,#DC5127,#8E0B22);
  }
  /* the description holds the lower left, which is where it lived on the card
     this replaces and where a reader's eye lands after the headline */
  p.desc{
    font-size:21px; line-height:1.48; color:var(--muted); max-width:41ch;
    margin:auto 0 0;
  }
  p.desc b{color:var(--ink); font-weight:600}
  .addr{
    display:inline-flex; align-items:center; gap:10px; margin:26px 0 0;
    font-family:var(--mono); font-size:15px; font-weight:600; letter-spacing:.02em;
    color:var(--bay); background:rgba(20,85,143,.10);
    border:1px solid rgba(20,85,143,.26); border-radius:999px; padding:9px 18px 9px 14px;
  }
  .dot{width:8px;height:8px;border-radius:50%;background:#388557;display:block}
</style>
<img class="map" src="__MAP__" alt="">
<span class="edge"></span>
<div class="col">
  <div class="eyebrow">__EYEBROW__</div>
  <h1 id="h">__TITLE__</h1>
  <span class="ramp"></span>
  <p class="desc">__DESC__</p>
  <span class="addr"><span class="dot"></span>__DOMAIN__</span>
</div>
<script>
/* Titles run from two words to ten, so the headline is fitted rather than set.
   It steps down until it fits the column in at most three lines - a fixed size
   either clips the long ones or leaves the short ones looking timid. */
(function(){
  var h = document.getElementById('h');
  var maxH = 250, size = 78;
  h.style.fontSize = size + 'px';
  while (size > 38 && (h.scrollHeight > maxH || h.scrollWidth > h.parentNode.clientWidth)) {
    size -= 2;
    h.style.fontSize = size + 'px';
  }
  document.documentElement.setAttribute('data-fitted', size);
})();
</script>
"""


def pages():
    """(file, title, description) for every page that should carry a card."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
        name = os.path.basename(f)
        if name in SKIP:
            continue
        s = io.open(f, encoding='utf-8').read()
        t = re.search(r'<meta property="og:title" content="([^"]*)"', s)
        d = re.search(r'<meta property="og:description" content="([^"]*)"', s)
        if not (t and d):
            print('  skipped (no og tags): %s' % name)
            continue
        out.append((name, html.unescape(t.group(1)).strip(),
                    html.unescape(d.group(1)).strip()))
    return out


def emphasise(desc):
    """Bold the clause after the last em dash.

    The old card set its closing claim in solid ink against muted body text,
    which is what gave it a point to land on. Descriptions here are written
    with a dash before the claim, so that is the seam to use - and when there
    is no dash the paragraph simply stays even, rather than bolding an
    arbitrary half of it.
    """
    d = html.escape(desc, quote=False)
    if u'\u2014' in d:
        head, tail = d.rsplit(u'\u2014', 1)
        if 12 <= len(tail.strip()) <= 90:
            return u'%s\u2014 <b>%s</b>' % (head, tail.strip())
    return d


def render(html_path, out_path):
    if not CHROME:
        sys.exit('no Chrome found - set CHROME_BIN to the executable')
    profile = tempfile.mkdtemp(prefix='cardshot-')
    try:
        subprocess.run([
            CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
            '--no-first-run', '--no-default-browser-check', '--force-device-scale-factor=1',
            '--user-data-dir=' + profile,
            '--window-size=1200,630',
            # long enough for the webfont to load and the fitter to settle
            '--virtual-time-budget=12000',
            '--screenshot=' + out_path,
            'file:///' + html_path.replace('\\', '/'),
        ], check=True, capture_output=True, timeout=180)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def main():
    os.chdir(ROOT)
    if not os.path.exists(MAP):
        sys.exit('missing %s - the card cannot be rebuilt without it' % MAP)
    if not os.path.isdir(CARDS):
        os.makedirs(CARDS)

    work = tempfile.mkdtemp(prefix='cards-')
    map_uri = 'file:///' + os.path.join(ROOT, MAP).replace('\\', '/')
    built = []

    # an optional filter, so the design can be iterated against one card
    # instead of waiting for the whole set to re-render
    only = [a.replace('.html', '') for a in sys.argv[1:]]

    try:
        for name, title, desc in pages():
            slug = name[:-5]
            if only and slug not in only:
                continue
            # on the front page the headline is the wordmark, so the eyebrow
            # carries the scope instead of repeating it
            eyebrow = 'All 351 municipalities' if title.strip() == SITE else SITE
            page = (TEMPLATE
                    .replace('__MAP__', map_uri)
                    .replace('__EYEBROW__', html.escape(eyebrow, quote=False))
                    .replace('__TITLE__', html.escape(title, quote=False))
                    .replace('__DESC__', emphasise(desc))
                    .replace('__DOMAIN__', DOMAIN))
            src = os.path.join(work, slug + '.html')
            io.open(src, 'w', encoding='utf-8', newline=NL).write(page)

            shot = os.path.join(work, slug + '.png')
            render(src, shot)
            if not os.path.exists(shot):
                sys.exit('render produced nothing for %s' % name)

            # Chrome only writes PNG, and a photographic map does not belong in
            # one: twenty-one of them would add about 7 MB to a site that was
            # deliberately cut to 14. JPEG is what every scraper wants anyway.
            out = os.path.join(ROOT, CARDS, slug + '.jpg')
            im = Image.open(shot).convert('RGB')
            if im.size != (1200, 630):
                sys.exit('%s rendered at %sx%s, expected 1200x630' % ((name,) + im.size))
            im.save(out, 'JPEG', quality=86, optimize=True, progressive=True)

            built.append((slug, os.path.getsize(out)))
            print('  %-30s %6.0f KB' % (slug + '.jpg', os.path.getsize(out) / 1024.0))

        # the hub card also stays at the historic path, so anything that cached
        # og-image.png keeps resolving to something correct
        idx = os.path.join(ROOT, CARDS, 'index.jpg')
        if os.path.exists(idx):
            Image.open(idx).save(os.path.join(ROOT, DEFAULT), 'PNG', optimize=True)
            print('  %-30s (the hub card, at its historic path)' % DEFAULT)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(NL + 'cards built: %d' % len(built))
    if built:
        big = [s for s, n in built if n > 900000]
        if big:
            print('  oversized (>900 KB), some scrapers refuse these: %s' % ', '.join(big))


if __name__ == '__main__':
    main()
