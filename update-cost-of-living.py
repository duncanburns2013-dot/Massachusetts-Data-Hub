#!/usr/bin/env python3
"""Rebuild the cost-of-living dataset behind affordability-dashboard.html.

Sources, all public and key-free:
  * BEA Regional Price Parities, state    -> apps.bea.gov/regional/zip/SARPP.zip
      SARPP  (price level, US = 100, five categories)
      SARPI  (real per-capita personal income, chained 2017 dollars)
      SAIRPD (implicit regional price deflator)
  * BEA Regional Price Parities, metro    -> apps.bea.gov/regional/zip/MARPP.zip
  * Nominal per-capita personal income    -> FRED {ST}PCPI (mirrors BEA SAINC1)
  * MIT Living Wage Calculator, MA        -> livingwage.mit.edu/states/25

Writes data/cost-of-living-latest.json and injects the same payload into the
<script id="col-data"> block in affordability-dashboard.html.

Design note: the previous updater for this page did scattered regex
find-and-replace against individual figures in the HTML. Several of those
anchors silently stopped matching and the page sat on stale numbers for months
while still committing daily. This one has exactly one HTML anchor, and a
failure to match is fatal rather than silent.
"""
import csv, html as _html, io, json, os, re, sys, urllib.request, zipfile

html_unescape = _html.unescape
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "affordability-dashboard.html")
OUT = os.path.join(HERE, "data", "cost-of-living-latest.json")
UA = {"User-Agent": "Mozilla/5.0 (Massachusetts-Data-Hub updater)"}

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
# BEA RPP line codes -> the key used in the JSON payload
RPP_LINES = {"1": "all", "2": "goods", "3": "housing", "4": "utilities", "5": "other"}
# Must carry the state suffix: BEA also publishes Springfield IL / Springfield MO,
# and a bare "Springfield" prefix match silently returned whichever came last.
MA_METROS = {
    "Boston-Cambridge-Newton, MA-NH": "Boston",
    "Worcester, MA": "Worcester",
    "Springfield, MA": "Springfield",
    "Barnstable Town, MA": "Barnstable",
    "Pittsfield, MA": "Pittsfield",
    "Providence-Warwick, RI-MA": "Providence-Warwick",
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=120).read()
    return raw if binary else raw.decode("utf-8", "replace")


def bea_zip(name):
    """Download a BEA regional zip and return {csv_basename: parsed rows}."""
    z = zipfile.ZipFile(io.BytesIO(get(f"https://apps.bea.gov/regional/zip/{name}.zip", True)))
    out = {}
    for n in z.namelist():
        if n.lower().endswith(".csv"):
            out[n] = list(csv.reader(io.StringIO(z.read(n).decode("utf-8", "replace"))))
    return out


def num(x):
    x = (x or "").strip().strip('"').replace(",", "")
    try:
        return float(x)
    except ValueError:
        return None


def geo(row):
    return row[1].strip().strip('"')


# ── BEA state: price parities, real income, deflator ─────────────────────────
def state_tables():
    files = bea_zip("SARPP")
    rpp_csv = next(v for k, v in files.items() if k.startswith("SARPP_STATE"))
    rpi_csv = next(v for k, v in files.items() if k.startswith("SARPI_STATE"))
    year = rpp_csv[0][-1].strip()

    rpp = {}
    hist = {}
    years = [c.strip() for c in rpp_csv[0][8:]]
    for r in rpp_csv[1:]:
        if len(r) < 9:
            continue
        st = STATES.get(geo(r))
        line = r[4].strip().strip('"')
        if not st or line not in RPP_LINES:
            continue
        rpp.setdefault(st, {})[RPP_LINES[line]] = num(r[-1])
        if st == "MA":
            hist[RPP_LINES[line]] = [num(v) for v in r[8:]]

    real = {}
    for r in rpi_csv[1:]:
        if len(r) < 9:
            continue
        st = STATES.get(geo(r))
        if st and "Real per capita personal income" in r[6]:
            real[st] = num(r[-1])
    return year, years, rpp, hist, real


# ── BEA metro price parities ─────────────────────────────────────────────────
def metro_table():
    files = bea_zip("MARPP")
    rows = next(v for k, v in files.items() if k.startswith("MARPP_MSA"))
    out = {}
    for r in rows[1:]:
        if len(r) < 9:
            continue
        name = geo(r)
        line = r[4].strip().strip('"')
        if line not in RPP_LINES:
            continue
        for full, short in MA_METROS.items():
            if name.startswith(full + " ") or name == full:
                out.setdefault(short, {})[RPP_LINES[line]] = num(r[-1])
    missing = [s for s in MA_METROS.values() if s not in out]
    if missing:
        raise SystemExit(f"BEA metro RPP: no rows for {missing} — check MARPP geography names")
    return out


# ── FRED: nominal per-capita personal income, pinned to the BEA vintage ──────
def nominal_income(year):
    """Every request used to fail silently into `continue`, so a bad run
    returned {} and the writer published it. Failures are counted now and a
    result too small to be real raises instead of shipping."""
    out, failed = {}, []
    for st in STATES.values():
        try:
            txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={st}PCPI")
        except Exception as e:
            failed.append(f"{st}:{type(e).__name__}")
            continue
        for row in list(csv.reader(io.StringIO(txt)))[1:]:
            if row and row[0][:4] == year:
                out[st] = num(row[1])
    if failed:
        print(f"  nominal_income: {len(failed)} state(s) failed: {', '.join(failed[:8])}")
    if len(out) < 45:
        raise RuntimeError(
            f"nominal_income returned {len(out)} of {len(STATES)} states for {year} - "
            "refusing to publish a partial series")
    return out


# ── MIT Living Wage Calculator ───────────────────────────────────────────────
def living_wage():
    s = get("https://livingwage.mit.edu/states/25")
    tables = []
    for m in re.finditer(r"(?is)<table[^>]*>(.*?)</table>", s):
        rows = []
        for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", m.group(1)):
            # unescape after stripping tags: MIT's labels carry &amp; ("Computer &
            # Mathematical"), which reached the page verbatim without this.
            cells = [re.sub(r"\s+", " ", html_unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                     for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)

    def money(x):
        x = (x or "").replace("$", "").replace(",", "").strip()
        try:
            return float(x)
        except ValueError:
            return None

    # The household grid is 12 wide: three adult configurations x 0-3 children.
    # Slicing it to 8 silently drops the entire "2 adults (both working)" block,
    # which is the configuration most Massachusetts families actually run.
    NCOL = 12
    rows = {}
    for t in tables:
        for r in t:
            if not r:
                continue
            k = r[0].strip().lower()
            if k and len(r) >= NCOL + 1 and k not in rows:
                rows[k] = [money(x) for x in r[1:NCOL + 1]]
    occ = [(r[0], money(r[1])) for t in tables for r in t
           if len(r) == 2 and money(r[1]) and not r[0].lower().startswith("occupational")]

    need = ("living wage", "housing", "child care", "required annual income before taxes")
    missing = [k for k in need if k not in rows]
    if missing or not occ:
        raise SystemExit(f"MIT Living Wage: table layout changed (missing {missing}) — "
                         "refusing to write partial data")
    cols = []
    for adults in ("1 adult", "2 adults (1 working)", "2 adults (both working)"):
        for kids in ("", ", 1 child", ", 2 children", ", 3 children"):
            cols.append(adults + kids)
    return {"columns": cols, "hourly": rows["living wage"],
            "minimum_wage": rows.get("minimum wage"), "poverty_wage": rows.get("poverty wage"),
            "budget": {k: v for k, v in rows.items()
                       if k not in ("living wage", "minimum wage", "poverty wage")},
            "occupations": occ}


# ── Income benchmark the living wage is measured against ─────────────────────
def income_benchmark():
    """Median household and (where a Census key is available) family income.

    The Census API stopped serving keyless requests, so the family figure only
    resolves in CI. Locally we fall back to the household figure this repo
    already stores, rather than inventing one: the number this page used to lead
    with ($313,747 "to live comfortably") carried no source at all.
    """
    out = {"household": None, "family": None, "vintage": None,
           "source": "Census ACS via data/census-latest.json"}
    try:
        with open(os.path.join(HERE, "data", "census-latest.json"), encoding="utf-8") as f:
            c = json.load(f)
        out["household"] = c.get("ma_median_hh_income")
        out["vintage"] = c.get("acs_vintage")
    except Exception as e:
        print(f"  ! census-latest.json unreadable ({e})")

    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("  · CENSUS_API_KEY not set — skipping median family income")
        return out
    for yr in (out["vintage"] or 2024, 2023):
        try:
            url = ("https://api.census.gov/data/%d/acs/acs1?get=NAME,B19113_001E,B19013_001E"
                   "&for=state:25&key=%s" % (yr, key))
            rows = json.loads(get(url))
            out["family"] = float(rows[1][1])
            out["household"] = float(rows[1][2])
            out["vintage"] = yr
            out["source"] = f"Census ACS 1-Year {yr} (B19113 family, B19013 household)"
            break
        except Exception as e:
            print(f"  ! Census ACS {yr} failed ({e})")
    return out


def main():
    year, years, rpp, hist, real = state_tables()
    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rpp_year": year,
            "sources": {
                "rpp": "BEA Regional Price Parities (SARPP / MARPP)",
                "real_income": "BEA Real per-capita personal income (SARPI, chained 2017 dollars)",
                "nominal_income": "BEA per-capita personal income via FRED {ST}PCPI",
                "living_wage": "MIT Living Wage Calculator, Massachusetts",
            },
        },
        "years": years,
        "rpp": rpp,
        "ma_history": hist,
        "real_income": real,
        "nominal_income": nominal_income(year),
        "metros": metro_table(),
        "living_wage": living_wage(),
        "income": income_benchmark(),
    }

    # A section that comes back empty must never replace a populated one. The
    # Aug 20 run emptied nominal_income and the page published "$NaN" and a rank
    # of "0th"; carrying the last good values forward keeps a partial outage
    # from becoming a false figure.
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            prev = {}
        for key in ("rpp", "real_income", "nominal_income", "metros", "living_wage"):
            if not payload.get(key) and prev.get(key):
                payload[key] = prev[key]
                payload.setdefault("meta", {}).setdefault("carried_forward", []).append(key)
                print(f"  WARNING: {key} came back empty - carried the previous values forward")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    blob = json.dumps(payload, separators=(",", ":"))
    html = open(HTML, encoding="utf-8").read()
    pat = re.compile(r'(<script id="col-data" type="application/json">)(.*?)(</script>)', re.S)
    if not pat.search(html):
        raise SystemExit("affordability-dashboard.html: no <script id=\"col-data\"> block to fill")
    new = pat.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)
    if new != html:
        open(HTML, "w", encoding="utf-8", newline="\n").write(new)
        print(f"updated affordability-dashboard.html (RPP vintage {year})")
    else:
        print(f"no change (RPP vintage {year})")
    print(f"wrote {OUT}: {len(rpp)} states, {len(payload['metros'])} metros, "
          f"{len(payload['living_wage']['occupations'])} occupations")


if __name__ == "__main__":
    sys.exit(main())
