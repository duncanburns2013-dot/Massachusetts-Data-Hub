#!/usr/bin/env python3
"""Build the MA / MA+NH watermarks for the burden dashboards' share cards.

Real boundary geometry, not hand-drawn. Reads per-state GeoJSON, projects,
simplifies, and emits SVGs small enough to live in a CSS data-URI -- which is what
html2canvas can actually rasterise, and what survives the PNG export. An external
image or a CSS gradient fails one or the other.

    python make-watermark.py data/geo/massachusetts.geojson data/geo/new-hampshire.geojson

Writes ma-nh-watermark.svg, ma-watermark.svg and watermark-css.txt. Paste the
data-URI from watermark-css.txt into the WATERMARK block in each dashboard's
<style> — tax-burden-dashboard.html takes the MA-only variant, the NH comparison
takes both states.

Boundary geometry: github.com/glynnbird/usstatesgeojson (US Census derived).
"""
import json
import math
import sys
from pathlib import Path

WIDTH = 1000       # viewBox width; height follows the geometry
TOL = 0.0016       # simplification tolerance, low enough to keep Cape Cod
OPACITY = 0.14
COLOR = {"ma": "#14558F", "nh": "#C0392B"}


def rings(geo):
    g = geo["geometry"]
    if g["type"] == "Polygon":
        return g["coordinates"]
    return [r for poly in g["coordinates"] for r in poly]


def perp(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def simplify(pts, tol):
    """Douglas-Peucker. Keeps the coastline readable at a fraction of the points."""
    if len(pts) < 3:
        return pts
    worst, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = perp(pts[i], pts[0], pts[-1])
        if d > worst:
            worst, idx = d, i
    if worst <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def data_uri(svg):
    enc = (svg.replace("%", "%25").replace("#", "%23").replace('"', "'")
              .replace("<", "%3C").replace(">", "%3E"))
    return f'url("data:image/svg+xml;charset=utf8,{enc}")'


def main():
    src = {"ma": Path(sys.argv[1]), "nh": Path(sys.argv[2])}
    geo = {c: json.loads(p.read_text(encoding="utf-8")) for c, p in src.items()}

    pts = [p for g in geo.values() for r in rings(g) for p in r]
    k = math.cos(math.radians(sum(p[1] for p in pts) / len(pts)))

    # Project once, in a shared frame, so the two states stay correctly positioned
    # relative to each other no matter which variant we render.
    projected = {
        c: [[(lon * k, -lat) for lon, lat in ring] for ring in rings(g)]
        for c, g in geo.items()
    }

    def render(codes):
        used = [p for c in codes for r in projected[c] for p in r]
        minx, maxx = min(p[0] for p in used), max(p[0] for p in used)
        miny, maxy = min(p[1] for p in used), max(p[1] for p in used)
        scale = WIDTH / (maxx - minx)
        height = round((maxy - miny) * scale)
        body, kept, total = "", 0, 0
        for c in codes:
            d = ""
            for ring in projected[c]:
                pl = [((x - minx) * scale, (y - miny) * scale) for x, y in ring]
                total += len(pl)
                pl = simplify(pl, TOL * scale)
                kept += len(pl)
                if len(pl) < 4:
                    continue
                d += "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pl) + "Z"
            body += f'<path fill="{COLOR[c]}" fill-opacity="{OPACITY}" d="{d}"/>'
        # width/height are NOT optional here. With only a viewBox the SVG has no
        # intrinsic size, and html2canvas silently drops it from the export -- verified
        # by diffing an exported card against one rendered with the background off.
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'width="{WIDTH}" height="{height}" '
               f'viewBox="0 0 {WIDTH} {height}">{body}</svg>')
        return svg, total, kept

    css = []
    for name, codes in (("ma-nh", ("ma", "nh")), ("ma", ("ma",))):
        svg, total, kept = render(codes)
        Path(f"{name}-watermark.svg").write_text(svg, encoding="utf-8")
        uri = data_uri(svg)
        css.append(f"/* {name} */\n{uri}")
        print(f"{name:6} points {total}->{kept}  svg {len(svg)}b  uri {len(uri)}b")
    Path("watermark-css.txt").write_text("\n\n".join(css), encoding="utf-8")


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
