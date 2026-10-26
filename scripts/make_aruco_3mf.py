#!/usr/bin/env python3
"""Make a two-material 3MF ArUco marker: a white base body and a black cells body, grouped as one object.

  white body : the whole plate (marker + white quiet-zone border), Z = 0 .. WHITE_H
  black body : only the black cells, stacked on top,               Z = WHITE_H .. BLACK_H
The bodies touch but never overlap, so the slicer can assign one filament to each.

Usage:  python3 make_aruco_3mf.py [size_mm] [marker_id]        e.g.  python3 make_aruco_3mf.py 60 7
Requires: opencv-python (with aruco), numpy
"""
import sys, zipfile
import numpy as np, cv2

DICT      = 'DICT_4X4_50'    # must match ARUCO_DICT in photo_to_outline.py
MARKER_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 7
SIZE_MM   = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0   # outer BLACK square
BLACK_H   = 2.0              # top of the black cells (mm)
WHITE_H   = 1.0              # top of the white base (mm)
MARGIN_CELLS = 1             # white quiet zone around the marker, in cells (1 is the minimum)
OUT       = 'aruco_%s_id%d_%dmm.3mf' % (DICT.replace('DICT_', ''), MARKER_ID, round(SIZE_MM))

dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
n = int(DICT.split('_')[1][0]) + 2                       # cells across incl. the black border (6 for 4X4)
k = 10
img = cv2.aruco.generateImageMarker(dic, MARKER_ID, n * k)
black_marker = np.array([[img[i * k + k // 2, j * k + k // 2] < 128 for j in range(n)] for i in range(n)])
m = MARGIN_CELLS
ny = nx = n + 2 * m
c = SIZE_MM / n                                          # cell size (mm)

white_mask = np.ones((ny, nx), bool)                     # the whole plate
black_mask = np.zeros((ny, nx), bool)
black_mask[m:m + n, m:m + n] = black_marker              # image row 0 = top of the marker as seen from above


def cell_mesh(mask, z0, z1):
    """Indexed, watertight mesh of the cells set in mask, from z0 to z1. Row 0 is the top (max y)."""
    verts, index, tris = [], {}, []
    def vid(p):
        key = tuple(np.round(p, 5))
        if key not in index:
            index[key] = len(verts); verts.append(key)
        return index[key]
    def add(a, b, cc, normal):
        a, b, cc = map(np.array, (a, b, cc))
        if np.dot(np.cross(b - a, cc - a), normal) < 0:      # counter-clockwise seen from outside
            b, cc = cc, b
        tris.append((vid(a), vid(b), vid(cc)))
    def quad(p, q, r, s, normal):
        add(p, q, r, normal); add(p, r, s, normal)
    for i in range(ny):
        for j in range(nx):
            if not mask[i, j]:
                continue
            x0, x1 = j * c, (j + 1) * c
            y0, y1 = (ny - i - 1) * c, (ny - i) * c
            quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1))
            quad((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (0, 0, -1))
            for di, dj, (a, b), nrm in (
                (-1, 0, ((x0, y1), (x1, y1)), (0, 1, 0)),
                (1, 0, ((x0, y0), (x1, y0)), (0, -1, 0)),
                (0, -1, ((x0, y0), (x0, y1)), (-1, 0, 0)),
                (0, 1, ((x1, y0), (x1, y1)), (1, 0, 0)),
            ):
                ii, jj = i + di, j + dj
                if not (0 <= ii < ny and 0 <= jj < nx and mask[ii, jj]):     # wall only on an exposed side
                    quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), nrm)
    return verts, tris


def mesh_xml(verts, tris):
    v = ''.join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % p for p in verts)
    t = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % t for t in tris)
    return '<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh>' % (v, t)


wv, wt = cell_mesh(white_mask, 0.0, WHITE_H)
bv, bt = cell_mesh(black_mask, WHITE_H, BLACK_H)

model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
         '<metadata name="Title">ArUco %s id %d, %.1f mm</metadata>'
         '<resources>'
         '<basematerials id="1"><base name="White" displaycolor="#FFFFFF"/><base name="Black" displaycolor="#000000"/></basematerials>'
         '<object id="2" name="white_base" type="model" pid="1" pindex="0">%s</object>'
         '<object id="3" name="black_cells" type="model" pid="1" pindex="1">%s</object>'
         '<object id="4" name="aruco_marker" type="model"><components><component objectid="2"/><component objectid="3"/></components></object>'
         '</resources><build><item objectid="4"/></build></model>'
         ) % (DICT, MARKER_ID, SIZE_MM, mesh_xml(wv, wt), mesh_xml(bv, bt))

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml',
               '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
               '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr('_rels/.rels',
               '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr('3D/3dmodel.model', model)
print('wrote %s: white %d tris, black %d tris, plate %.1f x %.1f mm, cell %.2f mm, black cells %d'
      % (OUT, len(wt), len(bt), nx * c, ny * c, c, int(black_marker.sum())))
