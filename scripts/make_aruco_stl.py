#!/usr/bin/env python3
"""Make a 3D-printable ArUco marker as a binary STL.

Black cells are BLACK_H tall, white cells and the quiet-zone border are WHITE_H tall, so with a filament
change at Z = WHITE_H (white below, black above) you get a two-colour marker from one STL.

Usage:  python3 make_aruco_stl.py [size_mm] [marker_id]      e.g.  python3 make_aruco_stl.py 60 7
Requires: opencv-python (with aruco), numpy
"""
import sys, struct
import numpy as np, cv2

DICT      = 'DICT_4X4_50'    # must match ARUCO_DICT in photo_to_outline.py
MARKER_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 7
SIZE_MM   = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0   # outer BLACK square
BLACK_H   = 2.0              # height of black cells (mm)
WHITE_H   = 1.0              # height of white cells and the border (mm); put the colour change here
MARGIN_CELLS = 1             # white quiet zone around the marker, in cells (1 is the minimum for detection)
OUT       = 'aruco_%s_id%d_%dmm.stl' % (DICT.replace('DICT_', ''), MARKER_ID, round(SIZE_MM))

dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
bits = int(DICT.split('_')[1][0])                  # 4 for 4X4
n = bits + 2                                       # cells across, including the black border
k = 10
img = cv2.aruco.generateImageMarker(dic, MARKER_ID, n * k)
grid = np.array([[img[i * k + k // 2, j * k + k // 2] for j in range(n)] for i in range(n)])
black = grid < 128                                 # row 0 is the TOP of the marker as seen from above

m = MARGIN_CELLS
H = np.full((n + 2 * m, n + 2 * m), WHITE_H)
H[m:m + n, m:m + n] = np.where(black, BLACK_H, WHITE_H)
ny, nx = H.shape
c = SIZE_MM / n                                    # cell size (mm)

tris = []
def add(a, b, cc, normal):
    a, b, cc = map(np.array, (a, b, cc))
    if np.dot(np.cross(b - a, cc - a), normal) < 0:    # wind counter-clockwise seen from outside
        b, cc = cc, b
    tris.append((a, b, cc))

def quad(p, q, r, s, normal):
    add(p, q, r, normal); add(p, r, s, normal)

for i in range(ny):
    for j in range(nx):
        h = H[i, j]
        x0, x1 = j * c, (j + 1) * c
        y0, y1 = (ny - i - 1) * c, (ny - i) * c            # image row i -> y, so the marker is not mirrored
        quad((x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h), (0, 0, 1))     # top
        quad((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (0, 0, -1))    # bottom (per cell: no T-junctions)
        for di, dj, (a, b), nrm in (
            (-1, 0, ((x0, y1), (x1, y1)), (0, 1, 0)),      # neighbour above  -> wall on +y edge
            (1, 0, ((x0, y0), (x1, y0)), (0, -1, 0)),      # neighbour below  -> wall on -y edge
            (0, -1, ((x0, y0), (x0, y1)), (-1, 0, 0)),     # neighbour left   -> wall on -x edge
            (0, 1, ((x1, y0), (x1, y1)), (1, 0, 0)),       # neighbour right  -> wall on +x edge
        ):
            ii, jj = i + di, j + dj
            hn = H[ii, jj] if 0 <= ii < ny and 0 <= jj < nx else 0.0
            if hn < h:                                      # each wall is built once, from the taller side
                quad((a[0], a[1], hn), (b[0], b[1], hn), (b[0], b[1], h), (a[0], a[1], h), nrm)

with open(OUT, 'wb') as f:
    f.write(('ArUco marker %s id %d %.1f mm' % (DICT, MARKER_ID, SIZE_MM)).encode().ljust(80)[:80])   # header must be exactly 80 bytes
    f.write(struct.pack('<I', len(tris)))
    for a, b, cc in tris:
        nv = np.cross(b - a, cc - a); nv = nv / np.linalg.norm(nv)
        f.write(struct.pack('<12fH', *nv, *a, *b, *cc, 0))
print('wrote %s: %d triangles, plate %.2f x %.2f mm, marker %.2f mm, cell %.3f mm, %.1f/%.1f mm tall'
      % (OUT, len(tris), nx * c, ny * c, SIZE_MM, c, BLACK_H, WHITE_H))
