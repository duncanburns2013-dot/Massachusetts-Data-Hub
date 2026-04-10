#!/usr/bin/env python3
"""
add-live-cost-tracker.py
Run ONCE to insert the Live Cost Tracker section into tax-budget-dashboard.html.
After running, delete this script — the update-tax-budget-dashboard.py handles ongoing updates.
"""
import os, sys

HTML_FILE = os.path.join(os.path.dirname(__file__), "tax-budget-dashboard.html")
if not os.path.exists(HTML_FILE):
    print(f"ERROR: {HTML_FILE} not found.")
    sys.exit(1)

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# Check if already inserted
if 'chartCPIlive' in html:
    print("Live Cost Tracker already present — skipping.")
    sys.exit(0)

# ── 1. Insert HTML section into Cost of Living tab ───────────────────
html_snippet = '''
  <!-- ===== LIVE COST TRACKER (auto-updated) ===== -->
  <div class="data-card" style="border-left:4px solid var(--red);margin-bottom:26px">
    <h3>&#x1F4E1; Live Cost Tracker &#x2014; Boston vs. National (BLS CPI, Monthly)</h3>
    <p style="font-size:0.78rem;color:var(--muted);margin-bottom:16px">Year-over-year inflation by category. Auto-updated monthly from BLS Consumer Price Index and EIA.</p>
    <table class="data-table">
      <thead><tr><th>Category</th><th>Boston / NE</th><th>US Average</th><th>MA Premium</th><th>Source</th></tr></thead>
      <tbody>
        <tr><td><strong>All Items (CPI-U)</strong></td><td class="highlight">+2.8%</td><td>+2.7%</td><td class="highlight">+0.1pp</td><td>BLS CPI</td></tr>
        <tr><td><strong>Shelter / Housing</strong></td><td class="highlight">+4.0%</td><td>+3.6%</td><td class="highlight">+0.4pp</td><td>BLS CPI</td></tr>
        <tr><td><strong>Electricity</strong></td><td class="highlight">31.5&#x00A2;/kWh</td><td>18.05&#x00A2;/kWh</td><td class="highlight">+75%</td><td>EIA</td></tr>
        <tr><td><strong>Overall Price Level</strong></td><td class="highlight">108.2</td><td>100.0</td><td class="highlight">+8.2%</td><td>BEA RPP (2023)</td></tr>
        <tr><td><strong>Purchasing Power of $100</strong></td><td class="highlight">$92.38</td><td>$100.00</td><td class="highlight">-$7.62</td><td>BEA RPP (2023)</td></tr>
      </tbody>
    </table>
    <div class="source">CPI and electricity data auto-updated via GitHub Actions. BEA RPP updates annually.</div>
  </div>
  <div class="chart-grid">
    <div class="chart-card">
      <h3>Boston vs. National Inflation by Category (YoY %)</h3>
      <div class="chart-area"><canvas id="chartCPIlive"></canvas></div>
      <div class="source">Source: BLS CPI-U, Boston-Cambridge-Newton MSA vs US City Average</div>
    </div>
    <div class="chart-card">
      <h3>MA Cost Premium &#x2014; Where You Pay More</h3>
      <div class="chart-area"><canvas id="chartCostPrem"></canvas></div>
      <div class="source">Source: BEA RPP (overall), EIA (electricity), BLS CPI (shelter), DOL (childcare)</div>
    </div>
  </div>
  <!-- ===== END LIVE COST TRACKER ===== -->

'''

# Insert before "Purchasing Power Illusion" alert
marker1 = '  <div class="alert">\n    <h4>\u26a0\ufe0f The Purchasing Power Illusion'
if marker1 not in html:
    # Try alternate
    marker1 = '<h4>\u26a0\ufe0f The Purchasing Power Illusion'
if marker1 not in html:
    # Try with HTML entity
    marker1 = 'The Purchasing Power Illusion'
    idx = html.find(marker1)
    if idx > 0:
        # Find the start of the containing div
        search_back = html.rfind('<div class="alert">', max(0, idx-200), idx)
        if search_back > 0:
            html = html[:search_back] + html_snippet + html[search_back:]
            print("Inserted Live Cost Tracker HTML section")
        else:
            print("WARNING: Found text but not containing div. Inserting before text.")
            html = html[:idx] + html_snippet + html[idx:]
            print("Inserted Live Cost Tracker HTML section (approx)")
    else:
        print("ERROR: Could not find 'Purchasing Power Illusion' in the file.")
        sys.exit(1)
else:
    html = html.replace(marker1, html_snippet + marker1, 1)
    print("Inserted Live Cost Tracker HTML section")

# ── 2. Insert chart JS into the costliving case ─────────────────────
js_snippet = '''
      safeChart('chartCPIlive', {
        type: 'bar',
        data: {
          labels: ['All Items', 'Shelter', 'Food', 'Energy', 'Medical'],
          datasets: [
            { label: 'Boston / NE', data: [2.8, 4.0, 2.5, 5.6, 3.2], backgroundColor: '#c0392b', borderRadius: 6 },
            { label: 'US Average', data: [2.7, 3.6, 2.3, 3.2, 3.0], backgroundColor: '#d4d0ca', borderRadius: 6 }
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, title: { display: true, text: 'YoY Change (%)' } } },
          plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } }
        }
      });
      safeChart('chartCostPrem', {
        type: 'bar',
        data: {
          labels: ['Electricity', 'Childcare', 'Housing', 'Utilities', 'Overall'],
          datasets: [{
            label: 'MA Premium Over US Average (%)',
            data: [75, 62, 96, 53, 8.2],
            backgroundColor: ['#c0392b', '#c0392b', '#b8860b', '#b8860b', '#1a4480'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, title: { display: true, text: '% Above US Average' } } },
          plugins: { legend: { display: false } }
        }
      });
'''

# Find the break before case 'fraud':
js_marker = "      break;\n    case 'fraud':"
if js_marker in html:
    html = html.replace(js_marker, js_snippet + "      break;\n    case 'fraud':", 1)
    print("Inserted Live Cost Tracker chart JS")
else:
    # Try with different whitespace
    import re
    m = re.search(r'break;\s*\n\s*case\s+.fraud.:', html)
    if m:
        html = html[:m.start()] + js_snippet + html[m.start():]
        print("Inserted Live Cost Tracker chart JS (regex match)")
    else:
        print("WARNING: Could not find JS insertion point. Charts won't render until manually added.")

# ── Write ─────────────────────────────────────────────────────────────
with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nDone! Live Cost Tracker added to {HTML_FILE}")
print("You can delete this script now — update-tax-budget-dashboard.py handles ongoing updates.")
