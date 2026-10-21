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

# Found by searching appropriation_account_name for: IMMIGRAN, REFUGEE, ASYLUM,
# SHELTER, CITIZENSHIP, MIGRANT, RESETTLE, EMERGENCY ASSISTANCE, HOUSING TRANS.
# Re-run that search to audit this list; it is the state's naming, not ours.
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


def budget_rows(codes):
    """Enacted and actual per (account, fiscal year), summed over funds.

    Several rows share one account and year -- one per fund. The hub's own
    $643.3M FY24 EA figure is that sum, not the largest row, so summing is
    what reproduces the published number.
    """
    qs = urllib.parse.urlencode({
        "$select": ("fiscal_year,appropriation_account_number,"
                    "appropriation_account_name,"
                    "total_enacted_budget_appropriation,total_expenses"),
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
        cur = out.setdefault(k, {"enacted": 0.0, "actual": 0.0,
                                 "name": r.get("appropriation_account_name", "")})
        cur["enacted"] += num(r.get("total_enacted_budget_appropriation"))
        cur["actual"] += num(r.get("total_expenses"))
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


if __name__ == "__main__":
    main()
