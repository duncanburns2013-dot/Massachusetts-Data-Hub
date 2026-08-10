#!/usr/bin/env python3
"""Extract text from PDFs using only the standard library.

Written for government PDFs that block automated download and/or embed subset fonts.

Handles:
  * /Length as a literal, and as an indirect reference (falls back to endstream scan)
  * object streams (/ObjStm), where many modern PDFs hide their content
  * 1-byte (WinAnsi) and 2-byte (CID/subset) text operands
  * subset fonts whose glyph ids sit a fixed offset below ASCII -- auto-detected by
    scoring candidate offsets against English letter frequency

Usage:
    python pdftext.py FILE.pdf            # auto-detect encoding
    python pdftext.py FILE.pdf --offset 29
"""
import argparse
import re
import sys
import zlib

TJ = re.compile(rb"\((?:\\.|[^\\()])*\)\s*Tj", re.S)
TJ_ARR = re.compile(rb"\[(?:\\.|[^\]])*\]\s*TJ", re.S)
STR = re.compile(rb"\((?:\\.|[^\\()])*\)", re.S)
ESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
COMMON = set("etaoinshrdlu ETAOINSHRDLU0123456789.,$%()-")


def _inflate(raw):
    for wbits in (15, -15, 47):
        try:
            return zlib.decompress(raw, wbits)
        except zlib.error:
            continue
    return None


def inflate_all(data: bytes) -> bytes:
    """Every stream we can decompress, concatenated. Tries /Length first, then scans."""
    out = bytearray()
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        # prefer the declared literal /Length if there is one just before this stream
        head = data[max(0, m.start() - 300):m.start()]
        lm = re.search(rb"/Length\s+(\d+)(?!\s+\d+\s+R)", head)
        candidates = []
        if lm:
            candidates.append(int(lm.group(1)))
        end = data.find(b"endstream", start)
        if end != -1:
            candidates.append(end - start)
        for n in candidates:
            blob = _inflate(data[start:start + n])
            if blob is not None:
                out += blob + b"\n"
                break
    return bytes(out)


def unescape(s: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(s):
        if s[i:i + 1] == b"\\" and i + 1 < len(s):
            c = s[i + 1:i + 2]
            out += ESC.get(c, c)
            i += 2
        else:
            out += s[i:i + 1]
            i += 1
    return bytes(out)


def operands(content: bytes):
    parts = []
    for m in TJ.finditer(content):
        parts.append(unescape(m.group(0).rsplit(b")", 1)[0][1:]))
    for m in TJ_ARR.finditer(content):
        buf = bytearray()
        for s in STR.finditer(m.group(0)):
            buf += unescape(s.group(0)[1:-1])
        parts.append(bytes(buf))
    return parts


def render(parts, mode, offset=0):
    if mode == "1byte":
        return "|".join(p.decode("latin1") for p in parts)
    out = []
    for p in parts:
        s = []
        for i in range(0, len(p) - 1, 2):
            cp = (p[i] << 8) | p[i + 1]
            if cp:
                s.append(chr((cp + offset) & 0xFFFF))
        out.append("".join(s))
    return "|".join(out)


def score(txt: str) -> float:
    if not txt:
        return 0.0
    return sum(c in COMMON for c in txt) / len(txt)


def extract(path: str, offset=None):
    data = open(path, "rb").read()
    content = inflate_all(data)
    # Object streams can hold further content streams, but only recurse when the file
    # actually declares one — re-scanning every inflated blob unconditionally is
    # quadratic and hangs on large PDFs.
    if b"/ObjStm" in data:
        content += inflate_all(content)
    parts = operands(content)
    if not parts:
        return "", "no text operands found"
    if offset is not None:
        return render(parts, "2byte", offset), f"2byte offset={offset}"
    best = (render(parts, "1byte"), "1byte", 0)
    best_s = score(best[0])
    for off in range(-64, 65):
        t = render(parts, "2byte", off)
        s = score(t)
        if s > best_s:
            best_s, best = s, (t, "2byte", off)
    return best[0], f"{best[1]} offset={best[2]} score={best_s:.2f}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--offset", type=int, default=None)
    a = ap.parse_args()
    txt, how = extract(a.path, a.offset)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"[{how}] {len(txt)} chars", file=sys.stderr)
    print(txt)
