#!/usr/bin/env python3
"""
primemls.py — reusable PrimeMLS (Paragon RESO Web API / OData) client.

urllib only, no third-party deps. Reads credentials from environment (or a .env
next to this file). Import and use:

    from primemls import fetch_all
    rows = fetch_all(
        "StandardStatus eq 'Closed' and City eq 'Portsmouth'",
        "ListingId,ClosePrice,ListPrice,CloseDate,DaysOnMarket,BedroomsTotal",
    )

HARD-WON LESSONS baked in (see README.md):
  * Auth is OAuth2 client-credentials -> 2h bearer token (cached here).
  * Sold = StandardStatus eq 'Closed' (the STRING; numeric 'eq 2' 500s).
  * NEVER use $count -- it 500s on this server. Paginate + count client-side.
  * The server 500s on heavy/complex queries and intermittently under load;
    _get() retries on 500/429/5xx with backoff. Keep result sets bounded
    (by city + date window) and PACE requests -- rate limits are strict.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://primemls.paragonrels.com/OData/primemls/identity/connect/token"
DATA_URL = "https://primemls.paragonrels.com/OData/primemls/DD1.7/Property"
SCOPE = "OData"
# Seconds to wait before re-reading a short page to tell "end of data" apart from
# "throttled and truncated". See fetch_all.
TRUNCATION_RECHECK_DELAY = 3.0
# A real browser UA — Cloudflare 403s the default python-urllib UA from datacenter (CI) IPs.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _load_dotenv():
    p = Path(__file__).resolve().parent / ".env"
    if not p.exists():
        return
    # utf-8-sig, not utf-8: PowerShell's `Set-Content -Encoding utf8` (the obvious
    # way to create this file on Windows) writes a BOM. Read as plain utf-8 the
    # first key becomes "﻿PRIMEMLS_CLIENT_ID" and auth fails with a confusing
    # KeyError on a file that looks completely correct in an editor.
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()
_tok = {"v": None, "exp": 0.0}


def get_token():
    now = time.time()
    if _tok["v"] and now < _tok["exp"] - 120:
        return _tok["v"]
    cid = os.environ["PRIMEMLS_CLIENT_ID"]
    sec = os.environ["PRIMEMLS_CLIENT_SECRET"]
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    data = f"grant_type=client_credentials&scope={os.environ.get('PRIMEMLS_SCOPE', SCOPE)}".encode()
    req = urllib.request.Request(
        os.environ.get("PRIMEMLS_TOKEN_URL", TOKEN_URL),
        data=data,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        t = json.loads(r.read())
    _tok["v"], _tok["exp"] = t["access_token"], now + t.get("expires_in", 7200)
    return _tok["v"]


def _get(params, max_retries=6):
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{os.environ.get('PRIMEMLS_DATA_URL', DATA_URL)}?{qs}"
    last = None
    for attempt in range(max_retries):
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {get_token()}", "Accept": "application/json",
                          "User-Agent": UA}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:120]}"
            # 403 = Cloudflare bot/rate block (needs a longer cooldown); 429/5xx = transient.
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < max_retries - 1:
                ra = e.headers.get("Retry-After")
                base = 12.0 if e.code == 403 else (2 ** attempt + 1.0)
                wait = float(ra) if (ra and ra.isdigit()) else base * (attempt + 1)
                time.sleep(min(wait, 90))
                continue
            raise RuntimeError(f"PrimeMLS {last}")
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"PrimeMLS network error: {last}")
    raise RuntimeError(f"PrimeMLS unreachable: {last}")


def fetch_all(filt, select, page=200, order="CloseDate desc", pace=0.4, max_pages=100000):
    """Paginate every record matching an OData $filter. No $count (paginate to the end).
    Keep `filt` bounded (city + date window) so the server doesn't 500 and $skip stays shallow.
    `pace` = seconds slept between pages to respect the rate limit."""
    rows, skip = [], 0
    for _ in range(max_pages):
        params = {"$top": page, "$skip": skip, "$select": select, "$filter": filt}
        if order:
            params["$orderby"] = order
        batch = _get(params).get("value", [])

        # A page shorter than $top means one of two very different things: we
        # genuinely reached the end, OR Cloudflare/PrimeMLS quietly truncated the
        # response under throttling. Treating the second as the first is silent
        # data loss, and it is exactly what produced Salem=200 (of ~1,755) and
        # Derry=0 on 2026-07-13 while the run reported success.
        #
        # So make a short page prove itself: pause and re-request the SAME offset.
        # A real end-of-data is deterministic and returns the same short page; a
        # throttled one usually returns more the second time.
        if len(batch) < page:
            time.sleep(TRUNCATION_RECHECK_DELAY)
            verify = _get(params).get("value", [])
            if len(verify) > len(batch):
                batch = verify                      # first read was truncated
            if len(batch) < page:
                rows.extend(batch)
                break

        rows.extend(batch)
        skip += page
        time.sleep(pace)
    return rows
