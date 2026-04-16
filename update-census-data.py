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

# Current hardcoded baselines (for safe fallback if a city can't be fetched)
OLD_FB = [44, 38, 35, 35, 34, 33, 32, 31, 31, 30, 29, 28, 27, 23, 22, 19]
OLD_ML = [78.5, 70.4, 58.3, 55.1, 52.6, 48.2, 45.1, 44.8, 43.5, 42.1]

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
        new_fb = []
        for i, city in enumerate(FOREIGN_BORN_CITIES):
            val = fb_data.get(city)
            if val is not None:
                new_fb.append(val)
            else:
                new_fb.append(OLD_FB[i])
                print(f"  WARN: No Census data for {city}, keeping {OLD_FB[i]}%")

        old_arr = ",".join(str(x) for x in OLD_FB)
        new_arr = ",".join(str(x) for x in new_fb)
        if old_arr != new_arr:
            html, ok = replace_once(html, f"data:[{old_arr}]", f"data:[{new_arr}]",
                                    "Foreign-born chart")

        # Update callout text
        for city, old_pct_str in [("Lawrence", "35%"), ("Methuen", "23%")]:
            new_pct = fb_data.get(city)
            if new_pct is not None and f"{new_pct}%" != old_pct_str:
                html = html.replace(
                    f"{city}:</strong> {old_pct_str} foreign-born",
                    f"{city}:</strong> {new_pct}% foreign-born"
                )
                print(f"  {city} callout: {old_pct_str} â {new_pct}%")

    # ââ Multilingual chart ââ
    if lang_data:
        new_ml = []
        for i, city in enumerate(MULTILINGUAL_CITIES):
            val = lang_data.get(city)
            if val is not None:
                new_ml.append(val)
            else:
                new_ml.append(OLD_ML[i])

        old_arr = ",".join(str(x) for x in OLD_ML)
        new_arr = ",".join(str(x) for x in new_ml)
        if old_arr != new_arr:
            html, ok = replace_once(html, f"data:[{old_arr}]", f"data:[{new_arr}]",
                                    "Multilingual chart")

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

    old_income = "$104,800"
    new_income = f"${med_income:,}"
    if old_income != new_income:
        n = html.count(old_income)
        if n > 0:
            html = html.replace(old_income, new_income)
            print(f"  MA Median HH Income: {old_income} â {new_income} ({n}x)")

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
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nRaw data â {json_path}")
    print("â¨ Census update complete.\n")


if __name__ == "__main__":
    main()
