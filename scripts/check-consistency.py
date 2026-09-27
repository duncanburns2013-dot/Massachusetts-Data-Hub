#!/usr/bin/env python3
"""Fail when MASTER_DATA.md contradicts the feeds it claims to mirror.

WHY THIS EXISTS
check-freshness.py asks "is this source old?". It cannot ask the question that
actually bit: does what we PUBLISH agree with what we FETCHED?

MASTER_DATA.md marks rows with a 🔄 meaning "a workflow owns this number". No
workflow does. It is hand-kept, and build_method.py turns it into method.html,
which no workflow runs either. So the documentation layer drifts away from the
dashboards silently and method.html republishes the drift as if verified.

On 2026-09-26 the whole chain was a full EIA release behind while every job was
green and every freshness age was inside its limit:

    method.html said   EIA May 2026, MA 28.82c, US 18.44c
    the dashboards had EIA Jun 2026, MA 29.61c, US 18.34c
    MASTER_DATA said   NH median $441,616   (feed said $444,695)
    MASTER_DATA said   MA unemployment 4.4% (feed said 4.3%)

Nothing was broken. Every number was simply typed once and never re-typed. That
is invisible to an age check, because the FILE is fresh -- it is the CLAIM that
is stale.

So this compares the live JSON against the text of MASTER_DATA.md and fails when
a feed-backed figure is not found there. It deliberately checks presence of the
current value rather than parsing the table: the tables are hand-formatted and
vary, but a figure that is genuinely current will appear somewhere, and one that
has drifted will not appear at all.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MASTER = REPO / 'MASTER_DATA.md'


def money(v):
    return f'{round(v):,}'


def load(name):
    return json.loads((REPO / 'data' / name).read_text())


def checks():
    """(label, expected-string, why) for every figure a feed owns."""
    out = []

    nh = load('nh-figures.json')
    sw = nh['markets']['NH Statewide']
    out += [
        ('NH statewide median sale', money(sw['median_sale']), 'nh-figures.json'),
        ('NH statewide avg sale', money(sw['avg_sale']), 'nh-figures.json'),
        ('NH active listings', money(sw['active_count']), 'nh-figures.json'),
    ]

    emp = load('employment-latest.json')
    lat = {k: v['latest'] for k, v in emp.items()
           if isinstance(v, dict) and isinstance(v.get('latest'), dict)}
    for key, label, fmt in [
        ('ma_unemployment_rate', 'MA unemployment rate', lambda v: f'{v:.1f}%'),
        ('us_unemployment_rate', 'US unemployment rate', lambda v: f'{v:.1f}%'),
        ('ma_unemployment_level', 'MA unemployment level', money),
        ('ma_labor_force', 'MA labor force', money),
    ]:
        if key in lat:
            out.append((label, fmt(lat[key]['value']), 'employment-latest.json'))

    cen = load('census-latest.json')
    if 'ma_median_hh_income' in cen:
        out.append(('MA median household income',
                    money(cen['ma_median_hh_income']), 'census-latest.json'))

    irs = load('irs-soi-migration-latest.json')
    if irs.get('results'):
        r = irs['results'][0]
        out.append(('IRS net AGI, latest year',
                    f'{abs(r["net_agi_billions"])}', 'irs-soi-migration-latest.json'))

    # Lobbying: the dashboard is hand-kept, and its source cannot be fetched by
    # any workflow (the SOS blocks servers), so the JSON is the only record of
    # what was actually scraped. Check the PAGE against it -- that is the pair
    # that silently drifted before, when a 2015-2025 cumulative ranking was
    # published in a card row that read as current.
    lob = load('ma-lobbying-firms-latest.json')
    for f in lob['top_firms'][:4]:
        out.append((f'Lobbying #{f["rank"]} {f["name"][:22]}',
                    f'${f["received"] / 1e6:.1f}M',
                    'ma-lobbying-firms-latest.json'))
    out.append(('MA lobbying fees, 2025 total',
                f'${lob["totals"]["fees_received"] / 1e6:.1f}M',
                'ma-lobbying-firms-latest.json'))

    # Electricity lives in the dashboard, not a JSON file: update-energy-dashboard.py
    # writes the page directly. Read it back from there so the comparison is against
    # what readers actually see.
    energy = (REPO / 'energy-dashboard.html').read_text(encoding='utf-8', errors='replace')
    m = re.search(r'MA residential rate: <strong>([\d.]+)', energy)
    if m:
        out.append(('MA residential electricity', m.group(1), 'energy-dashboard.html'))
    m = re.search(r'national average: ([\d.]+)', energy)
    if m:
        out.append(('US residential electricity', m.group(1), 'energy-dashboard.html'))
    m = re.search(r'EIA ([A-Z][a-z]{2} 20\d{2})', energy)
    if m:
        out.append(('EIA vintage label', m.group(1), 'energy-dashboard.html'))

    return out


def main():
    text = MASTER.read_text(encoding='utf-8')
    rows = checks()
    width = max(len(c[0]) for c in rows)

    print(f'{"figure".ljust(width)}  {"live value":>14}  status   source')
    print('-' * (width + 46))

    # Most rows are MASTER_DATA.md claims. The lobbying rows are claims made by
    # pay-to-play-dashboard.html itself, so each row is checked against the file
    # that publishes it.
    pages = {'ma-lobbying-firms-latest.json':
             (REPO / 'pay-to-play-dashboard.html').read_text(encoding='utf-8', errors='replace')}

    stale = []
    for label, value, src in rows:
        ok = value in pages.get(src, text)
        if not ok:
            stale.append((label, value, src))
        print(f'{label.ljust(width)}  {value:>14}  '
              f'{"ok" if ok else "STALE":7s}  {src}')

    if stale:
        print(f'\n{len(stale)} published figure(s) no longer match the feed:\n')
        for label, value, src in stale:
            where = 'pay-to-play-dashboard.html' if src in pages else 'MASTER_DATA.md'
            print(f'  {label}: feed says {value} ({src}), {where} does not contain it')
        if any(src not in pages for _, _, src in stale):
            print('\nMASTER_DATA.md generates method.html via build_method.py, so this drift is')
            print('published as documented fact. Re-sync the rows, then regenerate:')
            print('    python3 build_method.py')
        if any(src in pages for _, _, src in stale):
            print('\nThe rows above are published directly by a dashboard, not by MASTER_DATA.md.')
            print('Re-sync the figures in that page against the JSON named beside each one.')
        return 1

    print(f'\nAll {len(rows)} feed-backed figures match their source.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
