name: Update Energy Data

on:
  schedule:
    - cron: "0 10 15 * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update energy dashboard
        env:
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: python update-energy-dashboard.py
      - name: Update affordability dashboard
        env:
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: python update-affordability-dashboard.py
      - name: Commit if changed
        run: |
          git diff --quiet -- '*.html' && exit 0
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add *.html
          git commit -m "data: auto-update EIA + BLS data"
          git push
