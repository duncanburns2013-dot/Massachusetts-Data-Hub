#!/usr/bin/env python3
"""Write MIRA's lobbying-by-year cards from the verified registry file.

WHY THIS REPLACED WHAT WAS THERE
The dashboard listed four named lobbyists for 2022-2025:

  Amy M. Grunder $61,132 + Charles Group $20,000
  + Edwin Jonathan Paz $4,626 + Elizabeth Sweet $1,790  =  $87,548

That sum is the figure retired on 2026-10-21. It was salaries only for four of
six years: it left out the Charles Group retainer in every year but 2022, every
reported expense, and the 2020 filing entirely, understating the money more
than fivefold. data/retired-figures.json could not catch it because no cell on
the page held $87,548 -- only the four cells that add up to it did. A retired
figure split across four cells is still the retired figure.

What replaces it is each registration year's own summary total from the
Secretary of the Commonwealth: salaries, payments to outside firms and
reported expenses together, which is the basis the $451,299 headline uses, so
the cards and the headline now reconcile.

The registry blocks server-side fetches, so data/lobbying-immigration-latest.json
is read by hand from a browser session. This only renders it.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "lobbying-immigration-latest.json")
PAGE = os.path.join(ROOT, "immigration-dashboard.html")
START = "<!-- BEGIN owned:stamp-mira-lobbying.py MIRA-LOBBY -->"
END = "<!-- END owned:stamp-mira-lobbying.py MIRA-LOBBY -->"

CARD = ('          <div class="lobbyist-card"><div>'
        '<div class="lobbyist-name">{name}</div>'
        '<div class="lobbyist-years">{sub}</div></div>'
        '<div class="lobbyist-amount">{amt}</div></div>')


def main():
    with open(FEED, encoding="utf-8") as fh:
        feed = json.load(fh)
    mira = feed["entities"]["mira"]

    years = []
    for y in mira.get("prior_years", []):
        years.append((y["year"], y["total"], "full year"))
    # The current period is partial and must say so on the card; comparing a
    # half-year against full years without labelling it is what the prose
    # under this grid used to do.
    years.append((mira["registration_year"], mira["total"],
                  "Jan–Jun only" if feed.get("period_is_partial_year")
                  else "full year"))
    years.sort()

    gap = set(mira.get("no_registration_years", []))
    cards = []
    for y, total, sub in years:
        cards.append(CARD.format(name=str(y), sub=sub,
                                 amt="${0:,.0f}".format(total)))
    for y in sorted(gap):
        # Absence is not zero, and it is not a gap in our data either: a broad
        # search of that registration year returned no MIRA record while
        # ACLU-MA's filing for the same year is present.
        cards.append(CARD.format(
            name=str(y), sub="no registration filed",
            amt="—"))
    cards.sort(key=lambda c: c)

    grand = sum(t for _y, t, _s in years)
    cards.append(
        '          <div class="lobbyist-card" style="border-color:var(--navy)">'
        '<div><div class="lobbyist-name"><strong>Total</strong></div>'
        '<div class="lobbyist-years">{0}–{1}, as the registry totals it'
        '</div></div><div class="lobbyist-amount"><strong>${2:,.0f}</strong>'
        '</div></div>'.format(years[0][0], years[-1][0], grand))

    with open(PAGE, encoding="utf-8") as fh:
        html = fh.read()
    if START not in html or END not in html:
        print("  MIRA-LOBBY markers not found in the page")
        return 1
    pre, rest = html.split(START, 1)
    _old, post = rest.split(END, 1)
    html = pre + START + "\n" + "\n".join(cards) + "\n          " + END + post

    # The two figures the prose beside this grid compares, so it cannot drift
    # from the cards above it.
    cur = [t for y, t, _s in years if y == mira["registration_year"]]
    prev_full = [t for y, t, s in years
                 if s == "full year" and y < mira["registration_year"]]
    fields = {}
    if cur:
        fields["mira-2026-h1"] = "${0:,.0f}".format(cur[0])
    if prev_full:
        fields["mira-2025-full"] = "${0:,.0f}".format(prev_full[-1])
    import re
    missing = []
    for tag, val in fields.items():
        pat = r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)'
        html, n = re.subn(pat, lambda m: m.group(1) + val + m.group(2), html)
        if n == 0:
            missing.append(tag)

    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  wrote {len(cards)} lobbying cards, total ${grand:,.0f}")
    if missing:
        print("  WARNING: data-field missing: " + ", ".join(missing))
    headline = mira.get("prior_years_total_full", 0) + mira.get("total", 0)
    if abs(headline - grand) > 1:
        print(f"  WARNING: cards sum to ${grand:,.0f} but the file's own "
              f"totals give ${headline:,.0f}")
        return 1
    print(f"  reconciles to the published headline: ${grand:,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
