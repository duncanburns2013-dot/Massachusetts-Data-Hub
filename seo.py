# -*- coding: utf-8 -*-
"""Stamp canonicals, descriptions, sitemap, robots and a 404 across the site.

BASE is the one place the site's address lives. When massachusettsdatahub.com is
connected, change BASE and re-run this - that is the whole migration. Getting
canonicals in before the domain move matters: the moment the content answers on
two addresses, a search engine treats them as duplicates and splits the ranking
between them unless every page names which one is real.

Re-runnable. Existing canonical and og:url tags are replaced rather than
duplicated, and pages that already carry a description are left alone.
"""
import io, re, glob, os

BASE = 'https://massachusettsdatahub.com/'

# every address this site has answered on. Anything still naming one of
# these gets moved to BASE - og:image and twitter:image included, which
# canonical-only rewriting used to miss. Scoped to this repo's own path so
# the sibling projects on the same host, and all-things-boston's og:image
# which lives in another repository, are left where they are.
FORMER = ['https://duncanburns2013-dot.github.io/Massachusetts-Data-Hub/']

# pages that should never be indexed, and never appear in the sitemap
NOINDEX = {
    'template.html':                 'a development template, not content',
    'tax-burden-nh-comparison.html': 'a redirect stub kept so an old shared URL does not 404',
    '404.html':                      'served for URLs that do not exist; it is not one itself',
}

DESC = {
 'index.html':
   'Massachusetts tax, spending, housing, energy, education and immigration data. '
   'Nineteen dashboards built from primary government sources, with all 351 '
   'municipalities in one interactive instrument.',
 'about.html':
   'Who builds Massachusetts Data Hub, where every figure comes from, and the '
   'schedule each of the nine data feeds refreshes on.',
 'videos.html':
   'Parody and explainers on Massachusetts politics. Twenty-two short films, each '
   'labelled as one or the other so nothing here is mistaken for the record.',
 'instrument.html':
   'All 351 Massachusetts municipalities as a single interactive object: tax rates, '
   'real burden per resident, median home price and affordability, at real geometry.',
 'all-things-boston.html':
   "Boston's city budget, employee payroll, FBI crime figures, BPS education, ICE "
   'enforcement, commercial real estate, housing, 311 and pension obligations, all '
   'from official city data.',
 'energy-dashboard.html':
   'Why Massachusetts electricity costs what it does: the RGGI carbon tax, the '
   'mandates behind the charges, how the state compares with its neighbours, and '
   'where the money goes.',
 'ma-housing-dashboard.html':
   'Massachusetts MLS data for the state, Boston, Essex County and Greater '
   'Newburyport: median prices, days on market, sale-to-list ratios and '
   'affordability, over thirteen years.',
}

pages = sorted(p for p in glob.glob('*.html') if not p.startswith('_'))
added_desc = added_canon = fixed_og = added_noindex = moved = 0

for p in pages:
    s = orig = io.open(p, encoding='utf-8').read()
    url = BASE + ('' if p == 'index.html' else p)

    # --- move any address the site used to answer on
    for old in FORMER:
        if old != BASE and old in s:
            s = s.replace(old, BASE)
            moved += 1

    # --- canonical: replace any existing one rather than stacking a second
    s = re.sub(r'[ \t]*<link[^>]+rel="canonical"[^>]*>\n?', '', s)
    if p not in NOINDEX:
        tag = '<link rel="canonical" href="%s">\n' % url
        m = re.search(r'(<meta[^>]+name="viewport"[^>]*>\n)', s)
        if m:
            s = s[:m.end()] + tag + s[m.end():]
            added_canon += 1

    # --- og:url pointed at another repository entirely on one page
    def og(m):
        global fixed_og
        if m.group(1) != url: fixed_og += 1
        return '<meta property="og:url" content="%s">' % url
    s = re.sub(r'<meta property="og:url" content="([^"]*)"\s*/?>', og, s)

    # --- description
    if p in DESC and not re.search(r'name="description"', s):
        d = '<meta name="description" content="%s">\n' % DESC[p]
        m = re.search(r'(<title>.*?</title>\n)', s, re.S)
        if m:
            s = s[:m.end()] + d + s[m.end():]
            added_desc += 1

    # --- keep the template and the redirect stub out of the index
    if p in NOINDEX and 'name="robots"' not in s:
        m = re.search(r'(<title>.*?</title>\n)', s, re.S)
        if m:
            s = s[:m.end()] + '<meta name="robots" content="noindex,follow">\n' + s[m.end():]
            added_noindex += 1

    if s != orig:
        io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# ---------------------------------------------------------------- sitemap
listed = [p for p in pages if p not in NOINDEX]
def loc(p): return BASE + ('' if p == 'index.html' else p)
prio = lambda p: '1.0' if p == 'index.html' else ('0.9' if p in ('about.html','videos.html','instrument.html') else '0.8')
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p in listed:
    sm += ['  <url>', '    <loc>%s</loc>' % loc(p),
           '    <priority>%s</priority>' % prio(p), '  </url>']
sm.append('</urlset>')
io.open('sitemap.xml', 'w', encoding='utf-8', newline='\n').write('\n'.join(sm) + '\n')

# ---------------------------------------------------------------- robots
io.open('robots.txt', 'w', encoding='utf-8', newline='\n').write(
    'User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n' % BASE)

print('pages moved to BASE: %d' % moved)
print('canonicals stamped : %d' % added_canon)
print('descriptions added : %d' % added_desc)
print('og:url normalised  : %d changed' % fixed_og)
print('noindex added      : %d (%s)' % (added_noindex, ', '.join(NOINDEX)))
print('sitemap.xml        : %d urls' % len(listed))
print('robots.txt         : written')
