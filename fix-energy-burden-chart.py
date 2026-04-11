#!/usr/bin/env python3
"""
fix-energy-burden-chart.py
Fixes the broken Annual Household Total Energy Burden chart.
Problem: GAS/NG/DSL arrays have 16 entries but YEARS has 17.
Run once, then delete this script.
"""
import os, re, sys

HTML_FILE = os.path.join(os.path.dirname(__file__), "energy-dashboard.html")
if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

changed = False

# Fix 1: Ensure all 6 short arrays end with null
for name in ["GAS_MA", "GAS_US", "DSL_NE", "DSL_US", "NG_MA", "NG_US"]:
    pat = re.compile(r"(const " + name + r"\s*=\s*\[[^\]]+?)(\];)")
    m = pat.search(html)
    if m:
        arr_content = m.group(1)
        if not arr_content.rstrip().endswith("null"):
            html = html[:m.start()] + arr_content + ",null" + m.group(2) + html[m.end():]
            print(f"  Added null to {name}")
            changed = True
        else:
            print(f"  {name} already has null")

# Fix 2: Replace the burden computation to skip null entries
old_burden_ma = "const burdenMA=YEARS.map((_,i)=>Math.round(ELEC_MA[i]/100*7200+NG_MA[i]*700+GAS_MA[i]*500));"
new_burden_ma = "const burdenMA=YEARS.map((_,i)=>NG_MA[i]!=null&&GAS_MA[i]!=null&&ELEC_MA[i]!=null?Math.round(ELEC_MA[i]/100*7200+NG_MA[i]*700+GAS_MA[i]*500):null);"

old_burden_us = "const burdenUS=YEARS.map((_,i)=>Math.round(ELEC_US[i]/100*7200+NG_US[i]*700+GAS_US[i]*500));"
new_burden_us = "const burdenUS=YEARS.map((_,i)=>NG_US[i]!=null&&GAS_US[i]!=null&&ELEC_US[i]!=null?Math.round(ELEC_US[i]/100*7200+NG_US[i]*700+GAS_US[i]*500):null);"

if old_burden_ma in html:
    html = html.replace(old_burden_ma, new_burden_ma)
    print("  Fixed burdenMA computation")
    changed = True
else:
    # Try to find it with different formatting
    pat = re.compile(r"const burdenMA=YEARS\.map\(\(_,i\)=>[^;]+;")
    m = pat.search(html)
    if m:
        html = html[:m.start()] + new_burden_ma + html[m.end():]
        print("  Fixed burdenMA computation (regex)")
        changed = True
    else:
        print("  WARNING: Could not find burdenMA")

if old_burden_us in html:
    html = html.replace(old_burden_us, new_burden_us)
    print("  Fixed burdenUS computation")
    changed = True
else:
    pat = re.compile(r"const burdenUS=YEARS\.map\(\(_,i\)=>[^;]+;")
    m = pat.search(html)
    if m:
        html = html[:m.start()] + new_burden_us + html[m.end():]
        print("  Fixed burdenUS computation (regex)")
        changed = True
    else:
        print("  WARNING: Could not find burdenUS")

# Fix 3: Also fix the premium computations to handle null
for vname, old_start in [
    ("premElec", "const premElec"),
    ("premGas", "const premGas"),
    ("premNG", "const premNG"),
    ("premDsl", "const premDsl"),
]:
    pat = re.compile(r"(const " + vname + r"\s*=\s*YEARS\.map\(\(_,i\)=>)\+\(\(([A-Z_]+)\[i\]-([A-Z_]+)\[i\]\)/\3\[i\]\*100\)\.toFixed\(1\)\);")
    m = pat.search(html)
    if m:
        arr1 = m.group(2)
        arr2 = m.group(3)
        new_line = f"const {vname} = YEARS.map((_,i)=>{arr1}[i]!=null&&{arr2}[i]!=null?+(({arr1}[i]-{arr2}[i])/{arr2}[i]*100).toFixed(1):null);"
        html = html[:m.start()] + new_line + html[m.end():]
        print(f"  Fixed {vname} computation")
        changed = True

if changed:
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone! Fixed {HTML_FILE}")
else:
    print("\nNo changes needed.")
