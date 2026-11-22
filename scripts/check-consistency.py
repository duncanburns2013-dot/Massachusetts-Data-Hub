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
import datetime
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

    # CBP: every completed fiscal year in the feed. These rows were marked as
    # script-written in MASTER_DATA.md and no script owned them, so FY2026 sat at
    # 61,726 ('thru May 2026') while the feed held the full year at 98,705, and
    # FY2027 had no row at all. Nothing caught it because this list is explicit
    # and CBP was never added to it. Partial years are skipped: a month-to-date
    # total legitimately changes every release and would fail this check daily.
    # FY2024 and earlier are excluded because MASTER_DATA carries a DIFFERENT
    # measure for those years: OHSS total encounters (Border Patrol plus ports of
    # entry, FY2024 = 2,136,800), while this feed is Border Patrol only
    # (FY2024 = 1,530,523). CBP stopped publishing the ports-of-entry component
    # for FY2025+, which is why the two series only coexist up to FY2024.
    cbp = load('cbp-encounters-latest.json')['fy_totals']
    out += [(f'CBP {k} USBP southwest', money(v['total']), 'cbp-encounters-latest.json')
            for k, v in sorted(cbp.items())
            if v.get('months_reported') == 12 and k >= 'FY2025']

    # --- feed groups whose MASTER_DATA mark names a real script -------------------
    # Each of these had rows marked as script-written and sat outside this list, so
    # nothing compared them to the feed. Written as per-feed loops rather than one
    # entry per row: a new fiscal year or release month joins the check on its own.

    # BLS release dates. The dashboard once stamped 'Released <today>' from
    # new Date(), publishing a false provenance line on any non-release day, which
    # is why these dates are a feed at all.
    bls = load('bls-release-schedule.json')
    for series in ('employment_situation', 'state_employment'):
        for ref, rel in sorted(bls.get(series, {}).items()):
            d = datetime.date.fromisoformat(rel)
            out.append((f'BLS {series} {ref}', d.strftime('%b %d, %Y'),
                        'bls-release-schedule.json'))

    # CTHRU shelter actuals by fiscal year, written as $X.XXM in the register.
    imm = load('immigrant-spending-latest.json')['series']['by_fiscal_year']
    for fyr, v in sorted(imm.items()):
        a = v.get('shelter_system', {}).get('actual')
        if a:
            out.append((f'shelter actual FY{fyr}', f'${a / 1e6:,.2f}M',
                        'immigrant-spending-latest.json'))

    # EOHLC 3A headline counts.
    m3a = load('mbta-3a-latest.json')
    out += [(label, money(m3a[k]), 'mbta-3a-latest.json') for label, k in (
        ('3A communities', 'communities'),
        ('3A 2020 housing units', 'housing_units_2020'),
        ('3A required capacity', 'required_capacity'),
    ) if k in m3a]

    # Treasury gold, written in millions of fine troy ounces to one decimal.
    # PRIT and BEA RPP. Both were printed on a dashboard with no register row until
    # 2026-11-22, so nothing documented them and nothing compared them with the feed
    # they came from. Now registered, so the comparison can exist.
    prit = load('prit-latest.json')
    if prit.get('assets_billions'):
        out.append(('Total PRIT Fund assets',
                    f"${prit['assets_billions']}B", 'prit-latest.json'))
    col = load('cost-of-living-latest.json')
    _ma = ((col.get('rpp') or {}).get('MA') or {}).get('all')
    if _ma:
        out.append(('MA price level, all items, 2024', str(_ma),
                    'cost-of-living-latest.json'))

    gold = load('gold-reserve-latest.json')
    if gold.get('total_fine_troy_oz'):
        out.append(('gold total fine troy oz',
                    f"{gold['total_fine_troy_oz'] / 1e6:.1f}M", 'gold-reserve-latest.json'))

    # BLS levels. The feed stores these in THOUSANDS (3711, 7523) and the register
    # writes them out, which is why a raw string comparison missed them: the figures
    # agreed and the units did not. MA nonfarm matched all along; US job openings was
    # a month stale and 444k low, and nothing compared the two.
    e = load('employment-latest.json')
    out += [
        ('MA total nonfarm', money(e['ma_total_nonfarm']['latest']['value'] * 1000),
         'employment-latest.json'),
        ('US job openings', f"{e['us_job_openings']['latest']['value'] / 1000:.3f}M",
         'employment-latest.json'),
    ]

    # U-6 UNDERUTILISATION: the one employment figure with a live feed that
    # nothing writes into the page.
    #
    # data/u6-latest.json is regenerated daily by update-employment.yml, and
    # employment-dashboard.html carries the same numbers in hand-typed arrays.
    # 63 of that page's 67 substitution anchors are written by
    # fetch-bls-data.js; the four exceptions are all U-6 (@u6-u6, @u6-u3,
    # @u6-lf, @u6-lab). So a fresh feed sat beside a hand-typed copy of itself
    # with nothing comparing them -- they happened to agree on 2026-11-22, and
    # nothing would have said so had they stopped.
    #
    # Checked against the ANCHOR TAIL rather than the bare number: ",7.8/*@*/"
    # can only match the last element of the series the card reads, where
    # plain "7.8" would match any of a hundred figures on the page. Until the
    # anchors are wired to the feed, this is what makes the copy enforced
    # instead of hoped for.
    u6 = load('u6-latest.json')
    u6s = u6.get('series') or {}
    for name in ('U-3', 'U-6'):
        if isinstance(u6s.get(name), dict) and u6s[name].get('value') is not None:
            out.append((f'{name} MA, newest quarter (page array tail)',
                        f",{u6s[name]['value']}/*@*/", 'u6-latest.json'))
    _q = re.search(r'Q(\d) (\d{2})(\d{2})', (u6s.get('U-6') or {}).get('period', ''))
    if _q:
        out.append(('U-6 quarter label (page array tail)',
                    "'Q%s %s'/*@*/" % (_q.group(1), _q.group(3)), 'u6-latest.json'))


    # Statewide MLS, newest single-family year. mls-history.json is deliberately NOT
    # aged by check-freshness (only --backfill-history writes it), but whether the
    # register AGREES with it is a separate question, and that is what this asks.
    cells = load('mls-history.json')['cells']
    ma_sf = sorted(k for k in cells if k.startswith('ma|sf|'))
    if ma_sf:
        c = cells[ma_sf[-1]]
        out += [
            ('MLS statewide avg DOM', f"{c['avg_dom']} days", 'mls-history.json'),
            ('MLS statewide SP/LP', f"{c['sp_lp_pct']}%", 'mls-history.json'),
            ('MLS statewide units sold', money(c['count']), 'mls-history.json'),
            ('MLS statewide median price', f"${money(c['median_price'])}",
             'mls-history.json'),
        ]

    # IRS SoI, latest year only. The register's cumulative 2011-2024 sums are NOT
    # here: this feed carries one year, so those two rows need a multi-year source
    # and stay unchecked rather than being asserted against a number that cannot
    # support them. (They are re-derived by summing the dashboard's own 13 rows
    # whenever a year is added, which is the closest thing to a check they have.)
    #
    # results[0] is the newest year: update-irs-soi-migration.py sorts the list
    # newest-first for exactly this reason. Ordered the other way, this block would
    # check the register against the year the register had just moved off.
    #
    # Note on testing these: the net figure appears twice in the register, in the
    # row and in the prose below it, so editing one instance still passes. That is
    # this file's presence-check design, not a gap in this block: the failure mode
    # it exists for is the feed moving to a new year while the register does not,
    # and it catches that (verified by moving net_returns in the feed and watching
    # it go STALE).
    #
    # Outflow and inflow returns are checked because the register's prose restates
    # them. Without these, the net could be brought up to date while the sentence
    # under it kept the previous year's components, and the page would contradict
    # itself and still pass.
    res = load('irs-soi-migration-latest.json')['results']
    if res:
        r0 = res[0]
        out += [
            ('IRS net outflow returns', money(abs(r0['net_returns'])),
             'irs-soi-migration-latest.json'),
            ('IRS outflow returns', money(r0['outflow_returns']),
             'irs-soi-migration-latest.json'),
            ('IRS inflow returns', money(r0['inflow_returns']),
             'irs-soi-migration-latest.json'),
            ('IRS avg AGI leaving', f"${money(r0['avg_income_leaving'])}",
             'irs-soi-migration-latest.json'),
            ('IRS avg AGI arriving', f"${money(r0['avg_income_arriving'])}",
             'irs-soi-migration-latest.json'),
        ]

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

    mig = load('domestic-migration-latest.json')
    out.append(('Net domestic out-migration', money(mig['net_domestic_outmigration']),
                'domestic-migration-latest.json'))
    for comp, label in [('intl', 'Net international migration'),
                        ('netmig', 'Net migration'), ('popchg', 'Population change')]:
        if comp in mig.get('components', {}):
            out.append((label + ', cumulative',
                        money(sum(mig['components'][comp].values())),
                        'domestic-migration-latest.json'))

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
    L = lob['ledger_2026']
    # The hero figures. $104M sat here for the life of the page, in four places,
    # sourced nowhere -- the one thing a page arguing checkability cannot carry.
    out.append(('Hero: 2025 lobbying spend',
                f'${lob["comparison"]["2025_full_year"]["total"] / 1e6:.1f}M',
                'ma-lobbying-firms-latest.json'))
    out.append((f'MA lobbying fees to firms, {lob["year"]}',
                f'${L["clients_to_firms"] / 1e6:.1f}M',
                'ma-lobbying-firms-latest.json'))
    # The client side is the half of the ledger the page never had until 2026.
    # Both totals reconcile to the cent against what firms and lobbyists reported
    # RECEIVING, so a mismatch here means the page drifted, not the scrape.
    # Unformatted: the page carries these as a Chart.js data array, so that is the
    # form to look for. Checking the comma-grouped version would fail on a page
    # that is perfectly current.
    for c in lob['top_spenders'][:3]:
        out.append((f'Top spender #{c["rank"]} {c["name"][:20]}',
                    str(round(c['total'])), 'ma-lobbying-firms-latest.json'))

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
             (REPO / 'pay-to-play-dashboard.html').read_text(encoding='utf-8', errors='replace'),
             'u6-latest.json':
             (REPO / 'employment-dashboard.html').read_text(encoding='utf-8', errors='replace')}

    # BOUND TO A LINE, NEVER TO THE FILE  (changed 2026-11-22)
    #
    # This loop used to read `ok = value in pages.get(src, text)` -- a substring
    # search over the WHOLE of MASTER_DATA.md. `label` was printed and then
    # thrown away, so a figure counted as agreeing with its feed whenever its
    # digits appeared ANYWHERE in the register: any row, any subject, any year.
    #
    # That is not a theoretical hole. On 2026-11-22 the register carried
    #   | MA unemployment rate | 4.3% | September 2026 |
    # while the feed and BLS both said 4.2% for October. This check printed
    # "MA unemployment rate   4.2%  ok". The string "4.2%" does occur in
    # MASTER_DATA.md -- in the Greater Boston row, as a HOME PRICE CHANGE
    # (+4.2%), and again in a 2025 job-openings rate. A median house price was
    # standing in as proof that the unemployment rate was current.
    #
    # Three further rows held OCTOBER values stamped SEPTEMBER at that same
    # moment (labor force 3,886,370; level 164,934; nonfarm 3,715,000) and every
    # one passed. 74 figures reported as matching their source, bound to nothing
    # but the presence of their own digits somewhere in a 4,000-line file.
    #
    # A figure is now bound in one of two ways, tried in order:
    #
    #   1. ROW NAME -- a table row whose first cell is, or begins with, the
    #      label. The strongest binding, and the one to prefer when adding a
    #      check: give it the register's own row name.
    #   2. SAME LINE -- a line carrying both the value AND a distinctive word
    #      from the label. Most feed figures live in tables keyed by year or
    #      region ("| NH Statewide | $447,710 | ..."), where the label is a
    #      column heading and no first cell can ever match it. Requiring the
    #      value and the figure's own name on ONE line still ties the number to
    #      its subject, which is the property that was missing.
    #
    # Neither tier falls back to the whole file. A figure nothing can bind is a
    # failure, not a pass: it means the value is gone from the register, or the
    # row was renamed, or the label never named anything.
    #
    # PAGE-sourced rows are checked against that one dashboard, as before. Their
    # labels are built from feed data and are not row names ("Lobbying #1 Smith
    # Costello & Crawf" is truncated to fit the column), and the haystack is a
    # single page rather than the register.
    GENERIC = {'the', 'and', 'for', 'latest', 'actual', 'label', 'total',
               'year', 'cumulative', 'per'}

    def label_words(lab):
        """The words of a label that identify its subject, lowercased."""
        return [w for w in re.findall(r"[A-Za-z0-9#&/_-]{2,}", lab)
                if w.lower() not in GENERIC]

    rowidx = {}
    for _line in text.split(chr(10)):
        if not _line.startswith('|'):
            continue
        _cells = [c.strip() for c in _line.strip().strip('|').split('|')]
        if _cells:
            rowidx.setdefault(_cells[0].strip('*` '), []).append(_line)
    reg_lines = text.split(chr(10))

    def bind(lab, val):
        """(status, how) -- where the register backs this figure, if anywhere."""
        named = [ln for name, lns in rowidx.items()
                 if name == lab or name.startswith(lab) for ln in lns]
        if named:
            return ('ok' if any(val in ln for ln in named) else 'STALE'), 'row'
        words = [w.lower() for w in label_words(lab)]
        if words:
            for ln in reg_lines:
                low = ln.lower()
                if val in ln and any(w in low for w in words):
                    return 'ok', 'line'
        return 'STALE', 'none'

    stale = []
    for label, value, src in rows:
        if src in pages:
            status, how = ('ok' if value in pages[src] else 'STALE'), 'page'
        else:
            status, how = bind(label, value)
        if status != 'ok':
            stale.append((label, value, src))
        print(f'{label.ljust(width)}  {value:>14}  {status:7s}  {how:5s}  {src}')

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

    print(f'\nAll {len(rows)} feed-backed figures match their source,')
    print('each bound to a register line that names it, or to the page that publishes it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
