#!/usr/bin/env python3
"""Render the lobbying tables on shelter-immigrant-spending.html from the feed.

WHY
data/lobbying-immigration-latest.json is the verified copy: every figure in it
was read from the Secretary of the Commonwealth's Lobbyist Public Search on
2026-10-21 and reconciled, including the one the first read dropped (Laura
Rotolo, $12,500, lost to an accented character and caught only because the
named amounts summed $12,500 short of the registry's own salary line).

The page then carried all of it a second time, typed by hand. Both copies
agree today. Two hand-kept copies of 53 figures agreeing is luck, and the same
arrangement on the immigration dashboard is where a corrected figure survived
in four cells that nobody thought to re-add.

The registry blocks server-side fetches, so topping up the JSON stays a human
job done in a browser. Rendering it does not.

Idempotent.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "lobbying-immigration-latest.json")
PAGE = os.path.join(ROOT, "shelter-immigrant-spending.html")

ROW = '<tr><td>{a}</td><td class="num">{b}</td></tr>'
ROW_SEMI = ('<tr><td style="font-weight:600">{a}</td>'
            '<td class="num" style="font-weight:600">{b}</td></tr>')
ROW_BOLD = ('<tr><td style="font-weight:700">{a}</td>'
            '<td class="num" style="font-weight:700">{b}</td></tr>')
MUTED = ' style="color:var(--muted)"'


def money(v, cents=True):
    return f"${v:,.2f}" if cents else f"${v:,.0f}"


def now_block(ent, period_label):
    """The current filing period: named lobbyists, salaries, firm, expenses."""
    out = []
    for p in ent.get("lobbyists", []):
        if p.get("amount"):
            out.append(ROW.format(a=p["name"], b=money(p["amount"])))
    out.append(ROW_SEMI.format(a="Salaries", b=money(ent["salaries"])))
    if ent.get("entity_paid"):
        out.append(ROW.format(a=ent["entity_paid"],
                              b=money(ent["entity_payments"])))
    out.append(ROW.format(a="Expenses", b=money(ent["expenses_total"])))
    out.append(ROW_BOLD.format(a=period_label, b=money(ent["total"])))
    return out


def years_block(ent, with_firm):
    """Every year in sequence, including the ones with no filing.

    A year with no filing is not a year with no row: absence is not zero, and
    a silent gap reads as one. The no-registration rows are interleaved in
    date order rather than appended, because a 2021 row printed after 2025
    looks like a footnote instead of a gap in the middle of the series.
    """
    rows = []
    for y in ent.get("prior_years", []):
        rows.append((y["year"], "filed", y))
    for y in ent.get("no_registration_years", []):
        rows.append((y, "none", None))
    out = []
    for year, kind, y in sorted(rows, key=lambda r: r[0]):
        if kind == "none":
            span = ' colspan="2"' if with_firm else ""
            out.append(
                '<tr><td{m}>{y}</td><td class="num"{s}{m2}>'
                'no registration found</td></tr>'.format(
                    y=year, m=MUTED, s=span,
                    m2=' style="color:var(--muted);font-size:.74rem"'))
        elif with_firm:
            out.append(
                '<tr><td>{y}</td><td class="num">{t}</td>'
                '<td class="num"{m}>{f}</td></tr>'.format(
                    y=year, t=money(y["total"], cents=False), m=MUTED,
                    f=money(y.get("entity_payments", 0), cents=False)))
        else:
            out.append(ROW.format(a=year, b=money(y["total"], cents=False)))
    return out


def replace(html, tag, rows):
    start = f"<!-- BEGIN owned:stamp-lobbying.py {tag} -->"
    end = f"<!-- END owned:stamp-lobbying.py {tag} -->"
    if start not in html or end not in html:
        return html, f"{tag} markers missing"
    pre, rest = html.split(start, 1)
    _old, post = rest.split(end, 1)
    return pre + start + "\n" + "\n".join(rows) + "\n" + end + post, None


def main():
    with open(FEED, encoding="utf-8") as fh:
        feed = json.load(fh)
    mira = feed["entities"]["mira"]
    aclu = feed["entities"]["aclu"]
    label = ("Total, first half " + str(mira["registration_year"])
             if feed.get("period_is_partial_year")
             else "Total, " + str(mira["registration_year"]))

    with open(PAGE, encoding="utf-8") as fh:
        html = fh.read()

    errs = []
    for tag, rows in (("MIRA-NOW", now_block(mira, label)),
                      ("MIRA-YEARS", years_block(mira, with_firm=True)),
                      ("ACLU-NOW", now_block(aclu, label)),
                      ("ACLU-YEARS", years_block(aclu, with_firm=False))):
        html, err = replace(html, tag, rows)
        if err:
            errs.append(err)
        else:
            print(f"  {tag:<12} {len(rows)} rows")
    if errs:
        print("  " + "; ".join(errs))
        return 1

    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(html)

    # Reconciliation, not decoration: the named amounts must sum to the salary
    # line the registry states. That check is what caught the dropped lobbyist.
    bad = 0
    for name, ent in (("MIRA", mira), ("ACLU", aclu)):
        s = sum(p.get("amount", 0) for p in ent.get("lobbyists", []))
        if abs(s - ent["salaries"]) > 0.01:
            print(f"  WARNING: {name} named lobbyists sum to ${s:,.2f} but "
                  f"the registry states salaries of ${ent['salaries']:,.2f}")
            bad += 1
        parts = ent["salaries"] + ent["entity_payments"] + ent["expenses_total"]
        if abs(parts - ent["total"]) > 0.01:
            print(f"  WARNING: {name} parts sum to ${parts:,.2f} against a "
                  f"stated total of ${ent['total']:,.2f}")
            bad += 1
    if bad:
        return 1
    print("  both filings reconcile: named amounts to salaries, "
          "parts to totals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
