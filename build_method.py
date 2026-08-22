# -*- coding: utf-8 -*-
"""Render MASTER_DATA.md as a real page.

The Method nav item pointed straight at the markdown file. GitHub Pages serves
.md as text/markdown, so a visitor got 767 lines of raw '#' and '>' with no
styling, no nav and no way back - and the first thing they read was an
instruction addressed to an AI assistant about how to prompt it. That is the
opposite of what a page called Method should do on a site whose argument is that
every figure is checkable.

What the file actually holds is the citation register: 365 rows of
figure -> source -> date verified, section by section. That is the most
defensible thing on the site, so it gets rendered properly.

Three sections are held back. "How to Use This File" is addressed to me, not to a
reader. The "Update Log" carries an "Updated By" column naming its authors,
which is a disclosure decision for Duncan rather than a default. "Gold &
Treasury" is federal reserve-holdings research that no dashboard on this site
draws on - the Method page is meant to account for the figures that are
published, and sourcing something nothing shows invites the question of where
it is. The research stays in MASTER_DATA.md; it just stops being published.

The one distinction the page must not lose is the file's own: a row marked with
the recycling mark is API-fed and authoritative in data/*.json, while a ticked
row is hand-verified and can drift between reviews. Those become visible chips
rather than emoji buried in a table cell.
"""
import io, re, html as H

NL = chr(10)
SRC, OUT = 'MASTER_DATA.md', 'method.html'
SKIP_SECTIONS = ('How to Use This File', 'Update Log', 'Gold & Treasury')

TICK, LIVE = '✅', '\U0001f504'          # the two status marks used in the file
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️⬀-⯿]+')

def strip_emoji(t):
    return EMOJI.sub('', t).strip()

def inline(t):
    """bold, code, links and the two status marks."""
    t = H.escape(t, quote=False)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = t.replace(TICK, '<span class="mk mk-v" title="hand verified">verified</span>')
    t = t.replace(LIVE, '<span class="mk mk-l" title="refreshed by a feed">live</span>')
    return t

def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', strip_emoji(t).lower()).strip('-')[:48]


def convert(md):
    """A converter for exactly the subset this file uses: h2-h4, tables,
    bullets, blockquotes, rules and paragraphs."""
    out, sections = [], []
    lines = md.split('\n')
    i, skipping = 0, False
    para, bullets, quote, table = [], [], [], []

    def flush():
        if para:
            out.append('<p>%s</p>' % inline(' '.join(para))); para.clear()
        if bullets:
            out.append('<ul class="mk-list">%s</ul>' %
                       ''.join('<li>%s</li>' % inline(b) for b in bullets)); bullets.clear()
        if quote:
            out.append('<blockquote class="mk-note">%s</blockquote>' %
                       ''.join('<p>%s</p>' % inline(q) for q in quote if q.strip())); quote.clear()
        if table:
            head, rows = table[0], [r for r in table[1:]
                                    if not re.match(r'^[\s|:-]+$', '|'.join(r))]
            out.append('<div class="mk-tw"><table class="mk-t"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
                ''.join('<th>%s</th>' % inline(c) for c in head),
                ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(c) for c in r) for r in rows)))
            table.clear()

    while i < len(lines):
        raw = lines[i].rstrip()
        s = raw.strip()

        if s.startswith('## '):
            flush()
            title = s[3:].strip()
            skipping = any(k in title for k in SKIP_SECTIONS)
            if not skipping:
                t = strip_emoji(title)
                sections.append((slug(title), t))
                out.append('<h2 id="%s" class="mk-h2 rv">%s</h2>' % (slug(title), inline(t)))
            i += 1; continue

        if skipping:
            i += 1; continue

        if s.startswith('#### '):
            flush(); out.append('<h4 class="mk-h4">%s</h4>' % inline(strip_emoji(s[5:]))); i += 1; continue
        if s.startswith('### '):
            flush(); out.append('<h3 class="mk-h3">%s</h3>' % inline(strip_emoji(s[4:]))); i += 1; continue
        if s.startswith('# '):
            i += 1; continue
        if s == '---':
            flush(); i += 1; continue
        if s.startswith('>'):
            if para or bullets or table: flush()
            quote.append(s.lstrip('>').strip()); i += 1; continue
        if s.startswith('|'):
            if para or bullets or quote: flush()
            table.append([c.strip() for c in s.strip('|').split('|')]); i += 1; continue
        if re.match(r'^[-*] ', s):
            if para or quote or table: flush()
            bullets.append(s[2:]); i += 1; continue
        if not s:
            flush(); i += 1; continue
        if quote or bullets or table: flush()
        para.append(s); i += 1

    flush()
    return '\n'.join(out), sections


CSS = """/* == method:css start == */
.mk-lede{font-size:clamp(17px,1.5vw,24px);line-height:1.45;text-align:center;margin:0}
.mk-key{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:20px 0 6px}
.mk-key span{font-family:var(--font-text);font-size:13px;color:rgba(11,17,19,.78)}
.mk{display:inline-block;font-family:var(--font-mono);font-size:11px;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:5px;
  border:1px solid;white-space:nowrap}
.mk-v{color:#2C6B45;border-color:rgba(56,133,87,.42);background:rgba(56,133,87,.10)}
.mk-l{color:#0F4577;border-color:rgba(20,85,143,.40);background:rgba(20,85,143,.09)}
.mk-jump{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin:22px 0 0;padding:0;list-style:none}
.mk-jump a{display:inline-block;text-decoration:none;font-family:var(--font-mono);font-size:11px;
  font-weight:600;letter-spacing:.06em;padding:6px 11px;border-radius:7px;color:var(--bay-blue);
  background:rgba(20,85,143,.07);border:1px solid rgba(20,85,143,.20);transition:background .2s,border-color .2s}
.mk-jump a:hover{background:rgba(20,85,143,.15);border-color:rgba(20,85,143,.45)}
.mk-body{text-align:left;margin:34px 0 0}
.mk-h2{font-family:var(--font-display);font-weight:700;letter-spacing:-.025em;
  font-size:clamp(20px,2vw,29px);color:var(--ink);margin:46px 0 4px;padding-top:24px;
  border-top:1px solid rgba(11,17,19,.12);scroll-margin-top:80px}
.mk-h2:first-of-type{margin-top:8px}
.mk-h3{font-family:var(--font-display);font-weight:700;letter-spacing:-.015em;
  font-size:clamp(15px,1.35vw,19px);color:var(--cranberry);margin:28px 0 6px}
.mk-h4{font-family:var(--font-text);font-weight:700;font-size:14px;margin:18px 0 4px;color:var(--ink)}
.mk-body p{font-family:var(--font-text);font-size:14.5px;line-height:1.68;
  color:rgba(11,17,19,.84);margin:8px 0}
.mk-list{margin:8px 0 8px 2px;padding:0;list-style:none}
.mk-list li{position:relative;padding-left:16px;font-family:var(--font-text);font-size:14px;
  line-height:1.6;color:rgba(11,17,19,.84);margin:4px 0}
.mk-list li::before{content:'';position:absolute;left:2px;top:.62em;width:5px;height:5px;
  border-radius:50%;background:rgba(20,85,143,.55)}
.mk-note{margin:14px 0;padding:13px 16px;border-radius:11px;
  background:rgba(194,65,12,.06);border:1px solid rgba(194,65,12,.22)}
.mk-note p{margin:4px 0;font-size:13.5px;color:rgba(11,17,19,.86)}
.mk-tw{overflow-x:auto;margin:12px 0 16px;border-radius:11px;
  border:1px solid rgba(11,17,19,.09);background:rgba(255,255,255,.55)}
.mk-t{border-collapse:collapse;width:100%;min-width:520px}
.mk-t th{position:sticky;top:0;text-align:left;font-family:var(--font-mono);font-size:11px;
  font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(11,17,19,.62);
  padding:10px 13px;background:rgba(241,243,242,.97);border-bottom:1px solid rgba(11,17,19,.12)}
.mk-t td{font-family:var(--font-text);font-size:13.5px;color:rgba(11,17,19,.86);
  padding:9px 13px;border-bottom:1px solid rgba(11,17,19,.06);vertical-align:top}
.mk-t tbody tr:last-child td{border-bottom:0}
.mk-t tbody tr:hover{background:rgba(20,85,143,.045)}
.mk-t td:nth-child(2){font-family:var(--font-mono);font-size:13px;white-space:nowrap}
.mk-body code{font-family:var(--font-mono);font-size:12.5px;padding:1px 5px;border-radius:4px;
  background:rgba(11,17,19,.06);color:rgba(11,17,19,.78)}
@media (max-width:620px){ .mk-t{min-width:440px} }
/* == method:css end == */"""


def build():
    md = io.open(SRC, encoding='utf-8').read()
    body, sections = convert(md)

    shell = io.open('about.html', encoding='utf-8').read().replace('\r\n', '\n')
    head = shell[shell.index('<head>'):shell.index('</head>') + 7]
    head = re.sub(r'<title>.*?</title>', '<title>Method — Massachusetts Data Hub</title>', head, flags=re.S)
    head = re.sub(r'<meta name="description"[^>]*>',
                  '<meta name="description" content="Every figure on Massachusetts Data Hub, '
                  'with its source, its source URL and the date it was verified.">', head)
    head = re.sub(r'<link rel="canonical"[^>]*>', '', head)
    # about.html keeps a second <style> in the body holding .doc / .doc-in;
    # without it this page has no frame - the heading lands on the wordmark
    extra = re.findall(r'<style>.*?</style>', shell[shell.index('</head>'):], re.S)
    head = head.replace('</head>', NL.join(extra) + NL + '<style>' + CSS + '</style>' + NL + '</head>')

    hdr = re.search(r'<header class="site-head">.*?</header>', shell, re.S).group(0)
    hdr = hdr.replace(' aria-current="page"', '')
    hdr = hdr.replace('<a href="MASTER_DATA.md">Method</a>',
                      '<a href="method.html" aria-current="page">Method</a>')
    ftr = re.search(r'<footer>.*?</footer>', shell, re.S).group(0)
    flow = re.search(r'<script type="module">\s*/\* =+\s*EFFECT 3.*?</script>', shell, re.S).group(0)
    skip = '<a class="skip-link" href="#main">Skip to content</a>'

    jump = ''.join('<li><a href="#%s">%s</a></li>' % (s, t) for s, t in sections)

    page = """<!DOCTYPE html>
<html lang="en">
%(head)s
<body>
%(skip)s
<canvas id="flow" aria-hidden="true"></canvas>
%(hdr)s
<main id="main" class="doc">
  <div class="doc-in">
    <h1>Method</h1>
    <span class="ramp" aria-hidden="true"></span>
    <p class="mk-lede">Every figure on this site, with the source it came from and
    the date it was checked.</p>
    <div class="mk-key">
      <span><span class="mk mk-v">verified</span> checked by hand against the source</span>
      <span><span class="mk mk-l">live</span> refreshed by a feed; the JSON is authoritative</span>
    </div>
    <ul class="mk-jump">%(jump)s</ul>
    <div class="mk-body">
%(body)s
    </div>
  </div>
</main>
%(ftr)s
<script type="importmap">
{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js"}}
</script>
%(flow)s
</body>
</html>
""" % dict(head=head, skip=skip, hdr=hdr, ftr=ftr, flow=flow, jump=jump, body=body)

    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(page)
    print('%s: %.1f KB' % (OUT, len(page) / 1024.0))
    print('sections: %d | tables: %d | rows: %d | notes: %d' % (
        len(sections), page.count('<table'), page.count('<tr>') - page.count('<thead'),
        page.count('mk-note')))
    print('status chips: verified %d, live %d' % (page.count('mk-v">'), page.count('mk-l">')))


build()
