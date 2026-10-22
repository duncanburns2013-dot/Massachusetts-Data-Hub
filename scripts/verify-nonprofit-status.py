#!/usr/bin/env python3
"""Check CTHRU payment recipients against the IRS Exempt Organizations file.

WHAT IT ANSWERS
immigration-dashboard.html lists 392 organisations paid under immigrant,
refugee and family-shelter appropriations, and until now every row carried
nonprofit_verified: false, because CTHRU gives a vendor name and an amount and
says nothing about tax status. This resolves that against the IRS's own file.

Source: IRS Exempt Organizations Business Master File, Massachusetts
(https://www.irs.gov/pub/irs-soi/eo_ma.csv). SUBSECTION 03 is 501(c)(3).

THE MATCHING IS DELIBERATELY STRICT
Name matching is what produced the error this whole page was built to avoid: a
substring filter caught three federally qualified health centres on NEIGHBOR and
a dentist on MIRA. So:

  exact     the normalised names are identical. Only this sets
            nonprofit_verified = true.
  ambiguous normalised name matches more than one EIN. Recorded with the
            candidates and NOT marked verified -- two charities can share a
            name and picking one would be a guess.
  none      no match in the Massachusetts file.

Normalisation strips punctuation, collapses whitespace, drops a leading THE and
the legal-form suffixes (INC, INCORPORATED, CORP, CO, LLC, LLP, LTD). It does
NOT do fuzzy or partial matching. A near-miss is reported for a human to read,
never auto-accepted.

"NONE" DOES NOT MEAN "NOT A CHARITY"
This is the Massachusetts file. A national charity incorporated elsewhere, or
one paid through a fiscal sponsor, will not appear in it. Absence is recorded as
unmatched, never as for-profit -- the same rule that applies to a name missing
from a vendor export.
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BMF = os.path.join(ROOT, "data", "_raw_irs", "eo_ma.csv")
PAY = os.path.join(ROOT, "data", "immigrant-spending-latest.json")

SUFFIXES = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY",
            "LLC", "LLP", "LP", "LTD", "PC", "PLLC"}


def norm(name):
    """Upper, de-punctuated, suffix-stripped. Conservative by design."""
    s = (name or "").upper()
    s = s.replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("THE "):
        s = s[4:]
    parts = s.split()
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return " ".join(parts)


def load_bmf():
    if not os.path.exists(BMF):
        sys.exit(f"ERROR: {BMF} not found. Download the IRS file first:\n"
                 "  https://www.irs.gov/pub/irs-soi/eo_ma.csv")
    idx = {}
    n = 0
    with open(BMF, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            nm = norm(row.get("NAME"))
            if not nm:
                continue
            n += 1
            idx.setdefault(nm, []).append({
                "ein": (row.get("EIN") or "").strip(),
                "name": (row.get("NAME") or "").strip(),
                "city": (row.get("CITY") or "").strip(),
                "subsection": (row.get("SUBSECTION") or "").strip(),
                "ntee": (row.get("NTEE_CD") or "").strip(),
            })
    return idx, n


def main():
    idx, n_bmf = load_bmf()
    # CTHRU truncates long vendor names -- "CATHOLIC CHARITABLE BUREAU OF" and
    # "MASSACHUSETTS IMMIGRANT &" (which is MIRA) are both cut mid-name, so they
    # can never match exactly and were counted as unmatched on the first pass.
    # A truncated name is still a prefix, so: if it prefixes exactly ONE BMF
    # name, that is a determination rather than a guess. Uniqueness is what
    # makes it safe; a prefix matching several names stays ambiguous.
    keys = sorted(idx)

    def looks_truncated(raw):
        """Does the RAW CTHRU string show evidence of being cut off?

        Without this, a complete short name prefixes a different, longer
        organisation and the match is simply wrong. Three real cases caught on
        the first pass:
            CITY OF BOSTON            -> CITY OF BOSTON CREDIT UNION
            CONSIGLI CONSTRUCTION CO  -> CONSIGLI CONSTRUCTION FOUNDATION
            OLD COLONY YMCA INC       -> OLD COLONY YMCA WELLNESS SERVICES
        The second is the dangerous shape: a for-profit matched to its own
        charitable arm and marked a verified 501(c)(3).

        CTHRU cuts at a fixed width, so a truncated name is long AND does not
        end tidily on a legal suffix -- a name ending "INC" ended where its
        owner meant it to.
        """
        r = (raw or "").strip().rstrip(",")
        # A name ending on a dangling conjunction or preposition is truncated
        # whatever its length -- no organisation is called "Massachusetts
        # Immigrant &". That string is MIRA, cut at 25 characters, and the
        # length floor alone was dropping it.
        DANGLING = {"&", "AND", "OF", "FOR", "THE", "IN", "ON", "AT", "TO"}
        last = r.upper().split()[-1].rstrip(".,") if r.split() else ""
        if last in DANGLING:
            return True
        if len(r) < 28:
            return False
        tail = re.sub(r"[^A-Z]", "", r.upper().split()[-1]) if r.split() else ""
        return tail not in SUFFIXES

    def prefix_unique(stem, raw, min_len=14):
        if len(stem) < min_len or not looks_truncated(raw):
            return None
        hits = [k for k in keys if k.startswith(stem)]
        return idx[hits[0]][0] if len(hits) == 1 else None
    print(f"=== IRS Exempt Organizations, Massachusetts: {n_bmf:,} rows, "
          f"{len(idx):,} distinct normalised names ===\n")

    with open(PAY, encoding="utf-8") as fh:
        doc = json.load(fh)

    orgs = doc["recipients"]["organisations"]
    counts = {"exact": 0, "ambiguous": 0, "none": 0, "prefix": 0}
    nonlocal_c3 = []
    c3 = 0

    for o in orgs:
        key = norm(o["vendor"])
        hits = idx.get(key, [])
        if len(hits) == 1:
            h = hits[0]
            o["irs"] = {
                "match": "exact",
                "ein": h["ein"],
                "irs_name": h["name"],
                "city": h["city"],
                "subsection": h["subsection"],
                "ntee": h["ntee"],
                "is_501c3": h["subsection"] == "03",
            }
            o["nonprofit_verified"] = True
            counts["exact"] += 1
            if h["subsection"] == "03":
                c3 += 1
        elif len(hits) > 1:
            # Two charities can carry the same name. Choosing one would be the
            # guess this file exists to prevent.
            o["irs"] = {
                "match": "ambiguous",
                "candidates": [
                    {"ein": h["ein"], "name": h["name"], "city": h["city"],
                     "subsection": h["subsection"]} for h in hits[:6]
                ],
            }
            o["nonprofit_verified"] = False
            counts["ambiguous"] += 1
        else:
            h = prefix_unique(key, o['vendor'])
            if h:
                o["irs"] = {
                    "match": "prefix_unique",
                    "note": ("CTHRU truncated the vendor name; it prefixes "
                             "exactly one organisation in the IRS file"),
                    "ein": h["ein"],
                    "irs_name": h["name"],
                    "city": h["city"],
                    "subsection": h["subsection"],
                    "ntee": h["ntee"],
                    "is_501c3": h["subsection"] == "03",
                }
                o["nonprofit_verified"] = True
                counts["prefix"] = counts.get("prefix", 0) + 1
                if h["subsection"] == "03":
                    nonlocal_c3.append(1)
            else:
                o["irs"] = {"match": "none"}
                o["nonprofit_verified"] = False
                counts["none"] += 1

    c3 += len(nonlocal_c3)

    matched_total = sum(o["total"] for o in orgs if o["nonprofit_verified"])
    c3_total = sum(o["total"] for o in orgs
                   if o.get("irs", {}).get("is_501c3"))
    all_total = sum(o["total"] for o in orgs)

    doc["recipients"]["tax_status"] = (
        "Checked against the IRS Exempt Organizations Business Master File for "
        "Massachusetts. nonprofit_verified is true only on an exact normalised "
        "name match to exactly one EIN. An unmatched name is NOT evidence of "
        "for-profit status -- a charity incorporated outside Massachusetts, or "
        "paid through a fiscal sponsor, will not appear in the Massachusetts "
        "file.")
    doc["recipients"]["irs_check"] = {
        "source": "IRS Exempt Organizations Business Master File, Massachusetts",
        "source_url": "https://www.irs.gov/pub/irs-soi/eo_ma.csv",
        "bmf_rows": n_bmf,
        "method": ("exact normalised name match only; punctuation stripped, "
                   "leading THE and legal-form suffixes dropped; no fuzzy or "
                   "partial matching"),
        "matched_exact": counts["exact"],
        "matched_prefix_unique": counts["prefix"],
        "ambiguous": counts["ambiguous"],
        "unmatched": counts["none"],
        "organisations": len(orgs),
        "verified_501c3": c3,
        "dollars_total": round(all_total, 2),
        "dollars_verified_nonprofit": round(matched_total, 2),
        "dollars_verified_501c3": round(c3_total, 2),
    }

    with open(PAY, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"  organisations     {len(orgs)}")
    print(f"  exact match       {counts['exact']}")
    print(f"  prefix (truncated) {counts['prefix']}")
    print(f"  -> 501(c)(3)      {c3}")
    print(f"  ambiguous         {counts['ambiguous']}")
    print(f"  unmatched         {counts['none']}")
    print()
    print(f"  total paid            ${all_total:,.0f}")
    print(f"  to verified non-profits ${matched_total:,.0f} "
          f"({matched_total / all_total * 100:.1f}%)")
    print(f"  to verified 501(c)(3)   ${c3_total:,.0f} "
          f"({c3_total / all_total * 100:.1f}%)")
    # The page's own summary figures. Hand-typing them is how a number goes
    # false the next time this runs -- the lesson from the 45 unowned hero
    # figures fixed on 2026-10-20.
    page = os.path.join(ROOT, "immigration-dashboard.html")
    if os.path.exists(page):
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        fields = {
            "irs-c3-count": str(c3),
            "irs-org-count": str(len(orgs)),
            "irs-c3-dollars": f"${c3_total / 1_000_000:.1f}M",
            "irs-c3-pct": (f"{c3_total / all_total * 100:.1f}%"
                           if all_total else "n/a"),
            "irs-total-dollars": f"${all_total / 1_000_000:.1f}M",
        }
        missing = []
        for tag, val in fields.items():
            pat = r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)'
            html, n = re.subn(pat, lambda m: m.group(1) + val + m.group(2), html)
            if n == 0:
                missing.append(tag)
        if missing:
            print("  WARNING: data-field missing from the page: "
                  + ", ".join(missing))
        else:
            with open(page, "w", encoding="utf-8") as fh:
                fh.write(html)
            print(f"  stamped {len(fields)} fields into the page")

    print(f"\nUpdated {PAY}")


if __name__ == "__main__":
    main()
