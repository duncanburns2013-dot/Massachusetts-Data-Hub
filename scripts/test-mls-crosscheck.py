"""Exercise fhfa_crosscheck() without running the script's network section.
Real history must pass; a deliberately shifted history must still be caught --
a guard that stops failing on a real off-by-one has been disarmed, not fixed."""
import json, sys, types, datetime, statistics, argparse
from pathlib import Path
REPO = Path(r'C:\Users\dunca\code\Massachusetts-Data-Hub')
src = (REPO / 'update-mls-figures.py').read_text(encoding='utf-8')
cut = src.index('# ---------- DATA COLLECTION ----------')
head = src[:cut]
# neutralise the arg parsing + token check that run at import
head = head.replace('ARGS = _ap.parse_args()', 'ARGS = _ap.parse_args([])')
head = head.replace('if not TOKEN:\n    sys.exit("BRIDGE_TOKEN env var not set")', 'TOKEN = TOKEN or "stub"')
mod = types.ModuleType('mlsmod'); mod.__file__ = str(REPO / 'update-mls-figures.py')
exec(compile(head, 'update-mls-figures.py', 'exec'), mod.__dict__)

hist = json.loads((REPO / 'data' / 'mls-history.json').read_text(encoding='utf-8'))
cells = hist['cells']
HS, HE = mod.HIST_START, mod.HIST_END
print(f"history window {HS}-{HE}")

def shift(delta):
    out = {'meta': hist['meta'], 'cells': dict(cells)}
    for y in range(HS, HE + 1):
        srcc = cells.get(f'ma|sf|{y+delta}')
        if srcc: out['cells'][f'ma|sf|{y}'] = srcc
    return out

print("\n=== POSITIVE: real, correctly-labelled history ===")
f0 = mod.fhfa_crosscheck(hist)
print("   ->", f0 if f0 else "no failures — PASSES")

print("\n=== NEGATIVE: labels hold NEXT year's data ===")
f1 = mod.fhfa_crosscheck(shift(+1))
print("   ->", (f1[0][:110] + '...') if f1 else "NONE — GUARD DISARMED")

print("\n=== NEGATIVE: labels hold PREVIOUS year's data ===")
f2 = mod.fhfa_crosscheck(shift(-1))
print("   ->", (f2[0][:110] + '...') if f2 else "NONE — GUARD DISARMED")

ok = (not f0) and bool(f1) and bool(f2)
print("\nRESULT:", "PASS — accepts truth, rejects both shifts" if ok else "FAIL")
sys.exit(0 if ok else 1)
