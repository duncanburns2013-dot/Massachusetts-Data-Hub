# -*- coding: utf-8 -*-
"""Stamp a "how this is sourced" strip onto each dashboard, pointing at Method.

Method is the most defensible page on the site and nothing linked to it. It sat
in the nav and nowhere else, so the answer to "where did that number come from"
was three clicks away from the number.

This is a stamper rather than sixteen hand edits because the dashboards have no
shared footer or nav to hang it on - they were built at different times and link
back to the hub with different wording, or not at all. One place to maintain,
re-runnable, fenced.

A dashboard is only linked to a section that actually documents it. All sixteen
are documented now; anything added later that is not belongs in UNDOCUMENTED
until it is, because linking "how this is sourced" to a page that does not
source it is worse than not linking at all.
"""
import io, os, re, sys, glob

NL = chr(10)
BASE = 'method.html'

# dashboard -> the Method section that documents its figures
SECTION = {
    'immigration-dashboard.html':      ('immigration',                          'Immigration'),
    'ma-housing-dashboard.html':       ('housing-real-estate',                  'Housing &amp; Real Estate'),
    'nh-housing-dashboard.html':       ('housing-real-estate',                  'Housing &amp; Real Estate'),
    'haverhill-market-report.html':    ('housing-real-estate',                  'Housing &amp; Real Estate'),
    'commercial-re-dashboard.html':    ('housing-real-estate',                  'Housing &amp; Real Estate'),
    'affordability-dashboard.html':    ('cost-of-living',                       'Cost of Living'),
    'employment-dashboard.html':       ('employment-labor',                     'Employment &amp; Labor'),
    'education-statewide.html':        ('education',                            'Education'),
    'education-merrimack-valley.html': ('education',                            'Education'),
    'healthcare-dashboard.html':       ('healthcare-insurance',                 'Healthcare &amp; Insurance'),
    'tax-budget-dashboard.html':       ('state-budget-the-scope-reconciliation', 'State Budget'),
    'tax-burden-dashboard.html':       ('tax-burden-federal-massachusetts',     'Tax Burden'),
    'energy-dashboard.html':           ('energy',                               'Energy'),
    'pension-dashboard.html':          ('pensions',                             'Pensions'),
    'pay-to-play-dashboard.html':      ('lobbying-political-spending',          'Lobbying &amp; Political Spending'),
    'all-things-boston.html':          ('boston',                               'Boston'),
}

# every dashboard is documented now; anything added here that has no section in
# MASTER_DATA.md belongs in this tuple until it does, because linking "how this
# is sourced" to a page that does not source it is worse than not linking
UNDOCUMENTED = ()

F0, F1 = '<!-- == method-link start == -->', '<!-- == method-link end == -->'

CSS = """<style>
/* Sourced-here strip. Uses the shared theme's own tokens so it reads as part of
   whichever dashboard it lands on, and stays quiet: this is a way out to the
   working, not a call to action. */
.msrc{max-width:1560px;margin:44px auto 0;padding:16px 24px 0;
  border-top:1px solid var(--rule,#CDD3D1);
  font-family:var(--font-mono,ui-monospace,monospace);font-size:11.5px;
  letter-spacing:.04em;color:var(--muted,#5A6467);text-align:center}
.msrc a{color:var(--navy,#14558F);font-weight:600;text-decoration:none;
  border-bottom:1px solid rgba(20,85,143,.35)}
.msrc a:hover{border-bottom-color:var(--navy,#14558F)}
.msrc a:focus-visible{outline:2px solid var(--navy,#14558F);outline-offset:3px}
</style>"""


def strip_for(anchor, label):
    return (
        '<p class="msrc">Every figure on this page is listed with its source in the '
        '<a href="%s#%s">%s section of the method</a>.</p>' % (BASE, anchor, label))


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    stamped = skipped = 0

    for page in sorted(glob.glob('*.html')):
        if page not in SECTION:
            continue
        s = orig = io.open(page, encoding='utf-8').read()
        anchor, label = SECTION[page]

        block = F0 + NL + CSS + NL + strip_for(anchor, label) + NL + F1 + NL
        if F0 in s:
            a = s.index(F0)
            b = s.index(F1) + len(F1) + 1
            s = s[:a] + block + s[b:]
        else:
            if '</body>' not in s:
                sys.exit('no </body> in ' + page)
            s = s.replace('</body>', block + '</body>', 1)
        if s != orig:
            io.open(page, 'w', encoding='utf-8', newline=NL).write(s)
        stamped += 1

    for page in UNDOCUMENTED:
        if os.path.exists(page):
            skipped += 1

    print('method links stamped : %d dashboards' % stamped)
    if skipped:
        print('left unlinked        : %d (%s)' % (skipped, ', '.join(UNDOCUMENTED)))
        print('  no section in MASTER_DATA.md yet; write one and map it above')
    else:
        print('left unlinked        : none, every dashboard is documented')

    # every anchor pointed at must exist on the built page
    m = io.open(BASE, encoding='utf-8').read()
    missing = sorted({a for a, _ in SECTION.values() if 'id="%s"' % a not in m})
    if missing:
        sys.exit('anchors missing from %s: %s' % (BASE, ', '.join(missing)))
    print('anchors verified     : all %d resolve in %s' % (len({a for a, _ in SECTION.values()}), BASE))


if __name__ == '__main__':
    main()
