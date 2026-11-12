# -*- coding: utf-8 -*-
"""Fill missing environment variables from the repo's gitignored .env.

WHY THIS EXISTS
Every updater here reads its API key with os.environ.get and stopped there.
CI works, because the workflows inject the repo's Actions secrets. A local run
does not, because nothing on this machine exports anything -- the keys live in
.env, which until now only primemls.py and scripts/refresh-burden-acs.py ever
read, each with its own copy of the parser.

The result was a whole class of local-only failure that looked like a missing
key and was not one. update-tax-budget-dashboard.py skipped all nine of its
electricity figures and the page date stamp on every hand run for months,
reporting "EIA_API_KEY not set", while the key sat in .env the entire time.
update-energy-dashboard.py does not even degrade: it sys.exits.

CONTRACT
- setdefault, never assignment. In CI the injected secret is the authority and
  a stale .env on somebody's disk must never override it.
- A missing .env is normal, not an error. CI has no .env at all; it is
  gitignored and untracked, which is the point.
- utf-8-sig, not utf-8. PowerShell's `Set-Content -Encoding utf8` -- the
  obvious way to write this file on Windows -- emits a BOM, and read as plain
  utf-8 the first key becomes "﻿EIA_API_KEY". It then fails as a missing
  key, from a file that looks perfect in an editor. primemls.py was bitten by
  exactly this and its comment is why this function reads the way it does.

USE
    import envfile; envfile.load()

before the first os.environ.get of a secret. From scripts/, put the repo root
on sys.path first -- those files already compute it.
"""
import os

_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load(path=_ENV):
    """Set any key in .env that is not already in the environment.

    Returns the list of names taken from the file, never their values, so a
    caller can log what it picked up without putting a secret in a CI log.
    """
    taken = []
    if not os.path.exists(path):
        return taken
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k and k not in os.environ:
                os.environ[k] = v.strip()
                taken.append(k)
    return taken
