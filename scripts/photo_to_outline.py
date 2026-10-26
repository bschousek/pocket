#!/usr/bin/env python3
"""Photo -> scaled, straightened, simplified outline (DXF + SVG, mm).

Scale comes from a reference of known size lying flat next to the object:
  'aruco'        a printed ArUco marker (see make_aruco_marker.py). Found automatically, no box needed,
                 and it can also straighten perspective (ARUCO_RECTIFY).
  'half_banana'  100 x 40 mm rectangle
  'credit_card'  85.6 x 53.98 mm (ISO ID-1)
  'dollar_bill'  155.96 x 66.29 mm (US note, 6.14 x 2.61 in)
  'ruler'        two tick marks a known distance apart (see TICK_* below)
  (long_mm, short_mm)  any other rectangle, e.g. REF = (210.0, 148.5)

Usage (marker photo, black square measured at 60.2 mm):
  python photo_to_outline.py my_photo.jpg --aruco-size 60.2
Every SETTINGS value below is a default that a command-line flag overrides; run with -h for the list.
Requires: opencv-python (4.7+ or 5.x, with the aruco module), numpy, scipy, shapely, ezdxf
"""
import os, argparse
import numpy as np, cv2, ezdxf
from scipy.ndimage import binary_fill_holes
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity

# ---------------- SETTINGS ----------------
SRC    = 'photo.jpg'
OUTDIR = './out/'
NAME   = 'object'

# --- Scale reference -------------------------------------------------------
REF        = 'aruco'                # 'aruco' | 'half_banana' | 'credit_card' | 'dollar_bill' | 'ruler' | (long_mm, short_mm)

# REF = 'aruco'
ARUCO_DICT      = 'DICT_4X4_50'     # must match the marker you printed
ARUCO_ID        = None              # None = use the largest marker found; or an int to pick one
ARUCO_SIZE_MM   = 60.0              # side of the OUTER BLACK square, measured with calipers after printing
ARUCO_RECTIFY   = True              # straighten perspective so the marker's plane is true top-down

# REF = a rectangle (half_banana / credit_card / dollar_bill / (long, short))
REF_BOX    = None                   # x0, y0, x1, y1 in ORIGINAL pixels around a rectangle reference (not needed for aruco)
REF_DARKER = True                   # True: reference is darker than the background; False: lighter

# REF = 'ruler': x pixels of two ticks TICK_INCHES apart
TICK_A_PX, TICK_B_PX, TICK_INCHES = 180, 1742, 8.0

# --- Segmentation of the object -------------------------------------------
DARK_THRESH = None                  # gray below this = object (dark object, light background). None = automatic (Otsu)
KEEP_BOX    = None                  # x0, y0, x1, y1: only look here. None = whole photo
PAPER_PATCH = None                  # x0, y0, x1, y1 of clean background, for light/shiny parts. None = auto
LIGHT_PARTS_BOX = None              # x0, y0, x1, y1 around light/shiny parts the dark threshold misses (e.g. a metal connector)
LIGHT_DIFF  = 28                    # brightness difference from background that counts as object in that box

# --- Cleanup / output -----------------------------------------------------
SIMPLIFY_MM       = 0.4             # polyline simplification tolerance
CLEARANCE_MM      = 0.4             # per-side print clearance for the nest version
FLATTEN_TOP       = False           # replace a narrow protrusion at the top (e.g. connector) with a rectangle
BODY_MIN_WIDTH_MM = 60              # a slice wider than this counts as body, not the protrusion
# ------------------------------------------

PRESETS = {
    'half_banana': (100.0, 40.0),
    'credit_card': (85.60, 53.98),
    'dollar_bill': (155.96, 66.29),
}

def _box(t):
    return tuple(int(float(v)) for v in t.split(','))

ap = argparse.ArgumentParser(description='Photo -> scaled, straightened, simplified outline (DXF + SVG, mm)')
ap.add_argument('photo', nargs='?', default=SRC, help='input photo')
ap.add_argument('--name', default=None, help='output file prefix (default: the photo file name)')
ap.add_argument('--out', default=OUTDIR, help='output folder')
ap.add_argument('--ref', default=None, help='aruco | half_banana | credit_card | dollar_bill | ruler | LONGxSHORT in mm, e.g. 100x40')
ap.add_argument('--aruco-size', type=float, default=ARUCO_SIZE_MM, help='measured side of the black marker square, mm')
ap.add_argument('--aruco-id', type=int, default=ARUCO_ID, help='marker id to use (default: largest found)')
ap.add_argument('--no-rectify', action='store_true', help='do not straighten perspective using the marker')
ap.add_argument('--ref-box', type=_box, default=REF_BOX, help='x0,y0,x1,y1 around a rectangle reference')
ap.add_argument('--ref-lighter', action='store_true', help='a rectangle reference is lighter than its background')
ap.add_argument('--keep-box', type=_box, default=KEEP_BOX, help='x0,y0,x1,y1: only look for the object here')
ap.add_argument('--dark-thresh', type=int, default=DARK_THRESH, help='gray level below which a pixel is object (default: auto)')
ap.add_argument('--light-box', type=_box, default=LIGHT_PARTS_BOX, help='x0,y0,x1,y1 around light/shiny parts')
ap.add_argument('--paper-patch', type=_box, default=PAPER_PATCH, help='x0,y0,x1,y1 of clean background (with --light-box)')
ap.add_argument('--clearance', type=float, default=CLEARANCE_MM, help='print clearance per side, mm')
ap.add_argument('--simplify', type=float, default=SIMPLIFY_MM, help='simplification tolerance, mm')
ap.add_argument('--flatten-top', action='store_true', help='replace a narrow protrusion at the top with a rectangle')
args = ap.parse_args()

SRC = args.photo
NAME = args.name or os.path.splitext(os.path.basename(SRC))[0]
OUTDIR = args.out if args.out.endswith(('/', '\\')) else args.out + os.sep
if args.ref:
    r = args.ref.lower()
    REF = tuple(float(v) for v in r.split('x')) if 'x' in r and r[0].isdigit() else r
ARUCO_SIZE_MM, ARUCO_ID = args.aruco_size, args.aruco_id
ARUCO_RECTIFY = ARUCO_RECTIFY and not args.no_rectify
REF_BOX, REF_DARKER = args.ref_box, REF_DARKER and not args.ref_lighter
KEEP_BOX, DARK_THRESH = args.keep_box, args.dark_thresh
LIGHT_PARTS_BOX, PAPER_PATCH = args.light_box, args.paper_patch
CLEARANCE_MM, SIMPLIFY_MM = args.clearance, args.simplify
FLATTEN_TOP = FLATTEN_TOP or args.flatten_top

os.makedirs(OUTDIR, exist_ok=True)
im = cv2.imread(SRC)
if im is None:
    raise SystemExit('cannot read ' + SRC)
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
ov = im.copy()
ref_poly = None          # polygon (pixels) covering the reference, masked out of the object


def side_lengths(c):
    return np.array([np.linalg.norm(c[(i + 1) % 4] - c[i]) for i in range(4)])


def find_aruco():
    """Detect the marker in the current grayscale image; return (id, 4x2 float32 corners, clockwise from its top-left)."""
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT))
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX   # sub-pixel corners: matters for scale and rectify
    corners, ids, _ = cv2.aruco.ArucoDetector(dic, params).detectMarkers(g)
    if ids is None or len(ids) == 0:
        raise SystemExit('no ArUco marker found. Is ARUCO_DICT right ("%s")? Is the marker sharp, '
                         'fully in frame, and surrounded by a white border?' % ARUCO_DICT)
    found = [(int(i), c.reshape(4, 2).astype(np.float32)) for i, c in zip(ids.ravel(), corners)]
    print('ArUco ids found:', [f[0] for f in found])
    if ARUCO_ID is not None:
        found = [f for f in found if f[0] == ARUCO_ID]
        if not found:
            raise SystemExit('marker id %d not found' % ARUCO_ID)
    return max(found, key=lambda f: cv2.contourArea(f[1]))


def measure_reference(long_mm, short_mm):
    """Find the reference rectangle inside REF_BOX; return (scale_long, scale_short, long_px, short_px)."""
    if REF_BOX is None:
        raise SystemExit('a rectangle reference needs --ref-box x0,y0,x1,y1 (pixels around the reference)')
    x0, y0, x1, y1 = REF_BOX
    roi = cv2.GaussianBlur(g[y0:y1, x0:x1], (5, 5), 0)
    t, _ = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = ((roi < t) if REF_DARKER else (roi > t)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        raise SystemExit('no reference found in REF_BOX - check REF_BOX and REF_DARKER')
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    cnts, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    rect = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
    lp, sp = sorted(rect[1], reverse=True)
    box_pts = (cv2.boxPoints(rect) + [x0, y0]).astype(np.int32)
    cv2.polylines(ov, [box_pts.reshape(-1, 1, 2)], True, (255, 0, 0), 4)
    return lp / long_mm, sp / short_mm, lp, sp


# ---- scale ----
if REF == 'ruler':
    px_per_mm = (TICK_B_PX - TICK_A_PX) / TICK_INCHES / 25.4
    print('scale from ruler: %.4f px/mm' % px_per_mm)

elif REF == 'aruco':
    mid, mc = find_aruco()
    s = side_lengths(mc)
    spread = (s.max() - s.min()) / s.mean() * 100
    print('marker id %d: sides %s px, spread %.1f%%' % (mid, np.round(s, 1).tolist(), spread))
    if ARUCO_RECTIFY:
        # map the 4 corners to a perfect square (same centre, same orientation, same mean size),
        # which removes perspective for everything lying in the marker's plane
        ctr, side = mc.mean(axis=0), s.mean()
        v = (mc[1] - mc[0]) + (mc[2] - mc[3])
        a = np.arctan2(v[1], v[0])
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        h = side / 2
        tgt = (ctr + np.array([[-h, -h], [h, -h], [h, h], [-h, h]]) @ R.T).astype(np.float32)
        Hm = cv2.getPerspectiveTransform(mc, tgt)
        im = cv2.warpPerspective(im, Hm, (im.shape[1], im.shape[0]), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        ov = im.copy()
        cv2.imwrite(OUTDIR + NAME + '_rectified.jpg', im)
        mid, mc = find_aruco()                       # re-measure on the straightened image
        s = side_lengths(mc)
        spread2 = (s.max() - s.min()) / s.mean() * 100
        print('after rectify: sides spread %.2f%% (was %.1f%%)' % (spread2, spread))
        if spread2 > 0.5:
            print('WARNING: marker still not square after rectify (%.2f%%) - marker may be curled or blurry.' % spread2)
    elif spread > 2:
        print('WARNING: marker sides differ by %.1f%% - the photo has perspective. Set ARUCO_RECTIFY = True.' % spread)
    px_per_mm = s.mean() / ARUCO_SIZE_MM
    print('scale from marker: %.4f px/mm (marker %.2f mm)' % (px_per_mm, ARUCO_SIZE_MM))
    cv2.polylines(ov, [mc.astype(np.int32).reshape(-1, 1, 2)], True, (255, 0, 0), 4)
    c0 = mc.mean(axis=0)
    ref_poly = (c0 + (mc - c0) * 1.8).astype(np.int32)   # marker plus its white quiet zone

else:
    long_mm, short_mm = PRESETS[REF] if isinstance(REF, str) else REF
    s_long, s_short, lp, sp = measure_reference(long_mm, short_mm)
    px_per_mm = s_long                       # the long side has the smaller relative error
    diff = abs(s_long - s_short) / s_long * 100
    print('reference %.1f x %.1f px -> %.4f px/mm (long), %.4f px/mm (short), mismatch %.1f%%'
          % (lp, sp, s_long, s_short, diff))
    if diff > 2:
        print('WARNING: long and short sides disagree by >2 percent - the box may include a shadow or '
              'another object, or the reference is not a flat rectangle of the size you chose.')

# ---- segment the object ----
Hi, Wi = g.shape
x0, y0, x1, y1 = KEEP_BOX if KEEP_BOX else (0, 0, Wi, Hi)
valid = np.zeros_like(g, bool); valid[y0:y1, x0:x1] = True      # where to look...
excl = np.zeros_like(g, np.uint8)                               # ...except on the reference itself
if REF == 'aruco':
    cv2.fillConvexPoly(excl, ref_poly.reshape(-1, 1, 2), 1)
elif REF != 'ruler':
    rx0, ry0, rx1, ry1 = REF_BOX; excl[ry0:ry1, rx0:rx1] = 1
valid &= (excl == 0)


def otsu(values):
    p = np.bincount(values, minlength=256).astype(float); p /= p.sum()
    w = np.cumsum(p); mu = np.cumsum(p * np.arange(256))
    with np.errstate(divide='ignore', invalid='ignore'):
        var = (mu[-1] * w - mu) ** 2 / (w * (1 - w))
    return int(np.nanargmax(var))


thresh = DARK_THRESH if DARK_THRESH is not None else otsu(cv2.GaussianBlur(g, (5, 5), 0)[valid])
print('object threshold: gray < %d%s' % (thresh, '' if DARK_THRESH is not None else ' (automatic)'))
m = ((g < thresh) & valid).astype(np.uint8)
if LIGHT_PARTS_BOX:
    if PAPER_PATCH:
        px0, py0, px1, py1 = PAPER_PATCH
        paper = np.median(g[py0:py1, px0:px1])
    else:
        paper = np.percentile(g[valid], 75)                     # background usually dominates the bright side
    lx0, ly0, lx1, ly1 = LIGHT_PARTS_BOX
    light = np.zeros_like(m)
    light[ly0:ly1, lx0:lx1] = (np.abs(g[ly0:ly1, lx0:lx1].astype(float) - paper) > LIGHT_DIFF)
    light = cv2.morphologyEx(light, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (121, 9)))
    m = np.maximum(m, light * valid.astype(np.uint8))
E = cv2.getStructuringElement
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, E(cv2.MORPH_ELLIPSE, (25, 25)))
m = binary_fill_holes(m).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, E(cv2.MORPH_ELLIPSE, (15, 15)))
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
areas = st[:, cv2.CC_STAT_AREA].copy(); areas[0] = 0
touches_edge = (st[:, 0] == 0) | (st[:, 1] == 0) | (st[:, 0] + st[:, 2] >= Wi) | (st[:, 1] + st[:, 3] >= Hi)
cand = np.where(touches_edge, 0, areas)                         # a blob touching the photo edge is usually the backdrop
k = int(np.argmax(cand)) if cand.max() > 0 else int(np.argmax(areas))
m = binary_fill_holes(lab == k).astype(np.uint8)

c = max(cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
c = cv2.approxPolyDP(c, 0.25 * px_per_mm, True)[:, 0, :].astype(float)
cv2.polylines(ov, [c.astype(np.int32).reshape(-1, 1, 2)], True, (0, 255, 0), 3)
cv2.imwrite(OUTDIR + NAME + '_overlay.jpg', cv2.resize(ov, None, fx=0.5, fy=0.5))  # CHECK THIS: green = object, blue = reference

pts = np.stack([c[:, 0], -c[:, 1]], 1) / px_per_mm          # mm, y up

# ---- straighten: dominant edge direction (4-fold circular mean over long edges) ----
P = np.vstack([pts, pts[:1]]); d = np.diff(P, axis=0); L = np.hypot(*d.T)
th = np.arctan2(d[:, 1], d[:, 0]); w = np.where(L > 15, L, 0)
tilt = np.degrees(np.arctan2((w * np.sin(4 * th)).sum(), (w * np.cos(4 * th)).sum()) / 4)
poly = affinity.rotate(Polygon(pts), -tilt, origin='centroid')
print('tilt removed: %.2f deg' % tilt)

if FLATTEN_TOP:
    minx, miny, maxx, maxy = poly.bounds
    def width(y):
        s = poly.intersection(box(minx - 1, y - .05, maxx + 1, y + .05))
        return 0 if s.is_empty else s.bounds[2] - s.bounds[0]
    body_top = max(y for y in np.linspace(miny, maxy, 2000) if width(y) > BODY_MIN_WIDTH_MM)
    cb = poly.intersection(box(minx - 1, body_top + 2, maxx + 1, maxy + 1)).bounds
    body = poly.intersection(box(minx - 1, miny - 1, maxx + 1, body_top))
    poly = unary_union([body, box(cb[0], body_top - .5, cb[2], maxy)])
poly = poly.simplify(SIMPLIFY_MM, preserve_topology=True)


def norm(p):
    a = np.array(p.exterior.coords)[:-1]
    return a - a.min(axis=0)


def write(a, name):
    W, H = a.max(axis=0)
    dpath = 'M ' + ' L '.join('%.3f,%.3f' % (x, H - y) for x, y in a) + ' Z'
    open(OUTDIR + name + '.svg', 'w').write(
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.3fmm" height="%.3fmm" viewBox="0 0 %.3f %.3f">'
        '<path d="%s" fill="none" stroke="#000" stroke-width="0.2"/></svg>' % (W, H, W, H, dpath))
    doc = ezdxf.new('R2010'); doc.units = 4                      # 4 = millimetres
    doc.modelspace().add_lwpolyline([(float(x), float(y)) for x, y in a], close=True)
    doc.saveas(OUTDIR + name + '.dxf')
    print('%s: %.2f x %.2f mm, %d points' % (name, W, H, len(a)))


exact = norm(poly)
write(exact, NAME + '_exact')
write(norm(Polygon(exact).buffer(CLEARANCE_MM, join_style=1, resolution=8).simplify(0.05)),
      NAME + '_clearance')
