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
import io, re, glob, os, json, html, subprocess

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
 # No count that can move. Dashboards get added, films get added, feeds get
 # added, and a description that names a total is wrong from the next commit
 # onwards without anything appearing to break. 351 is the one number safe to
 # write down, because it is fixed by statute.
 'index.html':
   'Massachusetts tax, spending, housing, energy, education and immigration data, '
   'built from primary government sources, with all 351 municipalities in one '
   'interactive instrument.',
 'about.html':
   'Who builds Massachusetts Data Hub, where every figure comes from, and the '
   'schedule each data feed refreshes on.',
 'videos.html':
   'Parody and explainers on Massachusetts politics, each labelled as one or the '
   'other so nothing here is mistaken for the record.',
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
   'affordability, every year since 2014.',
}

# ---------------------------------------------------------------- structured data
# Pages that are a body of figures get Dataset. The two names that a plain title
# split would mangle are overridden; the rest come from the page's own <title>.
NOT_A_DATASET = {'index.html', 'about.html', 'videos.html', 'method.html'}
DATASET_NAME = {
    'instrument.html':          'Massachusetts municipal tax and affordability, all 351 municipalities',
    'tax-burden-dashboard.html': 'The five layers of Massachusetts and New Hampshire tax burden',
}
# where the figures are about, which is not always Massachusetts
COVERAGE = {
    'nh-housing-dashboard.html':  ['New Hampshire'],
    'tax-burden-dashboard.html':  ['Massachusetts', 'New Hampshire'],
    'all-things-boston.html':     ['Boston, Massachusetts'],
    'haverhill-market-report.html': ['Haverhill, Massachusetts'],
    'education-merrimack-valley.html': ['Merrimack Valley, Massachusetts'],
}

def last_commit(path):
    """git's own record of when this page last changed - not a date I chose"""
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', path],
                             capture_output=True, text=True, timeout=15)
        d = out.stdout.strip()
        return d if re.match(r'^\d{4}-\d{2}-\d{2}$', d) else None
    except Exception:
        return None

def page_title(s):
    m = re.search(r'<title>([^<]*)</title>', s)
    if not m:
        return None
    t = html.unescape(m.group(1)).strip()
    return re.split(r'\s+[\u2014|]\s+', t)[0].strip()

def page_desc(s):
    m = re.search(r'name="description" content="([^"]*)"', s)
    return html.unescape(m.group(1)).strip() if m else None

PERSON = {
    '@type': 'Person',
    '@id': BASE + 'about.html#duncan-burns',
    'name': 'Duncan Burns',
    'url': BASE + 'about.html',
    'sameAs': [
        'https://valleypatriot.com/category/op-eds-editorials/duncan-burns/',
        'https://github.com/duncanburns2013-dot',
    ],
}
ORG = {
    '@type': 'Organization',
    '@id': BASE + '#publisher',
    'name': 'Massachusetts Data Hub',
    'url': BASE,
    'logo': BASE + 'favicon-512.png',
    'founder': {'@id': PERSON['@id']},
}
# the logo file was removed as an orphan, so do not claim one
ORG.pop('logo')

def schema_for(p, s, url):
    title, desc = page_title(s), page_desc(s)
    if not title or not desc:
        return None
    if p == 'index.html':
        node = {'@type': 'WebSite', '@id': BASE + '#website', 'name': 'Massachusetts Data Hub',
                'url': BASE, 'description': desc, 'inLanguage': 'en-US',
                'publisher': ORG, 'creator': PERSON}
    elif p == 'about.html':
        node = {'@type': 'AboutPage', '@id': url, 'url': url, 'name': title,
                'description': desc, 'inLanguage': 'en-US',
                'isPartOf': {'@id': BASE + '#website'}, 'mainEntity': PERSON}
    elif p in NOT_A_DATASET:
        return None
    else:
        node = {'@type': 'Dataset', '@id': url + '#dataset',
                'name': DATASET_NAME.get(p, title), 'description': desc, 'url': url,
                'inLanguage': 'en-US', 'isAccessibleForFree': True,
                'creator': {'@id': PERSON['@id']}, 'publisher': ORG,
                'includedInDataCatalog': {'@type': 'DataCatalog', '@id': BASE + '#website',
                                          'name': 'Massachusetts Data Hub', 'url': BASE},
                'spatialCoverage': [{'@type': 'Place', 'name': n}
                                    for n in COVERAGE.get(p, ['Massachusetts'])]}
        when = last_commit(p)
        if when:
            node['dateModified'] = when
    node['@context'] = 'https://schema.org'
    ordered = {'@context': node.pop('@context')}
    ordered.update(node)
    return ordered

pages = sorted(p for p in glob.glob('*.html') if not p.startswith('_'))
added_desc = added_canon = fixed_og = added_noindex = moved = 0
added_icons = added_card = added_ld = 0

# the tab mark is the state's own outline; the .ico is there for older
# browsers and the crawlers that still ask for it by that name
ICONS = (
    '<link rel="icon" href="%sfavicon.svg" type="image/svg+xml">',
    '<link rel="icon" href="%sfavicon-32.png" sizes="32x32" type="image/png">',
    '<link rel="icon" href="%sfavicon-16.png" sizes="16x16" type="image/png">',
    '<link rel="icon" href="%sfavicon.ico" sizes="48x48">',
    '<link rel="apple-touch-icon" href="%sapple-touch-icon.png">',
)

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

    # --- description. DESC is the curated wording and it wins rather than
    # deferring to whatever the page already carries: leaving the page's own copy
    # alone is how "Nineteen dashboards" outlived a recount that put the real
    # figure at sixteen, three of those front-page cards being other projects.
    if p in DESC:
        want = '<meta name="description" content="%s">' % DESC[p]
        if want not in s:
            s2 = re.sub(r'[ \t]*<meta[^>]+name="description"[^>]*>\n?', '', s)
            m = re.search(r'(<title>.*?</title>\n)', s2, re.S)
            if m:
                s = s2[:m.end()] + want + '\n' + s2[m.end():]
                added_desc += 1

    # --- the icon set, stamped once and replaced rather than stacked
    s = re.sub(r'[ \t]*<link[^>]+rel="(?:icon|shortcut icon|apple-touch-icon)"[^>]*>\n?', '', s)
    m = re.search(r'(<link rel="canonical"[^>]*>\n)', s)
    if not m:
        m = re.search(r'(<meta[^>]+name="viewport"[^>]*>\n)', s)
    if not m:
        # a noindexed stub gets no canonical, and one of them carries no viewport
        # either, so fall back to the one tag every page is guaranteed to have
        m = re.search(r'(<title>.*?</title>\n)', s, re.S)
    if m:
        block = ''.join((t % BASE) + '\n' for t in ICONS)
        s = s[:m.end()] + block + s[m.end():]
        added_icons += 1

    # --- a social card only where the page has none of its own
    if p not in NOINDEX and 'og:image' not in s:
        card = ('<meta property="og:image" content="%sog-image.png">\n'
                '<meta name="twitter:image" content="%sog-image.png">\n'
                '<meta name="twitter:card" content="summary_large_image">\n') % (BASE, BASE)
        m = re.search(r'(<link rel="canonical"[^>]*>\n)', s)
        if m:
            s = s[:m.end()] + card + s[m.end():]
            added_card += 1

    # --- structured data, replaced rather than stacked
    s = re.sub(r'\n?<script type="application/ld\+json">.*?</script>', '', s, flags=re.S)
    if p not in NOINDEX:
        node = schema_for(p, s, url)
        if node:
            tag = ('<script type="application/ld+json">\n%s\n</script>\n'
                   % json.dumps(node, indent=2, ensure_ascii=False))
            m = re.search(r'(</head>)', s)
            if m:
                s = s[:m.start()] + tag + s[m.start():]
                added_ld += 1

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

print('structured data    : %d pages' % added_ld)
print('icon sets stamped  : %d' % added_icons)
print('social cards added : %d' % added_card)
print('pages moved to BASE: %d' % moved)
print('canonicals stamped : %d' % added_canon)
print('descriptions added : %d' % added_desc)
print('og:url normalised  : %d changed' % fixed_og)
print('noindex added      : %d (%s)' % (added_noindex, ', '.join(NOINDEX)))
print('sitemap.xml        : %d urls' % len(listed))
print('robots.txt         : written')
