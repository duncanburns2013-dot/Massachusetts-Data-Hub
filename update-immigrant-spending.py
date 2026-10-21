#!/usr/bin/env python3
"""Massachusetts spending on immigrant, refugee and family-shelter programs.

WHAT THIS IS
Two questions, from two CTHRU datasets, both keyed on the SAME appropriation
accounts so the answers cannot drift apart:

  how much   kv7m-35wn  Budget vs Actual -- enacted appropriation and actual
                        expenses, per account per fiscal year
  to whom    pegc-naaa  Comptroller spending -- every payment, with the vendor
                        it went to. Its create_date moves daily.

WHY BY APPROPRIATION, NOT BY VENDOR NAME
The earlier version of this analysis (duncanburns2013-dot/The-Invasion) built
its vendor list by matching names against substrings -- IMMIGRANT, REFUGEE,
MIRA, NEIGHBOR -- and its own README documents what that caught: the three
largest "immigrant vendors" were East Boston Neighborhood Health Center
($59.2M), Brockton Neighborhood Health Center ($58.6M) and NeighborHealth
($45.4M), federally qualified health centres billing MassHealth for every
patient. They matched on NEIGHBOR. MIRA matched a dentist (Paul F. Miraglia
D.D.S.), a daycare (Mini Miracles), Amirah Inc, and two people named Miranda.
Of $228.6M so collected, $179.3M (78.4%) was MassHealth claims.

Classifying by APPROPRIATION asks what the money was appropriated to do, which
is the Commonwealth's own answer and not ours. The accounts below were found by
searching appropriation_account_name for the purpose words, so the list is the
state's naming, auditable by re-running that search.

TWO TIERS, NEVER ONE BLENDED NUMBER
  tier 1  accounts whose own name identifies an immigrant, refugee or family
          shelter purpose. This is the defensible headline.
  tier 2  MRVP and RAFT -- general rental assistance, not immigrant-designated.
          Real housing money, but folding it into tier 1 would repeat exactly
          the overreach the NEIGHBOR match made. Published separately, labelled.

WHAT THIS DELIBERATELY DOES NOT CLAIM
  - Tax status. CTHRU gives a vendor name, not a 501(c)(3) determination. Legal
    suffixes are recorded as a HINT and nothing here asserts an organisation is
    a non-profit; that needs the IRS Business Master File and is a separate
    pass. `nonprofit_verified` is false on every row until it is done.
  - MassHealth claims and SNAP/EBT. Those are individual-level and federally
    protected, so no public record itemizes them by recipient. The page states
    that boundary rather than substituting a model for it.
  - SUMMARY PAYROLL rows are state agency payroll (MIL, OCD, DSS, DPH, ORI),
    not organisations receiving grants. Separated, never listed as recipients.

Exit 75 (EX_TEMPFAIL) when CTHRU does not answer: a neutral skip that leaves
the published figures alone, per the convention the other updaters here use.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "immigrant-spending-latest.json")
UA = {"User-Agent": "MA-Data-Hub/1.0 (+https://massachusettsdatahub.com)"}

DOMAIN = "https://cthru.data.socrata.com/resource"
BUDGET = f"{DOMAIN}/kv7m-35wn.json"     # enacted vs actual
SPEND = f"{DOMAIN}/pegc-naaa.json"      # the checkbook

EXIT_BLOCKED = 75

# The search that produces this list. Re-run it to audit the list; it is the
# state's naming, not ours.
#
# IMMIGRA, not IMMIGRAN: the original term matched "Immigrant" and "Immigrants"
# and silently missed "Immigration", which cost the headline the Immigration
# Legal Assistance Fund (4003-0124, $6,355,787 FY22-27). A substring that
# matches one word form of a purpose and not another is not a search, and the
# only reason it was found is that another page on this hub carried the
# account and the two disagreed.
SEARCH_TERMS = ["IMMIGRA", "REFUGEE", "ASYLUM", "SHELTER", "CITIZENSHIP",
                "MIGRANT", "RESETTLE", "EMERGENCY ASSISTANCE", "HOUSING TRANS",
                "NEW AMERICAN", "UNACCOMPANIED", "HOMELESS"]

# Accounts the search returns that are deliberately NOT in tier 1, with the
# reason, because an exclusion nobody can see is indistinguishable from an
# oversight -- which is what 4003-0124 turned out to be. Published on the page.
EXCLUDED = {
    "70040102": ("Homeless Individuals Assistance", "general homelessness"),
    "50462000": ("Services to the Homeless Mentally Ill", "general homelessness"),
    "70350008": ("Homeless Student Transportation", "general homelessness"),
    "70350005": ("Homeless Student Transportation", "general homelessness"),
    "70040100": ("Operation of Homeless Programs", "general homelessness"),
    "40000007": ("Unaccompanied Homeless Youth Services", "general homelessness"),
    "70040202": ("Homeless Individuals Rapid Re-Housing", "general homelessness"),
    "14100250": ("Assistance to Homeless Veterans", "general homelessness"),
    "70040106": ("Homeless Family Preference in Private Multi-Family",
                 "general family homelessness, not the EA shelter system"),
    "91101700": ("Elder Homeless Placement", "general homelessness"),
    "15990017": ("End Family Homelessness Reserve Fund",
                 "general family homelessness, not the EA shelter system"),
    "15991004": ("Commission to End Homelessness Recommendations Reserve",
                 "general homelessness"),
    "70040002": ("Friends of the Homeless (Springfield)", "general homelessness"),
    "05242022": ("New American Voters Grant Program",
                 "voter registration, not an immigrant service or shelter"),
}
EXCLUDED_REASON = (
    "These accounts match the purpose-word search but are general homelessness "
    "programs, not immigrant-designated ones. They carry $939M in FY2022-FY2027 "
    "spending between them. Folding that into an immigrant-spending headline "
    "would repeat exactly the overreach this page was built to avoid -- the "
    "earlier version of this analysis counted three federally qualified health "
    "centres as immigrant vendors because their names contained NEIGHBOR. A "
    "homeless shelter is not an immigrant program because both involve shelter.")

TIER1 = {
    "15990122": "Immigrants and Refugees Housing Reserve",
    "15990514": "Family Shelter and Services Reserve",
    "15990924": "Immigration and Refugee Reserve",
    "15990925": "Immigrants and Refugees Supports Reserve",
    "15991213": "Family Shelter and Services Reserve",
    "15992625": "Family Shelter / Supplemental Shelter Costs Reserve",
    "40030111": "Office of Refugees and Immigrants Administration",
    "40030122": "Low-Income Citizenship Program",
    "40030123": "For Resettlement Agencies",
    "40030124": "Immigration Legal Assistance Fund",
    "44032120": "For Family Shelter / Transitional Housing",
    "70040101": "Emergency Assistance - Family Shelters and Services",
    "70040103": "Homeless Family EA Shelter Overflow - Hotels and Motels",
    "70040108": "MA Short-Term Housing Transition Program (HomeBASE)",
    "70040109": "Shelter Workforce Assistance",
    "70040110": "Family Shelter Diversion",
}

# General rental assistance. NOT immigrant-designated -- that is the whole
# reason it is a separate tier.
TIER2 = {
    "70049024": "MRVP rental vouchers",
    "70049316": "RAFT / Homeless Housing (rental and mortgage aid)",
}

FIRST_FY = 2022

# The two series the immigration dashboard and MASTER_DATA.md publish by name.
# They were hand-maintained until 2026-10-21 and had drifted: the register
# carried HomeBASE FY26 at $91.35M "verified against CTHRU" when CTHRU says
# $57.29M, and explained the $34.07M gap as a transfer when CTHRU's own
# transfer_in for that account and year is $2,575. The gap was in fact the
# difference between an appropriation and a figure taken from a different
# source (the FY27 budget documents' FY26 projected column). Nothing checked
# it, so it survived six weeks and reached three pages. These are now written
# from CTHRU by this script and must not be edited by hand.
SHELTER_SYSTEM = ["70040101", "70040108", "70040109", "70040110",
                  "15990514", "15991213", "15992625", "15990122", "15990925"]
EA_LINE = "70040101"
HOMEBASE = "70040108"

# Agency payroll, not grant recipients. CTHRU files these as vendors.
PAYROLL_MARK = "SUMMARY PAYROLL"


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def blocked(msg):
    print(f"\n{msg}")
    print("Nothing written; the published figures stand. Exit 75 = neutral skip.")
    sys.exit(EXIT_BLOCKED)


def get(url, tries=3):
    """Socrata JSON, retried. A transient wobble must not look like no data."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                      # TimeoutError is not a URLError
            last = e
            if attempt < tries - 1:
                import time
                time.sleep(4 * (attempt + 1))
    blocked(f"CTHRU did not answer after {tries} tries: {type(last).__name__}: {last}")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def fy_of(row):
    try:
        return int(float(row.get("fiscal_year")))
    except (TypeError, ValueError):
        return None


def quoted(codes):
    return ",".join(f"'{c}'" for c in codes)


def check_account_coverage():
    """Re-run the purpose-word search and account for every hit.

    The list of accounts was written once and then trusted. When the search
    term was wrong, nothing noticed for as long as the list sat there -- an
    account can only go missing silently if nobody re-runs the search. This
    runs it every time and refuses to publish if an account turns up that is
    in neither tier nor the excluded register.

    New accounts appear in the real world: the Immigration Legal Assistance
    Fund has rows only from FY2026. A list that is never re-derived goes out of
    date by sitting still.
    """
    seen = {}
    for term in SEARCH_TERMS:
        qs = urllib.parse.urlencode({
            "$select": "appropriation_account_number,appropriation_account_name",
            "$where": (f"upper(appropriation_account_name) like '%{term}%' "
                       f"AND fiscal_year>={FIRST_FY}"),
            "$limit": "5000",
        })
        for r in get(f"{BUDGET}?{qs}"):
            acct = (r.get("appropriation_account_number") or "").strip()
            if acct:
                seen[acct] = (r.get("appropriation_account_name") or "").strip()
    known = set(TIER1) | set(TIER2) | set(EXCLUDED)
    new = {k: v for k, v in seen.items() if k not in known}
    print(f"\n  account coverage: {len(seen)} accounts match the purpose words; "
          f"{len(TIER1)} tier 1, {len(TIER2)} tier 2, {len(EXCLUDED)} excluded")
    if new:
        lines = "\n  ".join(f"{k}  {v}" for k, v in sorted(new.items()))
        blocked("the purpose-word search returned accounts that are in no "
                "tier and in no excluded register. Each needs a decision "
                "recorded in this script before the figures can be "
                f"republished:\n  {lines}")
    return seen


def build_series(rows, newest):
    """The published shelter series, per fiscal year, straight off CTHRU.

    Three measures, each with its account set stated so a reader can re-run it:
    the shelter system (nine accounts, reserves included), the EA line alone,
    and HomeBASE alone. transfer_in is carried because the register once
    asserted a transfer that the field does not show.
    """
    years = sorted({fy for (_a, fy) in rows}, key=int)
    out = {}
    for fy in years:
        def agg(codes):
            e = a = t = 0.0
            for c in codes:
                v = rows.get((c, fy))
                if v:
                    e += v["enacted"]
                    a += v["actual"]
                    t += v["transfer_in"]
            return {"enacted": round(e, 2), "actual": round(a, 2),
                    "transfer_in": round(t, 2)}
        out[str(fy)] = {
            "shelter_system": agg(SHELTER_SYSTEM),
            "ea_line": agg([EA_LINE]),
            "homebase": agg([HOMEBASE]),
            "complete": int(fy) < newest,
        }
    return out


def m(v):
    """$xxx.xxM, the form both the register and the chart use."""
    return v / 1_000_000.0


def stamp_chart(series, newest):
    """Rewrite the dashboard's SHIFT array from the series.

    Only the numbers are written. The per-year prose lives in SHIFT_NOTES,
    which a human edits and this never touches -- regexing prose to keep it
    current fails silently, and on this repo it already has.
    """
    page = os.path.join(ROOT, "immigration-dashboard.html")
    if not os.path.exists(page):
        return "immigration-dashboard.html missing"
    with open(page, encoding="utf-8") as fh:
        html = fh.read()
    lines = []
    for fy in sorted(series, key=int):
        s = series[fy]
        if s["complete"]:
            # A closed year shows what was actually spent.
            lines.append(
                "      {{ fy: 'FY{0}', shelter: {1:.2f}, home: {2:.2f}, "
                "xfer: {3:.2f}, kind: 'actual' }}".format(
                    str(fy)[-2:], m(s["ea_line"]["actual"]),
                    m(s["homebase"]["actual"]), m(s["homebase"]["transfer_in"])))
        else:
            # The year in progress shows the enacted appropriation, so the bar
            # is comparable with the full years beside it, and carries spending
            # to date separately rather than pretending it is a year's total.
            lines.append(
                "      {{ fy: 'FY{0}', shelter: {1:.2f}, home: {2:.2f}, "
                "xfer: {3:.2f}, kind: 'enacted', ytdShelter: {4:.2f}, "
                "ytdHome: {5:.2f} }}".format(
                    str(fy)[-2:], m(s["ea_line"]["enacted"]),
                    m(s["homebase"]["enacted"]), m(s["homebase"]["transfer_in"]),
                    m(s["ea_line"]["actual"]), m(s["homebase"]["actual"])))
    block = ("var SHIFT = [\n" + ",\n".join(lines) + "\n    ];")
    start = "/* BEGIN owned:update-immigrant-spending.py SHIFT */"
    end = "/* END owned:update-immigrant-spending.py SHIFT */"
    if start not in html or end not in html:
        return "SHIFT ownership markers not found in immigration-dashboard.html"
    pre, rest = html.split(start, 1)
    _old, post = rest.split(end, 1)
    html = pre + start + "\n    " + block + "\n    " + end + post
    with open(page, "w", encoding="utf-8") as fh:
        fh.write(html)
    return None


def stamp_register(series, newest):
    """Rewrite the shelter rows of MASTER_DATA.md, keyed on the row label.

    The label is the key, so nothing here matches on prose. A row this owns
    carries "written by update-immigrant-spending.py" in its verified column
    instead of a hand-verified tick, because a tick on a figure no one checks
    is the thing that went wrong.
    """
    reg = os.path.join(ROOT, "MASTER_DATA.md")
    if not os.path.exists(reg):
        return "MASTER_DATA.md missing"
    yrs = sorted(series, key=int)
    src = "CTHRU kv7m-35wn"
    # The register's own "refreshed by a feed" mark, plus the owner's name. A
    # hand-verified tick is what these rows used to carry, and a tick on a
    # figure nothing re-checks is how the wrong HomeBASE number kept its
    # credentials for six weeks.
    own = "\U0001f504 written by `update-immigrant-spending.py`"

    def fy_list(key):
        parts = []
        for fy in yrs:
            s = series[fy]
            tag = "" if s["complete"] else " YTD"
            parts.append("FY{0}{1} ${2:,.2f}M".format(
                str(fy)[-2:], tag, m(s[key]["actual"])))
        return " · ".join(parts)

    sys_tot = {fy: m(series[fy]["shelter_system"]["actual"]) for fy in yrs}
    done = [fy for fy in yrs if series[fy]["complete"]]
    hb_first, hb_last = yrs[0], (done[-1] if done else yrs[-1])
    hb_a = m(series[hb_first]["homebase"]["actual"])
    hb_b = m(series[hb_last]["homebase"]["actual"])
    growth = (hb_b / hb_a - 1) * 100 if hb_a else 0.0

    # An ordered list, not a dict scan: the register is published, so the rows
    # go out in year order however the previous file had them arranged.
    rowmap = {}
    order = []

    def row(lbl, val):
        rowmap[lbl] = val
        order.append(lbl)

    for fy in yrs:
        s = series[fy]
        lbl = ("Shelter system, FY{0} actual".format(fy) if s["complete"]
               else "Shelter system, FY{0} to date".format(fy))
        row(lbl, "${0:,.2f}M".format(sys_tot[fy]))
    for a, b, lbl in ((2024, 2025, "Shelter system, FY24 + FY25"),
                      (2022, 2025, "Shelter system, FY22–FY25"),
                      (2022, 2026, "Shelter system, FY22–FY26")):
        span = [fy for fy in yrs if a <= int(fy) <= b]
        if len(span) == (b - a + 1):
            t = sum(sys_tot[fy] for fy in span)
            # Billions first, to two places: that is the form the dashboards
            # print ("$1.85B"), and check-stats-documented.py matches the
            # register on the literal. Emitting only the precise millions form
            # left the page's own card undocumented.
            row(lbl, "${0:,.2f}B (${1:,.2f}M, derived)".format(t / 1000, t))
    row("EA line 7004-0101, actual", fy_list("ea_line"))
    hb = fy_list("homebase")
    xfer = series[hb_last]["homebase"]["transfer_in"]
    row("HomeBASE 7004-0108, actual",
        "{0} — CTHRU transfer_in into 7004-0108 is ${1:,.0f} in FY{2}, "
        "not a material top-up".format(hb, xfer, hb_last))
    row("HomeBASE growth, FY{0} → FY{1}".format(
        str(hb_first)[-2:], str(hb_last)[-2:]),
        "{0:+.0f}% (derived, ${1:,.2f}M → ${2:,.2f}M)".format(
            growth, hb_a, hb_b))

    with open(reg, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    # Every row this script owns is removed and the whole block re-emitted in
    # one place, in order. Replacing rows where they sit cannot do that: a label
    # carries its own fiscal year ("FY2027 to date"), so when the year turns the
    # old label is dead and the new one has nowhere to go but the end. Rebuilding
    # the block is also idempotent, which replacing-plus-appending was not.
    owned_now = set(rowmap)
    # A label whose year has turned. These are the labels this script generates,
    # with the year loosened -- never a general prefix match on the register.
    def is_owned(label):
        if label in owned_now:
            return True
        return (label.startswith("Shelter system, FY2")
                or label.startswith("HomeBASE growth, FY")
                or label in ("EA line 7004-0101, actual",
                             "HomeBASE 7004-0108, actual"))

    first = None
    kept = []
    for ln in lines:
        label = None
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) == 4:
                label = cells[0]
        if label is not None and is_owned(label):
            if first is None:
                first = len(kept)
            continue
        kept.append(ln)
    if first is None:
        return "no owned rows found in MASTER_DATA.md; refusing to guess a position"
    block = ["| {0} | {1} | {2} | {3} |".format(k, rowmap[k], src, own)
             for k in order]
    kept[first:first] = block
    with open(reg, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept))
    return None


def budget_rows(codes):
    """Enacted and actual per (account, fiscal year), summed over funds.

    Several rows share one account and year -- one per fund. The hub's own
    $643.3M FY24 EA figure is that sum, not the largest row, so summing is
    what reproduces the published number.
    """
    qs = urllib.parse.urlencode({
        "$select": ("fiscal_year,appropriation_account_number,"
                    "appropriation_account_name,"
                    "total_enacted_budget_appropriation,total_expenses,"
                    "transfer_in"),
        "$where": (f"appropriation_account_number in({quoted(codes)}) "
                   f"AND fiscal_year>={FIRST_FY}"),
        "$limit": "5000",
    })
    rows = get(f"{BUDGET}?{qs}")
    out = {}
    for r in rows:
        fy = fy_of(r)
        acct = r.get("appropriation_account_number")
        if fy is None or not acct:
            continue
        k = (acct, fy)
        cur = out.setdefault(k, {"enacted": 0.0, "actual": 0.0, "transfer_in": 0.0,
                                 "name": r.get("appropriation_account_name", "")})
        cur["enacted"] += num(r.get("total_enacted_budget_appropriation"))
        cur["actual"] += num(r.get("total_expenses"))
        cur["transfer_in"] += num(r.get("transfer_in"))
    return out


def by_year(rows, codes):
    years = {}
    for (acct, fy), v in rows.items():
        if acct not in codes:
            continue
        y = years.setdefault(fy, {"enacted": 0.0, "actual": 0.0, "accounts": 0})
        y["enacted"] += v["enacted"]
        y["actual"] += v["actual"]
        y["accounts"] += 1
    return {str(fy): {"enacted": round(v["enacted"], 2),
                      "actual": round(v["actual"], 2),
                      "accounts_with_activity": v["accounts"]}
            for fy, v in sorted(years.items())}


def recipients(codes, since_fy):
    """Who was paid, under these appropriations, grouped by vendor.

    Socrata does the grouping server-side; pulling 100k payment rows to sum
    them here would be slower and no more accurate.
    """
    qs = urllib.parse.urlencode({
        "$select": "vendor,sum(amount) as total,count(*) as payments",
        "$where": (f"appropriation_code in({quoted(codes)}) "
                   f"AND budget_fiscal_year>={since_fy}"),
        "$group": "vendor",
        "$order": "sum(amount) desc",
        "$limit": "400",
    })
    rows = get(f"{SPEND}?{qs}")
    orgs, payroll = [], []
    for r in rows:
        name = (r.get("vendor") or "").strip()
        if not name:
            continue
        rec = {
            "vendor": name,
            "total": round(num(r.get("total")), 2),
            "payments": int(num(r.get("payments"))),
            # A hint from the legal suffix, not a determination. Nothing here
            # asserts tax status; see nonprofit_verified below.
            "form_hint": form_hint(name),
            "nonprofit_verified": False,
        }
        (payroll if PAYROLL_MARK in name.upper() else orgs).append(rec)
    return orgs, payroll


def form_hint(name):
    u = name.upper()
    if any(t in u for t in (" LLC", " LLP", " L.L.C", " INC.", " LP")):
        return "for-profit form in name"
    if any(t in u for t in (" INC", " CORP", " COUNCIL", " INSTITUTE",
                            " CHARIT", " UNITED WAY", " COALITION")):
        return "corporate or charitable form in name"
    return "unclear from name"


def latest_payment_date(codes):
    # Aggregates, not order-by-limit-1: some rows carry a null date and the
    # first one back was one of them, which published "newest payment: None".
    qs = urllib.parse.urlencode({
        "$select": "max(date) as newest,max(create_date) as created",
        "$where": f"appropriation_code in({quoted(codes)})",
    })
    rows = get(f"{SPEND}?{qs}")
    if not rows:
        return None, None
    return rows[0].get("newest"), rows[0].get("created")


def main():
    print("=== MA immigrant, refugee and family-shelter spending (CTHRU) ===\n")

    check_account_coverage()

    all_codes = list(TIER1) + list(TIER2)
    rows = budget_rows(all_codes)
    if not rows:
        blocked("CTHRU returned no budget rows for any account -- refusing to "
                "publish an empty series.")

    t1 = by_year(rows, set(TIER1))
    t2 = by_year(rows, set(TIER2))
    if not t1:
        blocked("no tier-1 rows returned -- refusing to publish.")

    newest = max(int(y) for y in t1)
    print(f"  fiscal years {min(int(y) for y in t1)}-{newest}")
    for fy in sorted(t1, key=int):
        v = t1[fy]
        print(f"    tier 1  FY{fy}  enacted {v['enacted']:>15,.0f}   "
              f"actual {v['actual']:>15,.0f}")

    # A year whose actuals go DOWN against what we last published is either a
    # restatement or a bad fetch. Both need a human; neither should overwrite a
    # good figure silently. Same guard update-cbp-encounters.py carries.
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as fh:
                prev = json.load(fh)
            back = []
            for fy, v in (prev.get("tier1", {}).get("by_fiscal_year") or {}).items():
                now = t1.get(fy, {}).get("actual")
                was = v.get("actual")
                # FY in progress rises all year; only a completed year going
                # backwards is a real signal.
                if (now is not None and was and int(fy) < newest
                        and now < was * 0.98):
                    back.append(f"FY{fy}: {was:,.0f} -> {now:,.0f}")
            if back:
                blocked("a COMPLETED fiscal year's actuals fell since the last "
                        "run, which is a restatement or a bad fetch:\n  "
                        + "\n  ".join(back))
        except (OSError, ValueError) as e:
            print(f"  note: could not read previous file ({e}); no regression check")

    series = build_series(rows, newest)
    print("\n  shelter series, from CTHRU:")
    for fy in sorted(series, key=int):
        s = series[fy]
        print("    FY{0}  system {1:>12,.2f}M   EA {2:>9,.2f}M   "
              "HomeBASE {3:>8,.2f}M  (transfer_in {4:>10,.0f})".format(
                  fy, m(s["shelter_system"]["actual"]), m(s["ea_line"]["actual"]),
                  m(s["homebase"]["actual"]), s["homebase"]["transfer_in"]))

    orgs, payroll = recipients(set(TIER1), FIRST_FY)
    print(f"\n  recipients under tier-1 appropriations since FY{FIRST_FY}: "
          f"{len(orgs)} organisations, {len(payroll)} agency-payroll rows")
    for r in orgs[:8]:
        print(f"    {r['total']:>14,.0f}  {r['vendor'][:48]}")

    last_date, last_create = latest_payment_date(set(TIER1))
    print(f"\n  newest payment date {str(last_date)[:10]}; "
          f"CTHRU row created {str(last_create)[:10]}")

    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": ("Massachusetts CTHRU -- Budget vs Actual (kv7m-35wn) for "
                   "appropriation totals; Comptroller Spending (pegc-naaa) for "
                   "payments by vendor"),
        "source_url": "https://cthru.data.socrata.com/",
        "measure": ("state appropriations and actual expenses on accounts the "
                    "Commonwealth names for immigrant, refugee or family-shelter "
                    "purposes; recipients classified by appropriation, never by "
                    "vendor name"),
        "newest_fiscal_year": newest,
        "newest_payment_date": last_date,
        "cthru_row_created": last_create,
        "account_selection": {
            "search_terms": SEARCH_TERMS,
            "dataset": "kv7m-35wn, appropriation_account_name, FY2022 onward",
            "tier1_accounts": len(TIER1),
            "excluded": [{"account": k, "name": v[0], "reason": v[1]}
                         for k, v in sorted(EXCLUDED.items())],
            "excluded_reason": EXCLUDED_REASON,
            "audit": ("Re-run the search over the terms above and every account "
                      "it returns is either in tier 1, in tier 2, or in the "
                      "excluded list with a reason. check_account_coverage() "
                      "fails the run if a new one appears in none of the three."),
        },
        "method_note": ("Accounts selected by searching appropriation_account_name "
                        "for purpose words. Classifying by appropriation asks what "
                        "the money was appropriated to do. A vendor-name match "
                        "cannot: the prior version of this analysis caught three "
                        "federally qualified health centres on the substring "
                        "NEIGHBOR and a dentist on MIRA."),
        "not_disclosed": {
            "masshealth_claims": ("Individual medical claims. Not itemized by "
                                  "recipient in any public record; aggregate "
                                  "appropriation totals only."),
            "snap_ebt": ("Federally protected recipient data. Not itemized by "
                         "recipient in any public record."),
            "why_no_estimate": ("An earlier version of this page carried $670M of "
                                "modelled education and healthcare cost from the "
                                "Center for Immigration Studies, an advocacy "
                                "organisation. A model is not a record, so the "
                                "boundary is stated instead of filled."),
        },
        "series": {
            "label": ("the shelter series the immigration dashboard and "
                      "MASTER_DATA.md publish, per fiscal year"),
            "account_sets": {
                "shelter_system": SHELTER_SYSTEM,
                "ea_line": [EA_LINE],
                "homebase": [HOMEBASE],
            },
            "owned_by": "update-immigrant-spending.py",
            "hand_editing": ("These figures are written by this script into "
                             "MASTER_DATA.md and into the dashboard's SHIFT "
                             "array. Editing either by hand will be overwritten "
                             "and check-shelter-series.py will fail the build."),
            "by_fiscal_year": series,
        },
        "tier1": {
            "label": ("accounts whose own name identifies an immigrant, refugee "
                      "or family-shelter purpose"),
            "accounts": TIER1,
            "by_fiscal_year": t1,
        },
        "tier2": {
            "label": ("general rental assistance, NOT immigrant-designated -- "
                      "published separately and never added to tier 1"),
            "accounts": TIER2,
            "by_fiscal_year": t2,
        },
        "recipients": {
            "basis": f"payments under tier-1 appropriations, FY{FIRST_FY} onward",
            "tax_status": ("UNVERIFIED. CTHRU gives a vendor name, not a "
                           "501(c)(3) determination. form_hint reads the legal "
                           "suffix and is a hint only; confirming non-profit "
                           "status needs the IRS Business Master File."),
            "organisations": orgs,
            "agency_payroll": payroll,
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"\nWrote {OUT}")

    for what, err in (("immigration-dashboard.html SHIFT array",
                       stamp_chart(series, newest)),
                      ("MASTER_DATA.md shelter rows",
                       stamp_register(series, newest))):
        if err:
            print(f"  WARNING: did not stamp {what}: {err}")
        else:
            print(f"  stamped {what}")


if __name__ == "__main__":
    main()
