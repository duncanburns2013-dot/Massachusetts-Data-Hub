#!/usr/bin/env python3
"""
update-irs-soi-migration.py
Downloads IRS SOI state-to-state migration CSVs and updates tax-budget-dashboard.html.

The IRS publishes at predictable URLs:
  https://www.irs.gov/pub/irs-soi/stateoutflow{YYZZ}.csv
  https://www.irs.gov/pub/irs-soi/stateinflow{YYZZ}.csv

No API key needed â public IRS data.
Data lags ~18 months (e.g., 2023-24 data released ~mid-2026).

Updates:
  - Verifies current dashboard figures against source
  - Auto-detects when a NEW migration year drops (2023-24, etc.)
  - Updates cumulative totals, stat cards, and chart arrays
  - Saves data/irs-soi-migration-latest.json
"""
import csv, io, json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAX_BUDGET_HTML = os.path.join(BASE_DIR, "tax-budget-dashboard.html")

MA_FIPS = "25"
IRS_BASE = "https://www.irs.gov/pub/irs-soi/"

# Dashboard's current values (2022-23 is latest as of Feb 2026)
CURRENT_LATEST_YEAR = "2022-23"
CURRENT_CUM_RETURNS = -184719  # 2011-2023
CURRENT_CUM_AGI_B = -24.7      # billions (AGI in $K in CSV)
CURRENT_LATEST_RETURNS = -16921
CURRENT_LATEST_AGI_B = -4.18


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

    The IRS ships these files with mixed-case headers — `n1` and the FIPS
    columns are lowercase but AGI is uppercase `AGI` — so a case-sensitive
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

    # ââ Check for NEW data year ââ
    # Current latest is 2022-23. Check if 2023-24 has dropped.
    new_year = None
    check_pairs = [(2023, 2024), (2024, 2025)]
    for y1, y2 in check_pairs:
        tag = f"{str(y1)[-2:]}{str(y2)[-2:]}"
        url = f"{IRS_BASE}stateoutflow{tag}.csv"
        print(f"Checking for {y1}-{y2} data...")
        if head_check(url):
            print(f"  ð NEW DATA AVAILABLE: {y1}-{y2}!")
            new_year = (y1, y2)
            break
        else:
            print(f"  Not yet.")

    # ââ Fetch latest (and new if available) ââ
    results = []

    # Always verify the current latest year
    print(f"\nVerifying current data ({CURRENT_LATEST_YEAR})...")
    current = fetch_year(2022, 2023)
    if current:
        results.append(current)

    # Fetch new year if found
    new_result = None
    if new_year:
        print(f"\nFetching new year ({new_year[0]}-{new_year[1]})...")
        new_result = fetch_year(*new_year)
        if new_result:
            results.append(new_result)

    # ââ Update dashboard ââ
    if not os.path.exists(TAX_BUDGET_HTML):
        print(f"\n  SKIP: {TAX_BUDGET_HTML} not found.")
    else:
        with open(TAX_BUDGET_HTML, "r", encoding="utf-8") as f:
            html = f.read()
        orig = html

        # Verify current values
        if current:
            ret_diff = abs(current["net_returns"] - CURRENT_LATEST_RETURNS)
            agi_diff = abs(current["net_agi_billions"] - CURRENT_LATEST_AGI_B)
            if ret_diff < 200 and agi_diff < 0.15:
                verification = "ok"
                print(f"\n  OK - current {CURRENT_LATEST_YEAR} data verified "
                      f"(returns: {current['net_returns']:+,}, "
                      f"AGI: ${current['net_agi_billions']:+,.2f}B)")
            else:
                verification = "mismatch"
                print(f"\n  !! Current {CURRENT_LATEST_YEAR} data MISMATCH:")
                print(f"      Dashboard: {CURRENT_LATEST_RETURNS:+,} returns, ${CURRENT_LATEST_AGI_B:+,.2f}B")
                print(f"      Fetched:   {current['net_returns']:+,} returns, ${current['net_agi_billions']:+,.2f}B")
                # Surface it. This check printed into a log nobody reads while an
                # AGI column-case bug held every AGI figure at zero for months;
                # a CI annotation is what makes the next such drift visible.
                warn(
                    f"IRS SOI {CURRENT_LATEST_YEAR} verification mismatch - "
                    f"dashboard {CURRENT_LATEST_RETURNS:+,} returns / "
                    f"${CURRENT_LATEST_AGI_B:+,.2f}B vs fetched "
                    f"{current['net_returns']:+,} returns / "
                    f"${current['net_agi_billions']:+,.2f}B"
                )

        # A new year that comes back with zeroed AGI means the parser failed, not
        # that Massachusetts lost $0. Never let that overwrite published figures.
        if new_result and not is_plausible(new_result):
            warn(
                f"IRS SOI {new_result['year']} looks unparsed "
                f"(returns={new_result['net_returns']:+,}, "
                f"AGI=${new_result['net_agi_billions']:+,.2f}B) - skipping dashboard update."
            )
            print(f"\n  !! {new_result['year']} rejected as implausible - "
                  f"dashboard left unchanged.")
            rejected_new = new_result
            new_result = None

        # If new year available, update the dashboard
        if new_result:
            nr = new_result
            new_label = nr["year"]
            print(f"\n  ð Updating dashboard with {new_label} data...")

            # Update stat cards â latest year labels
            html = html.replace("2022-23 Net Outflow", f"{new_label} Net Outflow")
            html = html.replace("2022-23 Net AGI Loss", f"{new_label} Net AGI Loss")

            # Update latest year values
            html = html.replace(
                f">{CURRENT_LATEST_RETURNS:,}<",
                f">{nr['net_returns']:,}<"
            )
            html = html.replace(
                f"-${abs(CURRENT_LATEST_AGI_B)}B",
                f"-${abs(nr['net_agi_billions']):.2f}B"
            )

            # Update cumulative totals
            new_cum_ret = CURRENT_CUM_RETURNS + nr["net_returns"]
            new_cum_agi = round(CURRENT_CUM_AGI_B + nr["net_agi_billions"], 1)
            end_year = new_year[1]

            html = html.replace(
                f">{CURRENT_CUM_RETURNS:,}<",
                f">{new_cum_ret:,}<"
            )
            html = html.replace("-$24.7B", f"-${abs(new_cum_agi):.1f}B")
            html = html.replace("2011â2023", f"2011â{end_year}")
            html = html.replace("12-Year Migration", f"{end_year - 2011}-Year Migration")

            # Update avg income table
            pct_more = round((nr["avg_income_leaving"] / nr["avg_income_arriving"] - 1) * 100) if nr["avg_income_arriving"] > 0 else 0
            new_row = (
                f'<tr style="background:rgba(26,68,128,0.05);font-weight:600">'
                f'<td>{new_label} â</td>'
                f'<td class="highlight">${nr["avg_income_leaving"]:,}</td>'
                f'<td>${nr["avg_income_arriving"]:,}</td>'
                f'<td class="highlight">Leavers earn {pct_more}% more</td>'
                f'<td style="color:var(--red);font-weight:700">YES â full year</td></tr>'
            )
            # Insert before closing </tbody>
            old_latest_row_marker = "2022-23 â"
            if old_latest_row_marker in html:
                # Find the old "latest" row and demote it (remove â and special styling)
                html = html.replace('2022-23 â', '2022-23')
                # Find </tbody> in the avg income table and insert new row before it
                tbody_pattern = r'(YES â started Jan 2023</td></tr>)'
                html = re.sub(tbody_pattern, r'\1\n        ' + new_row, html, count=1)

            print(f"    Cumulative returns: {CURRENT_CUM_RETURNS:,} â {new_cum_ret:,}")
            print(f"    Cumulative AGI: -${abs(CURRENT_CUM_AGI_B)}B â -${abs(new_cum_agi):.1f}B")
            print(f"    Avg leaving: ${nr['avg_income_leaving']:,} | Arriving: ${nr['avg_income_arriving']:,} ({pct_more}% gap)")

        if html != orig:
            with open(TAX_BUDGET_HTML, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  â {TAX_BUDGET_HTML} updated.")
        else:
            print("  No dashboard changes needed.")

    # ââ Save JSON ââ
    out = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "IRS Statistics of Income \u2014 State-to-State Migration Data",
        "latest_year_verified": CURRENT_LATEST_YEAR,
        "verification": verification,
        "new_year_found": new_result["year"] if new_result else None,
        "new_year_rejected": rejected_new["year"] if rejected_new else None,
        "results": results,
    }
    json_path = os.path.join(BASE_DIR, "data", "irs-soi-migration-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nData â {json_path}")
    print("â¨ IRS SOI migration update complete.\n")


if __name__ == "__main__":
    main()
