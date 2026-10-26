#!/usr/bin/env python3
"""Make a print-ready ArUco marker sheet (PDF) with the marker at an exact physical size.

Edit the settings, run:  python3 make_aruco_marker.py
Print at 100% / "Actual size" (NOT "fit to page"), then measure the black square with calipers and
put that number in ARUCO_SIZE_MM in photo_to_outline.py. A 100 mm check line is printed under the marker.
Requires: opencv-python (with aruco), numpy, Pillow
"""
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

DICT      = 'DICT_4X4_50'   # must match ARUCO_DICT in photo_to_outline.py
MARKER_ID = 7
SIZE_MM   = 60.0            # outer black square
DPI       = 600
PAGE      = 'letter'        # 'letter' or 'a4'
OUT       = 'aruco_%s_id%d_%dmm.pdf' % (DICT.replace('DICT_', ''), MARKER_ID, round(SIZE_MM))

mm = lambda v: int(round(v / 25.4 * DPI))
page_mm = (215.9, 279.4) if PAGE == 'letter' else (210.0, 297.0)
W, H = mm(page_mm[0]), mm(page_mm[1])
img = Image.new('1', (W, H), 1)                              # 1-bit, white: stays crisp and lossless in the PDF
d = ImageDraw.Draw(img)

n = mm(SIZE_MM)
dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
mk = cv2.aruco.generateImageMarker(dic, MARKER_ID, n)
ox, oy = mm(25), mm(25)                                      # 25 mm white margin = plenty of quiet zone
img.paste(Image.fromarray((mk > 127).astype(np.uint8) * 255).convert('1'), (ox, oy))

# 100 mm check line with end ticks
ly = oy + n + mm(15)
d.line([(ox, ly), (ox + mm(100), ly)], fill=0, width=max(2, mm(0.3)))
for x in (ox, ox + mm(100)):
    d.line([(x, ly - mm(3)), (x, ly + mm(3))], fill=0, width=max(2, mm(0.3)))
try:
    font = ImageFont.load_default(size=mm(4))
except TypeError:
    font = ImageFont.load_default()
d.text((ox, ly + mm(5)), 'Check: this line must measure 100 mm. If not, reprint at 100 percent / actual size.', fill=0, font=font)
d.text((ox, ly + mm(12)), '%s  id %d  black square = %.1f mm (measure it and use that value)' % (DICT, MARKER_ID, SIZE_MM),
       fill=0, font=font)

img.save(OUT, resolution=DPI)
print('wrote', OUT, '| marker side %d px at %d dpi = %.3f mm' % (n, DPI, n / DPI * 25.4))
