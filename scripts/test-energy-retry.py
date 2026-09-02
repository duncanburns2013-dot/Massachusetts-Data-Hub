"""Does _fetch survive a transient timeout? Stub urlopen to fail twice then succeed."""
import sys, types, io, json, os
from pathlib import Path
REPO = Path(r'C:\Users\dunca\code\Massachusetts-Data-Hub')
os.environ['EIA_API_KEY'] = 'stub'
src = (REPO / 'update-energy-dashboard.py').read_text(encoding='utf-8')
head = src[:src.index('# --------------------------------------------------------------------------\n# Formatting helpers')]
mod = types.ModuleType('e'); mod.__file__ = str(REPO/'update-energy-dashboard.py')
exec(compile(head, 'x', 'exec'), mod.__dict__)

calls = {'n': 0}
class FakeResp:
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self): return json.dumps({"response":{"data":[{"price":"29.61","period":"2026-06"}]}}).encode()

def flaky(req, timeout=None, context=None):
    calls['n'] += 1
    if calls['n'] <= 2:
        raise TimeoutError("The read operation timed out")
    return FakeResp()
mod.urlopen = flaky
mod.time = types.SimpleNamespace(sleep=lambda s: None)   # don't actually wait

out = mod._fetch([("frequency","monthly")])
print(f"attempts made: {calls['n']}   result: {out}")
assert calls['n'] == 3, "should have retried twice then succeeded"
assert out[0]['price'] == '29.61'
print("PASS: transient timeout retried and recovered")

# And it must still fail loudly when the timeout never clears.
calls['n'] = 0
def always(req, timeout=None, context=None):
    calls['n'] += 1
    raise TimeoutError("The read operation timed out")
mod.urlopen = always
try:
    mod._fetch([("frequency","monthly")])
    print("FAIL: should have raised after exhausting retries"); sys.exit(1)
except TimeoutError:
    print(f"PASS: persistent timeout still raises after {calls['n']} attempts")
