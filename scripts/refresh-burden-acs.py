#!/usr/bin/env python3
"""Move every ACS figure in data/burden-constants.json to the newest ACS 1-year release, in one step.

The derivation in update-burden-constants.py requires the national and state ACS blocks to be the
same release, so they are refreshed together or not at all. Pulls direct from the Census API
(CENSUS_API_KEY from the environment or .env). Then run update-burden-constants.py.

    python scripts/refresh-burden-acs.py 2025
"""
import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year - 1
KEY = os.environ.get("CENSUS_API_KEY")
if not KEY:
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("CENSUS_API_KEY="):
            KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
if not KEY:
    sys.exit("CENSUS_API_KEY not set")

TABLES = {"households": "B11001_001E", "aggregateHouseholdIncome": "B19025_001E",
          "population": "B01003_001E", "medianHouseholdIncome_ACS": "B19013_001E"}
LABEL = {"households": "B11001", "aggregateHouseholdIncome": "B19025", "population": "B01003",
         "medianHouseholdIncome_ACS": "B19013"}


def pull(geo):
    q = f"https://api.census.gov/data/{YEAR}/acs/acs1?get=NAME,{','.join(TABLES.values())}&for={geo}&key={KEY}"
    with urllib.request.urlopen(q, timeout=60) as r:
        head, row = json.loads(r.read())
    return {k: int(row[head.index(v)]) for k, v in TABLES.items()}


today = datetime.date.today().isoformat()
release = f"ACS {YEAR} 1-year"
path = REPO / "data" / "burden-constants.json"
data = json.loads(path.read_text(encoding="utf-8"))


def stamp(node, field, value, geo):
    f = node[field]
    old = f["value"]
    f["value"] = value
    f["source"] = f"Census ACS {YEAR} 1-year, Table {LABEL[field]} (Census API, direct)"
    f["url"] = f"https://api.census.gov/data/{YEAR}/acs/acs1?get=NAME,{TABLES[field]}&for={geo}"
    f["verified"] = today
    print(f"  {field:28s} {old:>18,} -> {value:>18,}")


print("US")
us = pull("us:1")
nat = data["national_acs"]
nat["release"] = release
for k in ("households", "aggregateHouseholdIncome", "population"):
    stamp(nat, k, us[k], "us:1")

for code, fips in (("MA", "25"), ("NH", "33")):
    print(code)
    st = pull(f"state:{fips}")
    acs = data["states"][code]["acs"]
    acs["release"] = release
    for k in ("households", "aggregateHouseholdIncome", "population"):
        stamp(acs, k, st[k], f"state:{fips}")
    if "medianHouseholdIncome_ACS" in acs:
        stamp(acs, "medianHouseholdIncome_ACS", st["medianHouseholdIncome_ACS"], f"state:{fips}")

data["_meta"]["updated"] = today
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {path} ({release})")
