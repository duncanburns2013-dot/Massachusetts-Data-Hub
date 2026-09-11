#!/usr/bin/env python3
"""update-nyfed-grads.py — refresh the NY Fed recent-graduate figures on
employment-dashboard.html.

WHY THIS EXISTS
---------------
Three figures on that page came from the New York Fed's college labor market
release and were typed in by hand: the recent-graduate unemployment rate, the
underemployment rate, and the quarter they belong to. Audited 2026-09-10, the
rate was still right by coincidence (5.7% in both Q1 and Q2 2026) while the
quarter label said Q1 2026 and the underemployment figure read 41.5% against a
published 41.9%. A number that is right by luck is not maintained, and the label
beside it had already gone wrong.

The NY Fed publishes no API. It does publish the whole series as an .xlsx, which
is a zip of XML, so this reads it with the standard library rather than adding
openpyxl — the repo has no third-party Python dependencies and this is not worth
becoming the first.

The workbook carries MONTHLY observations. The release is quarterly and is
described by its quarter ("2026:Q2"), so the quarter is derived from the newest
observation's month rather than parsed out of the page copy.

No API key needed.
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "employment-dashboard.html")
URL = ("https://www.newyorkfed.org/medialibrary/Research/Interactives/Data/"
       "college-labor-market/College-labor-data")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Exit code for "the source did not give us anything usable, nothing written".
# Same convention as update-cbp-encounters.py: a neutral skip, not a build break.
EXIT_BLOCKED = 75


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def download(dest):
    """curl, not urllib: newyorkfed.org is fronted by a bot filter, the same
    lesson as update-cbp-encounters.py."""
    p = subprocess.run(
        ["curl", "-sSL", "-A", UA, "--max-time", "120", "-o", dest,
         "-w", "%{http_code}", URL],
        capture_output=True, text=True)
    if p.returncode != 0:
        return None, f"curl exit {p.returncode}: {p.stderr.strip()[:200]}"
    code = p.stdout.strip()
    if code != "200":
        return None, f"HTTP {code}"
    if not zipfile.is_zipfile(dest):
        return None, "response was not an .xlsx (bot filter or moved URL)"
    return dest, None


def cell_text(c, shared):
    v = c.find(NS + "v")
    if v is None or v.text is None:
        return None
    if c.get("t") == "s":
        try:
            return shared[int(v.text)]
        except (ValueError, IndexError):
            return None
    return v.text


def read_sheet(zf, name):
    """[(row_number, {column_letter: value})] for the named worksheet."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid = None
    for s in wb.iter(NS + "sheet"):
        if s.get("name", "").strip().lower() == name:
            rid = s.get("{http://schemas.openxmlformats.org/officeDocument/"
                        "2006/relationships}id")
    if rid is None:
        fail(f"worksheet {name!r} not found — workbook layout changed")
    target = None
    for r in rels:
        if r.get("Id") == rid:
            target = r.get("Target").lstrip("/")
    path = target if target.startswith("xl/") else "xl/" + target

    shared = []
    if "xl/sharedStrings.xml" in zf.namelist():
        ss = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in ss.iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))

    out = []
    sheet = ET.fromstring(zf.read(path))
    for row in sheet.iter(NS + "row"):
        cells = {}
        for c in row.iter(NS + "c"):
            ref = c.get("r") or ""
            col = re.sub(r"\d", "", ref)
            val = cell_text(c, shared)
            if val is not None:
                cells[col] = val
        if cells:
            out.append((int(row.get("r")), cells))
    return out


def latest_series(rows, label):
    """(date, value) for the newest row, reading the column headed `label`."""
    col = None
    for _, cells in rows[:30]:
        for k, v in cells.items():
            if isinstance(v, str) and v.strip().lower() == label:
                col = k
    if col is None:
        fail(f"column {label!r} not found — workbook layout changed")
    best = None
    for _, cells in rows:
        a, b = cells.get("A"), cells.get(col)
        if a is None or b is None:
            continue
        try:
            serial, value = float(a), float(b)
        except ValueError:
            continue
        if serial < 20000:          # not an Excel date serial
            continue
        # Excel's epoch, with its 1900 leap-year bug: serial 60 does not exist.
        d = date(1899, 12, 30) + timedelta(days=int(serial))
        if best is None or d > best[0]:
            best = (d, value)
    if best is None:
        fail(f"no dated observations under {label!r}")
    return best


def sub(html, pattern, value, what):
    new, n = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}",
                     html, count=1)
    if not n:
        fail(f"anchor for {what} not found — page structure changed. "
             f"Nothing written.")
    return new


def main():
    print("=== NY Fed recent-graduate figures ===\n")
    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        path, err = download(tmp)
        if err:
            print(f"  !! could not fetch the workbook: {err}", file=sys.stderr)
            print("     Nothing written; the page keeps its current figures.",
                  file=sys.stderr)
            return EXIT_BLOCKED
        with zipfile.ZipFile(path) as zf:
            un = read_sheet(zf, "unemployed")
            ue = read_sheet(zf, "underemployed")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    d_un, ur = latest_series(un, "recent graduates")
    d_ue, under = latest_series(ue, "recent graduates")
    if d_un != d_ue:
        # Both come from one release; different end dates means the workbook is
        # half-updated and the two figures would describe different quarters.
        print(f"  !! unemployment ends {d_un} but underemployment ends {d_ue}; "
              f"refusing to publish a mixed vintage.", file=sys.stderr)
        return EXIT_BLOCKED

    quarter = f"{d_un.year}:Q{(d_un.month - 1) // 3 + 1}"
    print(f"  latest observation : {d_un}  ({quarter})")
    print(f"  recent-grad UR     : {ur:.1f}%")
    print(f"  underemployment    : {under:.1f}%")

    with open(HTML_FILE, encoding="utf-8") as f:
        html = orig = f.read()

    html = sub(html, r'(data-field="nyfed-grad-ur">)[^<]*(<)', f"{ur:.1f}%",
               "recent-grad UR card")
    html = sub(html, r'(data-field="nyfed-grad-ur2">)[^<]*(<)', f"{ur:.1f}%",
               "recent-grad UR in prose")
    html = sub(html, r'(data-field="nyfed-under">)[^<]*(<)', f"{under:.1f}%",
               "underemployment")
    html = sub(html, r'(data-field="nyfed-quarter">)[^<]*(<)', quarter,
               "release quarter")

    if html == orig:
        print("\n  No changes needed.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  -> {os.path.basename(HTML_FILE)} written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
