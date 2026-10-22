#!/usr/bin/env python3
"""Give every hand-ticked register row an honest mark, with the reason.

THE PROBLEM THIS SOLVES
166 rows carried "hand verified <month>". That mark promises something it does
not deliver: it looks the same on a row nobody will ever check again as on a
row that genuinely needs re-reading every quarter, and the same as on a row a
script could own. The HomeBASE figure wore it for six weeks while being wrong.

Three honest states replace it:

  (script)   a job writes it. Done by wiring the updater that already fetches
             the data -- see update-mbta-3a.py and update-immigrant-spending.py.
  (frozen)   it cannot change. A recorded roll call, a signed act, a statute, a
             closed fiscal year, a published study, a series whose publisher
             has stopped extending it. Carries the reason. Not re-checked,
             because there is nothing to re-check.
  (recheck)  no API, so a human reads it -- a broker's quarterly, a
             subscription dataset, a PDF laid before the legislature. Carries
             a due date, and check-freshness.py ages it so a forgotten one
             fails instead of sitting there looking verified.

Every entry below is a decision about a published figure, so each one states
why. Run it again after editing; it is idempotent.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# DESE publishes enrollment each October, so these are a year behind -- SY2026
# is out. More seriously, the stated K-12 figure could not be reproduced from
# DESE's own dataset on 2026-10-21. Summing total_cnt for org_type 'State' in
# t8td-gens gives SY2019 955,942 -> SY2025 919,899, which is -3.8%; excluding
# pre-K gives -4.0%. The register says -3.5%. Neither basis reproduces it, so
# the basis is unknown and nothing here substitutes a replacement -- picking
# one of two numbers that both disagree with the published one would be a
# guess wearing a source. Against SY2026 the shift is -5.4% (all students) or
# -5.6% (excluding pre-K).
DESE_NOTE = ("DESE enrollment, SY2026 now published. NOTE: the stated figure "
             "could not be reproduced from DESE t8td-gens on 2026-10-21 -- "
             "that dataset gives -3.8% statewide SY2019 to SY2025 (-4.0% "
             "excluding pre-K) against the -3.5% published here. Re-derive on "
             "a stated basis before republishing.")

# --------------------------------------------------------------- FROZEN
# Each tuple is (section, {label: reason}). Section scoping is required:
# "FY2022" is a row in three different sections.

FROZEN = [
    ("Immigration", {
        f"FY{y}": ("closed federal fiscal year. These are OHSS total "
                   "encounters (Border Patrol plus ports of entry); OHSS "
                   "stopped publishing the ports-of-entry component after "
                   "FY2024, so this series is complete and cannot be extended "
                   "or revised. The Border Patrol-only series that does "
                   "continue is written by update-cbp-encounters.py.")
        for y in range(2017, 2025)
    }),
    ("Immigration", {
        "Cato/NASEM cumulative surplus (1994-2023)":
            "a published study's finding. Cato White Paper 2025, fixed text.",
        "College grad share of surplus": "same study, fixed text.",
        "Non-college grad share": "same study, fixed text.",
        "Noncitizen share of surplus": "same study, fixed text.",
        "Incarceration rate vs natives": "same study, fixed text.",
        "CBO state/local net cost (2023)":
            "CBO June 2025 report, a published document.",
        "Undocumented tax contributions (national)":
            "ITEP 2024 report, a published document.",
        "Undocumented tax contributions (MA)":
            "ITEP, a published document.",
        "FY2026 **projected** — budget documents, NOT a CTHRU actual":
            ("the FY27 budget documents' FY2026 projected column. A published "
             "document for a year that has since closed. Kept, clearly "
             "labelled, because mistaking this projection for a CTHRU actual "
             "is exactly what produced the wrong HomeBASE figure."),
        "EA caseload, 25 Jul 2024":
            "a dated snapshot from the biweekly EA report SD.3359. The report "
            "for that date will not be reissued.",
        "$100K fee per shelter family":
            "a filed legislative proposal, not a measurement.",
    }),
    ("Zoning", {
        "Minimum gross density": "set by MGL c. 40A s 3A. Statute.",
        "Distance from a station": "set by MGL c. 40A s 3A. Statute.",
        "Affordability required": "set by MGL c. 40A s 3A. Statute.",
        "Boston": "Boston is exempt from the Zoning Act by statute.",
    }),
    ("State Budget", {
        f"FY{y}": ("an enacted General Appropriation Act total. The year is "
                   "closed and the enacted figure is final.")
        for y in range(2018, 2027)
    }),
    ("State Budget", {
        "FY2027 GAA, headline scope":
            "H.5555, signed 9 July 2026. A signed act.",
        "**Governor's vetoes**":
            "a matter of record on a signed act: none were cast.",
        "Votes": "recorded roll calls. A vote is not re-taken.",
        "Chapter 70": "an enacted line in a signed act.",
        "— municipal / regional split": "an enacted split in a signed act.",
        "Unrestricted General Government Aid": "an enacted line in a signed act.",
        "SpEd Circuit Breaker": "an enacted line in a signed act.",
        "Emergency Assistance family shelter":
            "the FY2027 enacted line. Actual spending against it is written "
            "by update-immigrant-spending.py and is a different measure.",
        "State Retiree Benefits Trust (OPEB) deposit":
            "an enacted line (1595-6152) in a signed act.",
    }),
    ("Cost of Living", {
        "FY2022": "a published BSI annual report for a closed fiscal year.",
        "FY2023": "a published BSI annual report for a closed fiscal year.",
        "FY2024": "a published BSI annual report for a closed fiscal year.",
        "FY2025": "the State Auditor's release of 30 Jan 2026, a published "
                  "document for a closed fiscal year.",
        "FY2025 Q1": "a filed quarterly report, SD.2676. Not reissued.",
        "FY2026 first half (Q1 + Q2, Jul–Dec 2025)":
            "a filed report, SD.3769. Not reissued.",
        "Leading fraud type":
            "a published LexisNexis study finding, fixed text.",
    }),
    ("Employment & Labor", {
        "NFP downward revision (Apr 2024–Mar 2025)":
            "the BLS annual benchmark revision for a closed period. Final.",
    }),
]

# -------------------------------------------------------------- RECHECK
# A human must re-read these. The date is when, chosen from how often the
# publisher actually issues -- not from a guess.

RECHECK = [
    ("Housing & Real Estate", {
        "Office vacancy (C&W)": ("2027-01-31", "Cushman & Wakefield Q4 2026"),
        "Office vacancy (Colliers)": ("2027-01-31", "Colliers Q4 2026"),
        "Office vacancy (CBRE)": ("2027-01-31", "CBRE Q4 2026"),
        "National office vacancy": ("2027-01-31", "Cushman & Wakefield Q4 2026"),
        "CMBS office delinquency": ("2026-12-31", "Trepp monthly delinquency report"),
        "CMBS all-property delinquency": ("2026-12-31", "Trepp monthly delinquency report"),
        "Pre-COVID vacancy": ("2027-06-30",
                              "a baseline drawn from several sources; re-read "
                              "when any of them restates it"),
        "Major sale discounts (2025)": ("2027-03-31",
                                        "press coverage of individual sales; "
                                        "re-read against the land records"),
        "National avg office value decline": ("2027-01-31", "Green Street CPPI"),
        "Boston property tax dependence": ("2027-01-31",
                                           "Boston's FY2027 adopted budget"),
    }),
    ("Gold & Treasury", {
        "2010-2021 avg": ("2027-02-28", "World Gold Council annual demand trends"),
        "2022": ("2027-02-28", "World Gold Council annual demand trends"),
        "2023": ("2027-02-28", "World Gold Council annual demand trends"),
        "2024": ("2027-02-28", "World Gold Council annual demand trends"),
        "H1 2025": ("2027-02-28", "World Gold Council annual demand trends"),
    }),
    ("Immigration", {
        "Total annual immigration cost": ("2027-01-31",
                                          "a compilation of several state "
                                          "sources; re-derive from each"),
        "Illegal-only cost estimate": ("2027-01-31",
                                       "an estimate range from advocacy "
                                       "sources on both sides; re-derive"),
        "Entered (FY2021-24)": ("2027-01-31", "CBP plus Census, re-derive"),
        "Interior removals (Biden admin)": ("2027-01-31", "ICE ERO annual report"),
        "Net remaining": ("2027-01-31", "derived from the two rows above"),
        "Peak": ("2027-01-31", "USCIS parole and humanitarian data"),
        "Current": ("2027-01-31", "USCIS parole and humanitarian data"),
        "2024 US growth from immigration": ("2026-12-31",
                                            "Census Vintage 2026, due December"),
        "MA NIM \"nosedive\" (2025 proj)": ("2026-12-31",
                                            "Census Vintage 2026, due December"),
        "Cost per family per week, current": ("2026-12-31",
                                              "the next biweekly EA report"),
        "Cost per family per week": ("2027-02-28",
                                     "the State Auditor's next shelter review"),
    }),
    ("Employment & Labor", {
        "Perceived job-finding probability": ("2026-12-31",
                                              "NY Fed Survey of Consumer "
                                              "Expectations, monthly"),
        "Private sector hiring plans": ("2026-12-31",
                                        "Challenger Gray monthly report"),
        "MA premium over national rate": ("2026-12-31",
                                          "BLS JOLTS state tables"),
    }),
    ("Healthcare & Insurance", {
        "Personal health care spending per capita, 2020":
            ("2027-06-30", "CMS Health Expenditures by State of Residence"),
        "Employer family premium, 2025":
            ("2027-06-30", "AHRQ MEPS-IC, annual"),
    }),
    ("Housing & Real Estate", {
        "Median household income": ("2026-12-31",
                                    "Census ACS 5-year, next release"),
        "Condo median (Haverhill)": ("2026-12-31", "MLS PIN, quarterly pull"),
        "SF median (Haverhill)": ("2026-12-31", "MLS PIN, quarterly pull"),
        "Income needed for condo": ("2026-12-31",
                                    "derived from the condo median above and "
                                    "the stated rate assumptions; re-derive "
                                    "when either moves"),
        "Income needed for SF": ("2026-12-31",
                                 "derived from the SF median above and the "
                                 "stated rate assumptions; re-derive when "
                                 "either moves"),
    }),
    # DESE publishes enrollment every October and SY2026 is already out, so
    # these are a year behind. They are also the one group in this pass whose
    # stated figure could NOT be reproduced from the source it cites -- see
    # the note below. Short due date, because both need a human decision
    # about the basis, not a guess from here.
    ("Education", {
        "K-12 overall": ("2026-11-30", DESE_NOTE),
        "Local public schools": ("2026-11-30", DESE_NOTE),
        "Private schools": ("2026-11-30", DESE_NOTE),
        "Vocational/technical": ("2026-11-30", DESE_NOTE),
        "Charter schools": ("2026-11-30", DESE_NOTE),
        "Homeschooling": ("2026-11-30", DESE_NOTE),
    }),
    ("Employment & Labor", {
        "Job openings rate (peak)": ("2026-12-31", "BLS JOLTS via FRED"),
        "Job openings rate (2025)": ("2026-12-31", "BLS JOLTS via FRED"),
        "Healthcare jobs added (2025)": ("2026-12-31", "BLS CES via FRED"),
        "Business/professional services lost": ("2026-12-31", "BLS CES via FRED"),
        "Manufacturing lost": ("2026-12-31", "BLS CES via FRED"),
        "Federal government jobs lost since peak": ("2026-12-31",
                                                    "BLS CES via FRED"),
    }),
    ("Cost of Living", {
        "MA SNAP persons participating": ("2026-12-31",
                                          "USDA-FNS SNAP data tables"),
        "MA SNAP persons, a year earlier": ("2026-12-31",
                                            "USDA-FNS SNAP data tables"),
        "Change over the year": ("2026-12-31",
                                 "derived from the two SNAP rows above"),
        "MA poverty rate": ("2027-09-30", "Census ACS 1-year, table S1701"),
        "MA residents receiving SNAP": ("2026-12-31",
                                        "USDA-FNS over Census population"),
        "Expected fraud (national model)": ("2027-06-30",
                                            "USDA-FNS trafficking studies"),
        "Detected fraud (MA), BSI Q1 FY2025": ("2027-01-31",
                                               "the next BSI quarterly"),
        "Detection rate (SNAP, one quarter)": ("2027-01-31",
                                               "derived from the two rows above"),
        "Annual range FY22–FY25 (tax-budget card)":
            ("2027-01-31", "derived from the BSI annual rows above"),
        "Detection rate (tax-budget card)": ("2027-01-31",
                                             "derived from BSI FY25 over the "
                                             "benefit base"),
        "Program breakdown on tax-budget-dashboard": ("2027-01-31",
                                                      "the next BSI annual"),
    }),
    ("Immigration", {
        "2020": ("2026-12-31", "Census Vintage 2026, due December"),
        "2021": ("2026-12-31", "Census Vintage 2026, due December"),
        "2022": ("2026-12-31", "Census Vintage 2026, due December"),
        "2023": ("2026-12-31", "Census Vintage 2026, due December"),
        "2024": ("2026-12-31", "Census Vintage 2026, due December"),
        "2025": ("2026-12-31", "Census Vintage 2026, due December"),
        "EA caseload, 1 Oct 2026": ("2026-12-31",
                                    "the newest biweekly EA report"),
        "Caseload change, Jul 2024 to Oct 2026": ("2026-12-31",
                                                  "derived from the two "
                                                  "caseload rows"),
        "EOHLC all-in FY2026 (shelter $286.8M + exits incl. HomeBASE $153.7M)":
            ("2027-01-31", "the next EOHLC all-in report"),
        "FY2027 GAA": ("2027-07-31",
                       "the FY2028 budget documents, when the FY2027 column "
                       "becomes final"),
        "Immigrant-vendor payments file (28 vendors, 8,883 payments)":
            ("2027-01-31",
             "superseded in substance by shelter-immigrant-spending.html, "
             "which classifies by appropriation; this row describes the older "
             "vendor-name file and should be retired or restated"),
    }),
    ("State Budget", {
        "FY2027": ("2027-07-31",
                   "the enacted FY2027 total can still move on a supplemental; "
                   "final after the year closes"),
        "Growth, FY2018 to FY2026": ("2027-07-31",
                                     "derived from the GAA rows above"),
        "Growth, FY2018 to FY2027": ("2027-07-31",
                                     "derived from the GAA rows above"),
        "Fair Share surtax deployed": ("2027-01-31",
                                       "Mass Taxpayers Foundation analysis"),
        "Line items in `tax-budget-dashboard.html`":
            ("2027-07-31", "re-diff the dashboard against gaa1.xlsx for FY2028"),
    }),
]


def main():
    before = register.counts()
    froze = missed = 0
    for section, reasons in FROZEN:
        done, miss = register.freeze_rows(reasons, section=section)
        froze += len(done)
        if miss:
            missed += len(miss)
            print(f"  not found in [{section}]: {', '.join(miss)}")
    checks = 0
    for section, due in RECHECK:
        done, miss = register.recheck_rows(due, section=section)
        checks += len(done)
        if miss:
            missed += len(miss)
            print(f"  not found in [{section}]: {', '.join(miss)}")
    after = register.counts()
    print(f"\n  frozen  {froze} rows")
    print(f"  recheck {checks} rows")
    if missed:
        print(f"  {missed} labels in this file matched no register row")
    print(f"\n  before: {before}")
    print(f"  after:  {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
