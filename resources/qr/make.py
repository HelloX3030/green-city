#!/usr/bin/env python3
"""Generate the Green City QR code and an A4 print sheet.

    python3 resources/qr/make.py        # writes greencity-qr.svg, print-sheet.html, print-sheet.pdf

Needs `qrencode` (apt install qrencode) and google-chrome for the PDF.
"""
import subprocess, pathlib, shutil

URL = "https://greencity.parsalotfi.com/"
HERE = pathlib.Path(__file__).resolve().parent

# --- module matrix from qrencode (level M, no margin) ---
ascii = subprocess.run(["qrencode", "-l", "M", "-m", "0", "-t", "ASCII", "-o", "-", URL],
                       check=True, capture_output=True, text=True).stdout
rows = [line for line in ascii.splitlines() if line.strip("# ")=="" and line]
rows = [line for line in ascii.splitlines() if line]
n = len(rows)
matrix = [[rows[y][2*x:2*x+2] == "##" for x in range(n)] for y in range(n)]

def qr_group(size_mm, x0=0.0, y0=0.0, quiet=2):
    """Black modules as one <path>, code incl. quiet zone fits in size_mm square."""
    units = n + 2*quiet
    m = size_mm / units
    d = []
    for y in range(n):
        for x in range(n):
            if matrix[y][x]:
                d.append(f"M{x0+(x+quiet)*m:.3f} {y0+(y+quiet)*m:.3f}h{m:.3f}v{m:.3f}h-{m:.3f}z")
    return f'<rect x="{x0}" y="{y0}" width="{size_mm}" height="{size_mm}" fill="#fff"/><path d="{"".join(d)}" fill="#000"/>'

# --- master SVG: 100 mm, quiet zone included, nothing else ---
master = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">'
          f'<!-- {URL} · QR level M · {n}x{n} modules · regenerate with make.py -->'
          f'{qr_group(100)}</svg>')
(HERE/"greencity-qr.svg").write_text(master)

# --- print sheet (A4, mm) ---
CASE = 24.5       # lid pocket is 25 x 25 mm (3d-model/CreateLeafMacro.py, rebaje_qr)
HAND = 40.0       # handout tile: code width; tile has URL text underneath
cut = 'fill="none" stroke="#999" stroke-width="0.15" stroke-dasharray="1 1"'
parts = []
# row 1: case stickers
x, y = 15, 20
parts.append(f'<text x="15" y="15" font-size="3.2" fill="#444">Case · 24.5 mm · fits the lid pocket · cut on the dashed line</text>')
for i in range(7):
    parts.append(qr_group(CASE, x, y) + f'<rect x="{x}" y="{y}" width="{CASE}" height="{CASE}" {cut}/>')
    x += CASE + 3
# rows 2-3: handout tiles with URL
parts.append(f'<text x="15" y="62" font-size="3.2" fill="#444">Handout · 40 mm · with URL</text>')
tile_w, tile_h = HAND + 8, HAND + 14
for r in range(2):
    x = 15
    y = 66 + r*(tile_h + 4)
    for i in range(3):
        parts.append(f'<rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" {cut}/>'
                     + qr_group(HAND, x+4, y+4)
                     + f'<text x="{x+tile_w/2}" y="{y+HAND+10}" font-size="3.4" text-anchor="middle" '
                       f'font-family="Helvetica, Arial, sans-serif" fill="#000">greencity.parsalotfi.com</text>')
        x += tile_w + 3
# bottom: one big one for a poster / table
parts.append(f'<text x="15" y="185" font-size="3.2" fill="#444">Table / poster · 80 mm</text>')
parts.append(qr_group(80, 15, 189) + f'<rect x="15" y="189" width="80" height="80" {cut}/>'
             + f'<text x="55" y="277" font-size="5" text-anchor="middle" font-family="Helvetica, Arial, sans-serif">greencity.parsalotfi.com</text>')
parts.append(f'<text x="195" y="290" font-size="2.6" text-anchor="end" fill="#888">{URL} · print at 100 % (no "fit to page")</text>')

sheet_svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297" '
             'font-family="Helvetica, Arial, sans-serif">' + "".join(parts) + '</svg>')
html = ('<!doctype html><meta charset="utf-8"><title>Green City QR print sheet</title>'
        '<style>@page{size:A4;margin:0}html,body{margin:0}svg{display:block}</style>' + sheet_svg)
(HERE/"print-sheet.html").write_text(html)

chrome = shutil.which("google-chrome") or shutil.which("chromium")
if chrome:
    subprocess.run([chrome, "--headless=new", "--no-pdf-header-footer", "--disable-gpu",
                    f"--print-to-pdf={HERE/'print-sheet.pdf'}", str(HERE/"print-sheet.html")],
                   check=True, capture_output=True)
    print("wrote print-sheet.pdf")
print(f"{n}x{n} modules, wrote greencity-qr.svg, print-sheet.html")
