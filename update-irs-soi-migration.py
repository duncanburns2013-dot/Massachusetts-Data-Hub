#!/usr/bin/env python3
"""
update-irs-soi-migration.py
Downloads IRS SOI state-to-state migration CSVs and updates tax-budget-dashboard.html.

The IRS publishes at predictable URLs:
  https://www.irs.gov/pub/irs-soi/stateoutflow{YYZZ}.csv
  https://www.irs.gov/pub/irs-soi/stateinflow{YYZZ}.csv

No API key needed -- public IRS data.
Data lags ~2 years. Observed, not documented: 2022-23 landed March 2026 and
2023-24 landed 19 November 2026, so do not trust a documented release month.

What this does:
  - Verifies the published latest-year figures against the source CSVs
  - Auto-detects when a NEW migration year drops, and sanity-gates it
  - Writes data/irs-soi-migration-latest.json, newest year first

What this deliberately does NOT do: edit tax-budget-dashboard.html. It used
to, with bare string replacements that also matched the historical table
rows, so a new year would have overwritten published history and exited 0.
Applying a new year takes ~80 changes across that page including prose
judgements about rank and direction ("second worst" -> "fourth worst",
"deepened" -> "eased") that no replacement can make. When a new year lands
this prints the figures and warns; check-consistency.py then fails until the
register and dashboard are brought up to date.
"""
import csv, io, json, os, sys
from urllib.request import urlopen, Request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MA_FIPS = "25"
IRS_BASE = "https://www.irs.gov/pub/irs-soi/"

# The published figures this script verifies against. 2023-24 is the newest
# year the IRS has released (checked 2026-11-21: stateoutflow2425.csv 404s).
CURRENT_LATEST_YEAR = "2023-24"
CURRENT_PAIR = (2023, 2024)    # must match CURRENT_LATEST_YEAR
CURRENT_CUM_RETURNS = -203477  # 2011-2024
CURRENT_CUM_AGI_B = -28.4      # billions (AGI in $K in CSV)
CURRENT_LATEST_RETURNS = -18758
CURRENT_LATEST_AGI_B = -3.64

# Both cumulative constants above were re-derived by summing the 13 rows of
# the dashboard's own year-by-year table, not carried forward by addition.
# Carrying them forward is how a wrong total survives: the previous pair
# (-184,719 / -$24.7B) happened to be right, but nothing in this file checked
# it. Re-sum the table whenever you bump these.


def warn(msg):
    """Print a warning that is visible in the GitHub Actions run, not just the log."""
    print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"WARNING: {msg}")


def is_plausible(rec):
    """
    Sanity-gate a fetched year before it is allowed to rewrite the dashboard.

    A year is only trusted if BOTH sides of the flow parsed: returns and AGI.
    Zero AGI against non-zero returns is the exact signature of a column-name
    parse failure, and is never a real IRS result.
    """
    if not rec:
        return False
    return (
        rec["outflow_returns"] > 0
        and rec["inflow_returns"] > 0
        and rec["outflow_agi_k"] > 0
        and rec["inflow_agi_k"] > 0
    )


def fetch_csv(url):
    req = Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8-sig")
        if "<html" in text[:500].lower():
            return None
        return list(csv.DictReader(io.StringIO(text)))
    except Exception:
        return None


def head_check(url):
    """Check if a URL exists (returns True/False)."""
    req = Request(url, method="HEAD", headers={"User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def _pick(row, *names, default=""):
    """
    Read the first present column from a case-normalized row.

    The IRS ships these files with mixed-case headers -- `n1` and the FIPS
    columns are lowercase but AGI is uppercase `AGI` -- so a case-sensitive
    lookup silently reads returns correctly and AGI as zero. Every column is
    matched lowercased for that reason. Missing/short rows yield None from
    DictReader, so coerce before stripping.
    """
    for n in names:
        if n in row:
            v = row[n]
            if v is not None:
                return str(v).strip()
    return default


def get_ma_totals(rows, fips_col_from, fips_col_to, ma_fips_col, total_code="96"):
    """
    Extract MA total-migration row from an inflow or outflow CSV.
    Returns (returns_count, agi_thousands) or (0, 0).

    IRS CSV columns vary by year, but generally:
      - y1_statefips / y2_statefips  OR  y1_state_fips / y2_state_fips
      - n1 (number of returns) or return_num
      - AGI (AGI in thousands) or agi_num
    """
    for raw_row in rows:
        # Lowercase every header once, so the lookups below are case-agnostic.
        row = {str(k).lower().strip(): v for k, v in raw_row.items() if k}

        fips_from = _pick(row, fips_col_from.lower(), "y1_statefips", "y1_state_fips")
        fips_to = _pick(row, fips_col_to.lower(), "y2_statefips", "y2_state_fips")

        # We want the "Total Migration" row for MA
        is_ma_outflow = (fips_from == ma_fips_col and fips_to == total_code)
        is_ma_inflow = (fips_to == ma_fips_col and fips_from == total_code)

        if is_ma_outflow or is_ma_inflow:
            n1_raw = _pick(row, "n1", "return_num", default="0").replace(",", "")
            agi_raw = _pick(row, "agi", "agi_num", default="0").replace(",", "")
            try:
                return int(float(n1_raw)), int(float(agi_raw))
            except ValueError:
                pass
    return 0, 0


def fetch_year(y1, y2):
    """Fetch inflow + outflow for a migration year pair. Returns dict or None."""
    tag = f"{str(y1)[-2:]}{str(y2)[-2:]}"

    out_url = f"{IRS_BASE}stateoutflow{tag}.csv"
    in_url = f"{IRS_BASE}stateinflow{tag}.csv"

    print(f"  Fetching {y1}-{y2}...")
    out_rows = fetch_csv(out_url)
    in_rows = fetch_csv(in_url)

    if not out_rows and not in_rows:
        print(f"    Not available yet.")
        return None

    out_ret, out_agi = 0, 0
    in_ret, in_agi = 0, 0

    if out_rows:
        # Try column name variants
        out_ret, out_agi = get_ma_totals(out_rows, "y1_statefips", "y2_statefips", MA_FIPS)
        if out_ret == 0:
            out_ret, out_agi = get_ma_totals(out_rows, "y1_state_fips", "y2_state_fips", MA_FIPS)
        print(f"    Outflow: {out_ret:,} returns, ${out_agi:,}K AGI")

    if in_rows:
        in_ret, in_agi = get_ma_totals(in_rows, "y1_statefips", "y2_statefips", MA_FIPS)
        if in_ret == 0:
            in_ret, in_agi = get_ma_totals(in_rows, "y1_state_fips", "y2_state_fips", MA_FIPS)
        print(f"    Inflow:  {in_ret:,} returns, ${in_agi:,}K AGI")

    net_ret = in_ret - out_ret
    net_agi = in_agi - out_agi
    net_agi_b = round(net_agi / 1_000_000, 2)

    print(f"    Net:     {net_ret:+,} returns, ${net_agi_b:+,.2f}B AGI")

    avg_out = round(out_agi * 1000 / out_ret) if out_ret > 0 else 0
    avg_in = round(in_agi * 1000 / in_ret) if in_ret > 0 else 0

    return {
        "year": f"{y1}-{str(y2)[-2:]}",
        "outflow_returns": out_ret, "outflow_agi_k": out_agi,
        "inflow_returns": in_ret, "inflow_agi_k": in_agi,
        "net_returns": net_ret, "net_agi_k": net_agi,
        "net_agi_billions": net_agi_b,
        "avg_income_leaving": avg_out, "avg_income_arriving": avg_in,
    }


def main():
    print("=== IRS SOI Migration Data Update ===\n")

    verification = "not_run"
    rejected_new = None

    # -- Check for NEW data year --
    # Probe the two years after the published one. Both are probed because a
    # long gap between runs can let two releases land.
    new_year = None
    y1c, y2c = CURRENT_PAIR
    check_pairs = [(y1c + 1, y2c + 1), (y1c + 2, y2c + 2)]
    for y1, y2 in check_pairs:
        tag = f"{str(y1)[-2:]}{str(y2)[-2:]}"
        url = f"{IRS_BASE}stateoutflow{tag}.csv"
        print(f"Checking for {y1}-{y2} data...")
        if head_check(url):
            print(f"  [NEW] NEW DATA AVAILABLE: {y1}-{y2}!")
            new_year = (y1, y2)
            break
        else:
            print(f"  Not yet.")

    # -- Fetch latest (and new if available) --
    results = []

    # Always verify the current latest year
    print(f"\nVerifying current data ({CURRENT_LATEST_YEAR})...")
    current = fetch_year(*CURRENT_PAIR)
    if current:
        results.append(current)

    # Fetch new year if found
    new_result = None
    if new_year:
        print(f"\nFetching new year ({new_year[0]}-{new_year[1]})...")
        new_result = fetch_year(*new_year)
        if new_result:
            results.append(new_result)

    # --- Verify the published figures ---
    if current:
        ret_diff = abs(current["net_returns"] - CURRENT_LATEST_RETURNS)
        agi_diff = abs(current["net_agi_billions"] - CURRENT_LATEST_AGI_B)
        if ret_diff < 200 and agi_diff < 0.15:
            verification = "ok"
            print(f"\n  OK - published {CURRENT_LATEST_YEAR} figures verified "
                  f"(returns: {current['net_returns']:+,}, "
                  f"AGI: ${current['net_agi_billions']:+,.2f}B)")
        else:
            verification = "mismatch"
            print(f"\n  !! Published {CURRENT_LATEST_YEAR} figures MISMATCH:")
            print(f"      Published: {CURRENT_LATEST_RETURNS:+,} returns, ${CURRENT_LATEST_AGI_B:+,.2f}B")
            print(f"      Fetched:   {current['net_returns']:+,} returns, ${current['net_agi_billions']:+,.2f}B")
            # Surface it. This check printed into a log nobody reads while an
            # AGI column-case bug held every AGI figure at zero for months;
            # a CI annotation is what makes the next such drift visible.
            warn(
                f"IRS SOI {CURRENT_LATEST_YEAR} verification mismatch - "
                f"published {CURRENT_LATEST_RETURNS:+,} returns / "
                f"${CURRENT_LATEST_AGI_B:+,.2f}B vs fetched "
                f"{current['net_returns']:+,} returns / "
                f"${current['net_agi_billions']:+,.2f}B"
            )

    # A new year that comes back with zeroed AGI means the parser failed, not
    # that Massachusetts lost $0. Never let that be reported as a real release.
    if new_result and not is_plausible(new_result):
        warn(
            f"IRS SOI {new_result['year']} looks unparsed "
            f"(returns={new_result['net_returns']:+,}, "
            f"AGI=${new_result['net_agi_billions']:+,.2f}B) - not reported as a release."
        )
        print(f"\n  !! {new_result['year']} rejected as implausible.")
        rejected_new = new_result
        new_result = None
        if results and results[-1] is rejected_new:
            results.pop()

    # --- A new year landed: report it loudly, change no HTML ---
    if new_result:
        nr = new_result
        cum_ret = CURRENT_CUM_RETURNS + nr["net_returns"]
        cum_agi = round(CURRENT_CUM_AGI_B + nr["net_agi_billions"], 1)
        pct = (round((nr["avg_income_leaving"] / nr["avg_income_arriving"] - 1) * 100)
               if nr["avg_income_arriving"] > 0 else 0)
        print(f"\n  NEW YEAR {nr['year']} - the dashboard and register need a pass.")
        print(f"    net returns       {nr['net_returns']:+,}  (was {CURRENT_LATEST_RETURNS:+,})")
        print(f"    net AGI           ${nr['net_agi_billions']:+,.2f}B  (was ${CURRENT_LATEST_AGI_B:+,.2f}B)")
        print(f"    outflow           {nr['outflow_returns']:,} returns, ${nr['outflow_agi_k']:,}K")
        print(f"    inflow            {nr['inflow_returns']:,} returns, ${nr['inflow_agi_k']:,}K")
        print(f"    avg leaving       ${nr['avg_income_leaving']:,}")
        print(f"    avg arriving      ${nr['avg_income_arriving']:,}  ({pct}% premium)")
        print(f"    cumulative        {cum_ret:,} returns / -${abs(cum_agi):.1f}B"
              f"  -- RE-SUM the table rather than trusting this addition")
        print("    Then bump the CURRENT_* constants at the top of this file.")
        # Loud in CI, because the figures are now stale everywhere they appear
        # and nothing else will say so until check-consistency.py runs.
        warn(
            f"IRS SOI {nr['year']} has been released: net {nr['net_returns']:+,} returns / "
            f"${nr['net_agi_billions']:+,.2f}B. tax-budget-dashboard.html, MASTER_DATA.md and "
            f"this script's CURRENT_* constants are now stale and need a manual pass. "
            f"This job no longer edits HTML - see the module docstring for why."
        )

    # -- Save JSON --
    # Newest year first. check-consistency.py reads results[0] as "the latest
    # year", so ordering this the other way round would have it checking the
    # register against the year the register had just moved off.
    results.sort(key=lambda r: r["year"], reverse=True)
    newest = results[0]["year"] if results else None

    out = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "IRS Statistics of Income \u2014 State-to-State Migration Data",
        "latest_year_verified": CURRENT_LATEST_YEAR,
        "verification": verification,
        "new_year_found": new_result["year"] if new_result else None,
        "new_year_rejected": rejected_new["year"] if rejected_new else None,
        "meta": {
            "currency": {
                "checked": datetime.utcnow().strftime("%Y-%m-%d"),
                "newest_available": newest,
                "cadence": "annual, ~2-year lag; observed releases Mar 2026 "
                           "(2022-23) and 19 Nov 2026 (2023-24)",
                "note": "state_to_state totals are MA Total Migration-US and "
                        "Foreign, so they include moves abroad and are NOT "
                        "comparable with a domestic-only net migration count",
                "url_pattern": IRS_BASE + "state{in,out}flow{YYZZ}.csv",
            }
        },
        "results": results,
    }
    json_path = os.path.join(BASE_DIR, "data", "irs-soi-migration-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nData -> {json_path}")
    print("* IRS SOI migration update complete.\n")


if __name__ == "__main__":
    main()
