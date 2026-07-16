#!/usr/bin/env python3
"""
update-census-data.py
Fetches ACS 5-Year data from Census Bureau API and updates dashboards.

Covers:
  - Foreign-born % by city  â  immigration-dashboard.html (chart + callouts)
  - Multilingual % by city  â  immigration-dashboard.html (chart)
  - MA median HH income     â  affordability-dashboard.html
  - Saves raw JSON           â  data/census-latest.json

Env:
  CENSUS_API_KEY  (free â api.census.gov/data/key_signup.html)
                  Works without key at 50 req/day; with key 500 req/day.
"""
import json, os, re, sys
from urllib.request import urlopen, Request
from datetime import datetime

API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMMIGRATION_HTML = os.path.join(BASE_DIR, "immigration-dashboard.html")
AFFORDABILITY_HTML = os.path.join(BASE_DIR, "affordability-dashboard.html")

# Chart city order (must match immigration-dashboard.html exactly)
FOREIGN_BORN_CITIES = [
    "Chelsea", "Revere", "Lawrence", "Lynn", "Everett", "Malden",
    "Framingham", "Waltham", "Brockton", "Lowell", "Boston",
    "Quincy", "Somerville", "Methuen", "Worcester", "Springfield"
]
MULTILINGUAL_CITIES = [
    "Lawrence", "Chelsea", "Revere", "Everett", "Lynn",
    "Framingham", "Brockton", "Lowell", "Malden", "Waltham"
]

# NOTE: there used to be OLD_FB / OLD_ML baselines here, hardcoding the values as
# they stood when this script was written. They served double duty: fallback for an
# unfetchable city, AND the search key for the replacement. That second use made the
# script single-shot -- it searched for `data:[44,38,35,...]`, and its own first
# successful run replaced that array with `data:[46,44,45,...]`, after which the
# search never matched again and every later run silently did nothing.
#
# Both charts are now located by their Chart.js dataset label, which does not change
# when the data does, and the fallback is read out of the file itself. The script can
# therefore run any number of times, and a missing city keeps whatever is currently
# published rather than reverting to a 2-year-old constant.


def find_chart_data(html, label):
    """Return (match, [current values]) for the dataset labelled `label`.

    Anchors on `label:'...'` and takes the first data:[...] after it. Bounded to a
    short window so it cannot wander into the next dataset if markup shifts.
    """
    m = re.search(
        r"(label:\s*'" + re.escape(label) + r"'\s*,\s*data:\s*\[)([^\]]*)(\])", html
    )
    if not m:
        return None, None
    vals = [v.strip() for v in m.group(2).split(",") if v.strip()]
    return m, vals


def replace_chart_data(html, label, new_values, what):
    """Rewrite the data array of the dataset labelled `label`. Returns (html, ok)."""
    m, current = find_chart_data(html, label)
    if not m:
        print(f"  !! {what}: no dataset labelled '{label}' found -- NOT updated")
        return html, False
    new_arr = ",".join(str(x) for x in new_values)
    if new_arr == m.group(2):
        return html, False
    html = html[: m.start()] + m.group(1) + new_arr + m.group(3) + html[m.end():]
    print(f"  {what}: updated ({len(new_values)} values)")
    return html, True

# ACS vintage to try (newest first)
ACS_YEARS = [2024, 2023]


# ââ Census helpers âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def census_get(url):
    if API_KEY:
        sep = "&" if "?" in url else "?"
        url += f"{sep}key={API_KEY}"
    req = Request(url, headers={"User-Agent": "MA-Data-Hub/1.0"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  CENSUS ERROR: {e}")
        return None


def try_acs(path):
    """Try multiple ACS vintages, return (data, year_used) or (None, None)."""
    for year in ACS_YEARS:
        url = f"https://api.census.gov/data/{year}/acs/acs5{path}"
        data = census_get(url)
        if data and len(data) > 1:
            return data, year
    return None, None


def normalize_name(raw):
    """Strip 'city', 'Town', 'town', 'CDP' from Census place names."""
    name = raw.split(",")[0]
    for suffix in [" city", " Town", " town", " CDP"]:
        name = name.replace(suffix, "")
    return name.strip()


# ââ Data fetchers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def fetch_foreign_born():
    """Foreign-born % for all MA places."""
    path = "?get=NAME,B05002_001E,B05002_013E&for=place:*&in=state:25"
    data, year = try_acs(path)
    if not data:
        return {}, None
    results = {}
    for row in data[1:]:
        name = normalize_name(row[0])
        total = int(row[1]) if row[1] not in (None, "null", "") else 0
        foreign = int(row[2]) if row[2] not in (None, "null", "") else 0
        if total > 0:
            results[name] = round(foreign / total * 100)
    return results, year


def fetch_language():
    """Language-other-than-English % for all MA places."""
    path = "?get=NAME,C16001_001E,C16001_002E&for=place:*&in=state:25"
    data, year = try_acs(path)
    if not data:
        return {}, None
    results = {}
    for row in data[1:]:
        name = normalize_name(row[0])
        total = int(row[1]) if row[1] not in (None, "null", "") else 0
        eng_only = int(row[2]) if row[2] not in (None, "null", "") else 0
        if total > 0:
            results[name] = round((total - eng_only) / total * 100, 1)
    return results, year


def fetch_median_income():
    """MA statewide median household income."""
    path = "?get=NAME,B19013_001E&for=state:25"
    data, year = try_acs(path)
    if not data:
        return None, None
    for row in data[1:]:
        val = row[1]
        if val and val != "null":
            return int(val), year
    return None, None


# ââ HTML updaters ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def replace_once(html, old, new, label=""):
    """Replace first occurrence of old with new. Returns (html, changed)."""
    if old == new or not old or not new:
        return html, False
    if old in html:
        html = html.replace(old, new, 1)
        print(f"  {label}: '{old}' â '{new}'")
        return html, True
    return html, False


def update_immigration(fb_data, lang_data):
    if not os.path.exists(IMMIGRATION_HTML):
        print(f"  SKIP: {IMMIGRATION_HTML} not found.")
        return
    with open(IMMIGRATION_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html

    # ââ Foreign-born chart ââ
    if fb_data:
        _m, cur_fb = find_chart_data(html, "Foreign-Born %")
        new_fb = []
        for i, city in enumerate(FOREIGN_BORN_CITIES):
            val = fb_data.get(city)
            if val is not None:
                new_fb.append(val)
            elif cur_fb and i < len(cur_fb):
                # Keep what is currently published, not a constant from 2 years ago.
                new_fb.append(cur_fb[i])
                print(f"  WARN: No Census data for {city}, keeping {cur_fb[i]}%")
        if len(new_fb) == len(FOREIGN_BORN_CITIES):
            html, _ok = replace_chart_data(html, "Foreign-Born %", new_fb,
                                           "Foreign-born chart")
        else:
            print("  !! Foreign-born: incomplete data -- NOT updated")

        # Update callout text
        for city in ("Lawrence", "Methuen"):
            new_pct = fb_data.get(city)
            old_pct_str = None
            _cre = re.compile(r"(" + re.escape(city) + r":</strong>\s*)(\d+(?:\.\d+)?)(% foreign-born)")
            _cm = _cre.search(html)
            if _cm:
                old_pct_str = _cm.group(2) + "%"
            else:
                print(f"  !! {city} callout: anchor not found -- NOT updated")
            if new_pct is not None and _cm and f"{new_pct}%" != old_pct_str:
                html = _cre.sub(lambda m: f"{m.group(1)}{new_pct}{m.group(3)}", html, count=1)
                print(f"  {city} callout: {old_pct_str} â {new_pct}%")

    # ââ Multilingual chart ââ
    if lang_data:
        _m, cur_ml = find_chart_data(html, "Multilingual %")
        new_ml = []
        for i, city in enumerate(MULTILINGUAL_CITIES):
            val = lang_data.get(city)
            if val is not None:
                new_ml.append(val)
            elif cur_ml and i < len(cur_ml):
                new_ml.append(cur_ml[i])
                print(f"  WARN: No Census data for {city}, keeping {cur_ml[i]}%")
        if len(new_ml) == len(MULTILINGUAL_CITIES):
            html, _ok = replace_chart_data(html, "Multilingual %", new_ml,
                                           "Multilingual chart")
        else:
            print("  !! Multilingual: incomplete data -- NOT updated")

    if html != orig:
        with open(IMMIGRATION_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  â {IMMIGRATION_HTML} updated.")
    else:
        print("  Immigration dashboard â no changes needed.")


def update_affordability(med_income):
    if not os.path.exists(AFFORDABILITY_HTML) or med_income is None:
        return
    with open(AFFORDABILITY_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html

    # Read the income currently published rather than searching for a hardcoded
    # "$104,800". That literal was this script's own search key, and its first
    # successful run replaced it with $103,960 -- after which the anchor matched
    # nothing and the figure could never update again.
    _im = re.search(r'Median HH Income</td><td>\$([\d,]+)</td>', html)
    if not _im:
        print("  !! MA Median HH Income: anchor not found -- NOT updated")
        old_income = None
    else:
        old_income = "$" + _im.group(1)
    new_income = f"${med_income:,}"
    if old_income and old_income != new_income:
        n = html.count(old_income)
        if n > 0:
            html = html.replace(old_income, new_income)
            print(f"  MA Median HH Income: {old_income} â {new_income} ({n}x)")

    # The Gap row is (income needed - median income). It is derived, so recompute it
    # here instead of leaving it pinned to whatever the income was when it was last
    # hand-typed. It had drifted to -$66,457, which is exactly 171,257 - 104,800 --
    # the value of the dead anchor above, fossilised in an arithmetic result.
    _nm = re.search(r'Income Needed</td><td>\$([\d,]+)</td>', html)
    _gm = re.search(r'(Gap</td><td class="highlight">)([^\d$]*)(\$)([\d,]+)(\s*\()(\d+)(% short\))', html)
    if _nm and _gm:
        _needed = int(_nm.group(1).replace(",", ""))
        _gap = _needed - med_income
        _pct = round((1 - med_income / _needed) * 100)
        _repl = f"{_gm.group(1)}{_gm.group(2)}{_gm.group(3)}{_gap:,}{_gm.group(5)}{_pct}{_gm.group(7)}"
        if _repl != _gm.group(0):
            html = html[:_gm.start()] + _repl + html[_gm.end():]
            print(f"  Gap row: {_gm.group(3)}{_gm.group(4)} ({_gm.group(6)}% short)"
                  f" -> {_gm.group(3)}{_gap:,} ({_pct}% short)")
    elif not _gm:
        print("  !! Gap row: anchor not found -- NOT updated")

    if html != orig:
        with open(AFFORDABILITY_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  â {AFFORDABILITY_HTML} updated.")
    else:
        print("  Affordability dashboard â no changes needed.")


# ââ Main âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def main():
    print("=== Census Bureau Data Update ===\n")
    if not API_KEY:
        print("TIP: Set CENSUS_API_KEY for 500 req/day (vs 50 without).")
        print("     Free: https://api.census.gov/data/key_signup.html\n")

    # 1. Foreign-born
    print("Fetching foreign-born % (ACS 5-Year, all MA places)...")
    fb_data, fb_year = fetch_foreign_born()
    if fb_data:
        print(f"  ACS vintage: {fb_year}")
        for c in FOREIGN_BORN_CITIES:
            print(f"    {c}: {fb_data.get(c, 'N/A')}%")
    else:
        print("  WARN: Could not fetch foreign-born data.")

    # 2. Multilingual
    print("\nFetching multilingual % (ACS 5-Year)...")
    lang_data, lang_year = fetch_language()
    if lang_data:
        print(f"  ACS vintage: {lang_year}")
        for c in MULTILINGUAL_CITIES:
            print(f"    {c}: {lang_data.get(c, 'N/A')}%")
    else:
        print("  WARN: Could not fetch language data.")

    # 3. Median HH income
    print("\nFetching MA median household income (ACS 5-Year)...")
    med_income, inc_year = fetch_median_income()
    if med_income:
        print(f"  ACS vintage: {inc_year}")
        print(f"  MA Median HH Income: ${med_income:,}")
    else:
        print("  WARN: Could not fetch median income.")

    # ââ Update dashboards ââ
    print(f"\n--- Updating dashboards ---")
    update_immigration(fb_data, lang_data)
    update_affordability(med_income)

    # ââ Save raw JSON ââ
    out = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "Census Bureau API â ACS 5-Year Estimates",
        "acs_vintage": fb_year or lang_year or inc_year,
        "foreign_born_pct": {c: fb_data.get(c) for c in FOREIGN_BORN_CITIES} if fb_data else None,
        "multilingual_pct": {c: lang_data.get(c) for c in MULTILINGUAL_CITIES} if lang_data else None,
        "ma_median_hh_income": med_income,
    }
    json_path = os.path.join(BASE_DIR, "data", "census-latest.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    # Only rewrite if the DATA changed. fetched_at moves every run, so writing
    # unconditionally guaranteed a diff, which guaranteed a commit -- the workflow
    # then looked productive on every run even when the ACS vintage had not moved
    # for a month. Same failure mode the HTML date stamp had.
    _payload = {k: v for k, v in out.items() if k != "fetched_at"}
    _prev = {}
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                _prev = {k: v for k, v in json.load(f).items() if k != "fetched_at"}
        except Exception:
            _prev = {}
    if _payload == _prev:
        print("Raw data unchanged -- leaving census-latest.json alone.")
        print("Census update complete (no new ACS data).")
        return
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nRaw data â {json_path}")
    print("â¨ Census update complete.\n")


if __name__ == "__main__":
    main()
