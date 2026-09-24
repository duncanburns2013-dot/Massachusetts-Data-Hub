#!/usr/bin/env python3
"""update-prit.py -- refresh the PRIT Fund headline figures on the pension page.

WHY THIS EXISTS
---------------
The pension dashboard carried "Total PRIT Assets $105.3B, FY2024 (June 30,
2024)" and "FY2024 Return 9.9%" on 2026-09-24, when PRIM had published two more
fiscal years. The fund closed FY2026 at $129.5 billion -- the page understated it
by $24.2 billion, which is larger than most of the liabilities discussed
alongside it. Nothing on the page fetched anything, so nothing could catch it.

SOURCE
------
PRIM's own quarterly update, the Executive Director's report:
https://www.mapension.com/newsroom/quarterly-updates/

The fiscal-year figures are in that page's static HTML, so no key and no
browser. PRIM states the balance, the as-of date, the net return and the dollar
gain in one sentence, which is why this reads that sentence rather than a
number in isolation.

WHAT IT WILL AND WILL NOT DO
----------------------------
It updates only when PRIM is reporting a FISCAL YEAR close -- the August
quarterly update. The other three quarters report a quarter-end balance, which
is a different measure from the fiscal-year-end assets this card names, and
writing one into the other would quietly change what the card means. Those
quarters exit 75 and the page keeps what it has.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "pension-dashboard.html")
DATA_FILE = os.path.join(BASE_DIR, "data", "prit-latest.json")
SOURCE_URL = "https://www.mapension.com/newsroom/quarterly-updates/"

EXIT_BLOCKED = 75

# "The PRIT Fund ended fiscal year 2026 with a record balance of $129.5 billion
#  as of June 30, 2026 ... The Fund returned 12.7% (net), a gain of $14.7 billion"
BALANCE_RE = re.compile(
    r"PRIT Fund ended fiscal year (20\d\d) with a[^.$]*balance of "
    r"\$([\d,.]+) billion as of ([A-Z][a-z]+ \d{1,2}, 20\d\d)")
RETURN_RE = re.compile(
    r"Fund returned (-?[\d.]+)% \(net\)(?:, a (gain|loss) of \$([\d,.]+) billion)?")


def blocked(msg):
    print(f"SKIPPED: {msg}", file=sys.stderr)
    sys.exit(EXIT_BLOCKED)


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch(url):
    fd, out = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        r = subprocess.run(
            ["curl", "-sSL", "--max-time", "60", "--retry", "3",
             "--retry-delay", "2", "-o", out, "-w", "%{http_code}",
             "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 "
                   "Safari/537.36", url],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or r.stdout.strip() != "200":
            return None
        with open(out, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def visible_text(html_doc):
    import html as H
    s = re.sub(r"<(script|style).*?</\1>", " ", html_doc, flags=re.S)
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s)))


def setf(html, tag, value, what):
    new, n = re.subn(r'(data-field="' + re.escape(tag) + r'">)[^<]*(<)',
                     lambda m: m.group(1) + value + m.group(2), html, count=1)
    if n == 0:
        fail(f'data-field="{tag}" is missing from pension-dashboard.html '
             f"({what}). Nothing written.")
    return new


def main():
    print("=== PRIT Fund headline figures (PRIM quarterly update) ===\n")

    page = fetch(SOURCE_URL)
    if page is None:
        blocked("PRIM's quarterly-updates page did not answer -- the page keeps "
                "the figures it has.")
    text = visible_text(page)

    bal = BALANCE_RE.search(text)
    if not bal:
        blocked("PRIM is not reporting a fiscal-year close in the current "
                "quarterly update (that is the August one). Quarter-end "
                "balances are a different measure from fiscal-year-end assets, "
                "so nothing was written.")
    fy, assets, asof = bal.group(1), bal.group(2), bal.group(3)

    ret = RETURN_RE.search(text)
    if not ret:
        blocked(f"found the FY{fy} balance but not the net return sentence; "
                f"writing one without the other would leave the card half a "
                f"year apart from itself. Nothing written.")
    pct, direction, delta = ret.group(1), ret.group(2), ret.group(3)

    print(f"  FY{fy}: ${assets}B as of {asof}, {pct}% net"
          + (f", a {direction} of ${delta}B" if delta else ""))

    with open(HTML_FILE, encoding="utf-8") as fh:
        html = original = fh.read()

    # The section heading names the same number in words. Left as prose it
    # read "The $105 Billion Master Fund" directly above a $129.5B card.
    html = setf(html, "prit-headline",
                f"${round(float(assets.replace(',', '')))}", "section heading")
    html = setf(html, "prit-assets", f"${assets}B", "total PRIT assets")
    html = setf(html, "prit-asof", f"FY{fy} ({asof})", "assets as-of date")
    html = setf(html, "prit-fy", f"FY{fy} Return", "return card label")
    html = setf(html, "prit-return", f"{pct}%", "net return")
    html = setf(html, "prit-return-sub",
                (f"net of fees; a {direction} of ${delta}B" if delta
                 else "net of fees"), "return card subtitle")

    out = {
        "fiscal_year": int(fy),
        "assets_billions": float(assets.replace(",", "")),
        "as_of": asof,
        "return_pct_net": float(pct),
        "change_billions": (float(delta.replace(",", "")) if delta else None),
        "change_direction": direction,
        "verified": date.today().isoformat(),
        "source": "PRIM, Executive Director's quarterly update (PRIT Fund "
                  "performance), read from PRIM's own site",
        "source_url": SOURCE_URL,
        "meta": {"currency": {"checked": date.today().isoformat(),
                              "newest_available": f"FY{fy}",
                              "cadence": "fiscal-year figures land in PRIM's "
                                         "August quarterly update"}},
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    prev = None
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as fh:
                prev = json.load(fh)
        except (OSError, ValueError):
            prev = None
    strip = lambda d: ({k: v for k, v in d.items()
                        if k not in ("verified", "meta")} if d else None)
    if prev is not None and strip(prev) == strip(out):
        out["verified"] = prev.get("verified", out["verified"])
        out["meta"]["currency"]["checked"] = (
            prev.get("meta", {}).get("currency", {})
                .get("checked", out["meta"]["currency"]["checked"]))

    if html == original:
        print("\n  No changes needed.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"\n  Updated pension-dashboard.html -> FY{fy}")
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"Data -> {DATA_FILE}")


if __name__ == "__main__":
    main()
