# Photo → scaled outline → FreeCAD storage nest

A repeatable workflow for turning a photo of an irregular object into a true-scale, straightened, simplified outline (DXF + SVG), then into a 3D-printable storage nest in FreeCAD 1.1.1. Scale comes from a reference object of known size in the photo: a printed **ArUco marker** (recommended: found automatically and can straighten perspective), a **half banana** (100 × 40 mm), a credit card, a dollar bill, or a ruler.

Worked example: a handheld antenna analyzer (body ~97 × 241 mm with a connector on top). Numbers from that run are marked *(example)*.

## Files in this kit

| File | What it is |
|---|---|
| `photo-to-freecad-nest.md` | this guide |
| `scripts/photo_to_outline.py` | photo → scaled, straightened, simplified DXF + SVG |
| `scripts/make_aruco_marker.py` | printable marker sheet (PDF), default 60 mm |
| `scripts/make_aruco_stl.py` | 3D-printable marker, one STL (black 2 mm, white 1 mm) |
| `scripts/make_aruco_3mf.py` | 3D-printable marker, two-material 3MF (white base + black cells) |
| `marker/aruco_4X4_50_id7_60mm.pdf / .stl / .3mf` | the 60 mm, id 7 marker, ready to print |
| `match_outline/` | the finished outline of the antenna analyzer from the worked example (DXF, SVG, preview) |

---

## 1. Take the photo

- **Plain, high-contrast background.** A dark object on white paper is ideal. Edge-detect tracing picks up every printed line and text, so avoid busy backgrounds.
- **Straight down, from as far away as practical** (use some zoom). The top of a tall object is closer to the lens than its base, so it looks bigger. The farther away, the smaller this error.
- **Put a reference object in the frame**, lying flat on the same surface as the object, not touching it, with a clear gap around it. A bigger reference gives a better scale; the half banana (100 × 40 mm) or a dollar bill (156 × 66 mm) beats a credit card (86 × 54 mm).
- **Best option: a printed ArUco marker** (section 2). It needs no box drawn around it and lets the script correct a tilted camera.
- **Make the reference contrast with the background** (dark on light, or light on dark) and keep it free of shadows. It must be a flat rectangle-ish shape; rounded ends and corners are fine.
- Avoid shadows next to the object edge (they get traced as part of the object). Diffuse light helps.

## 2. Calibrate the scale

You tell the script which reference you used (`REF`) and draw a box around it (`REF_BOX`, in pixels of the **original, full-resolution** image). It then measures the reference's long and short sides in pixels, so no tick-counting is needed.

| `REF` | Size (long × short) |
|---|---|
| `'aruco'` | printed marker, size set by `ARUCO_SIZE_MM` (default 60 mm) |
| `'half_banana'` | 100 × 40 mm |
| `'credit_card'` | 85.60 × 53.98 mm (ISO ID-1) |
| `'dollar_bill'` | 155.96 × 66.29 mm (US note, 6.14 × 2.61 in) |
| `(long_mm, short_mm)` | any other rectangle, e.g. `(210.0, 148.5)` for an A5 sheet |
| `'ruler'` | two tick marks a known distance apart (Appendix B shows how to find them) |

### ArUco marker (recommended)

An ArUco marker is a square black-and-white barcode that OpenCV detects automatically and returns the four corner positions of, to a fraction of a pixel.

1. Run `make_aruco_marker.py` (Appendix C). It writes a PDF with a 60 mm marker (`DICT_4X4_50`, id 7) and a 100 mm check line. Print at **100% / Actual size** on matte paper and tape it flat.
2. Measure the black square with calipers and put that value in `ARUCO_SIZE_MM`.
3. Lay the marker flat on the same surface as the object, fully in frame, with its white border visible and not touching the object.
4. Set `REF = 'aruco'`. There is no `REF_BOX` to fill in.

**3D-printed alternative:** `make_aruco_stl.py` (Appendix D) writes an STL with the black cells 2 mm tall and the white cells and a one-cell white border 1 mm tall. Print flat, no supports, white filament first and a filament change at **Z = 1.0 mm** to black (use a layer height that divides 1.0 mm evenly, e.g. 0.2). Measure the black square across its top with calipers and use that for `ARUCO_SIZE_MM`. Prefer matte filament to avoid glare. Run `python3 make_aruco_stl.py 60 7` for a 60 mm marker with id 7 (any size and id from 0 to 49 work).

**Two-material 3MF:** `make_aruco_3mf.py` (Appendix E) writes a 3MF with a white base body (whole plate, 1 mm) and a separate black body (the black cells only, from 1 mm to 2 mm) grouped as one object. Load it in your slicer and assign one filament to each part. Run `python3 make_aruco_3mf.py 60 7` for a 60 mm marker with id 7.

The script measures the four sides, averages them for the scale, and (with `ARUCO_RECTIFY = True`) warps the photo so the marker's plane is exactly top-down, which removes keystoning from an angled camera. It masks the marker out of the object automatically, and prints the side-length spread before and after rectifying as a quality check.

*(tested)* On a synthetic photo with a known scale the result matched the ruler method to within 0.02%. On the same photo with deliberate perspective distortion (marker sides differing by 1.3%), rectifying cut the error from about 0.4% (width) and 0.8% (length) to 0.02% and 0.4%. The remaining error comes from extrapolating a perspective correction measured on a small marker out to the object, so a **bigger marker is better**. The 60 mm default is a good general size; go to 80–100 mm for objects around 250 mm or larger. Rectifying only corrects the surface the marker lies on, not height parallax.

### Rectangle references

How it works: inside `REF_BOX` it separates the reference from the background (Otsu threshold), takes the largest blob, and fits a rotated rectangle. The **long** side sets the scale. The short side is a cross-check: if the two disagree by more than 2% the script prints a warning, which usually means the box includes a shadow or another object, you chose the wrong `REF`, or the reference isn't flat or isn't a true rectangle.

Tips: use a tight box with only the reference in it, make sure `REF_DARKER` matches (dark reference on a light background = `True`), and measure a real synthetic reference with calipers once and set `REF` to its true `(long_mm, short_mm)` if it isn't exactly 100 × 40.

*(tested)* On synthetic photos the scale was recovered to within 0.3% for all three presets, and a deliberately wrong `REF` triggered the mismatch warning.

## 3. Run the script

1. Install requirements (in your virtual environment): `pip install "opencv-python>=4.7" numpy scipy shapely ezdxf pillow`
2. Save the script from Appendix A as `photo_to_outline.py`.
3. Run it on a photo that contains the printed ArUco marker, passing the **measured** size of the marker's black square:

```
python photo_to_outline.py my_photo.jpg --aruco-size 60.2
```

That's all that's needed for a dark object on a light background. Output goes to `./out/` with the photo's name as the prefix. Everything else is automatic: the marker is found without a box, perspective is straightened from it, the dark-object threshold is chosen by Otsu's method, anything touching the photo's edge (a dark backdrop) is ignored, and holes (labels, screws) are filled.

*(tested)* On a fresh synthetic photo (known 120 × 140 mm object, 3° tilt, dark backdrop at the edges) this one-line command measured 120.20 × 140.09 mm and recovered the tilt.

**Common flags** (`python photo_to_outline.py -h` lists them all; each overrides the matching default in the script's SETTINGS block):

| Flag | What it does |
|---|---|
| `--aruco-size MM` | Measured side of the marker's black square. Default 60.0, but **always set what your calipers say** |
| `--name NAME`, `--out DIR` | Output file prefix and folder (default: photo name, `./out/`) |
| `--clearance MM` | Per-side gap for the nest version (default 0.4; 0.3–0.5 mm for FDM) |
| `--simplify MM` | Point-reduction tolerance (default 0.4) |
| `--no-rectify` | Skip the perspective correction from the marker |
| `--aruco-id N` | Use marker id N when several are in the photo (default: the largest) |
| `--keep-box x0,y0,x1,y1` | Only look for the object inside this pixel box. Use it if something else dark is in frame |
| `--dark-thresh N` | Fix the gray level (0–255) below which a pixel is object, instead of automatic |
| `--light-box x0,y0,x1,y1` | Box around light or shiny parts (a metal connector) that the dark threshold misses; add `--paper-patch x0,y0,x1,y1` for a clean background sample |
| `--flatten-top` | Replace a narrow protrusion at the top (e.g. a connector) with a plain rectangle |
| `--ref half_banana` (or `credit_card`, `dollar_bill`, `ruler`, `100x40`) | Use a rectangle reference instead of the marker. Needs `--ref-box x0,y0,x1,y1`; add `--ref-lighter` if it is lighter than the background |

**Worked example (the antenna analyzer photo):** a metal connector the threshold misses, and a backdrop and ruler region to avoid, so it needs the boxes:

```
python photo_to_outline.py analyzer.jpg --aruco-size 60.2 --keep-box 300,0,1500,2040 ^
  --paper-patch 300,300,500,700 --light-box 800,150,1130,540 --dark-thresh 95 --flatten-top
```

(`^` continues a line in Windows `cmd`; in PowerShell use a backtick `` ` ``; on Mac/Linux use a backslash. Or put it all on one line.) The pixel boxes are specific to that photo; a new photo of a plain dark object normally needs none of them.

It does, in order: measure the reference for scale → dark-pixel mask → fill label/screw holes → merge light parts → largest blob → contour → convert to mm → remove tilt (from the dominant straight edges) → optional protrusion flattening → simplify → write exact and clearance versions.

**Outputs**
- `NAME_exact.dxf` / `.svg`: true-size outline
- `NAME_clearance.dxf`: same outline grown by `CLEARANCE_MM` per side. **Use this one for the nest pocket.**
- `NAME_overlay.jpg`: your photo with the traced object in **green** and the detected reference in **blue**

## 4. Check before you trust it

- [ ] **Open `NAME_overlay.jpg`.** The green line should hug the object, with no shadow or background included and no missing parts. The blue box should sit exactly on the reference, and the script should report a mismatch under 2% (rectangle references) or a marker side spread under 0.5% after rectify (ArUco).
- [ ] **Measure the real object** with calipers (length and width) and compare to the printed size. *(example: 96.86 × 241.27 mm.)*
- [ ] If it's off by a consistent percentage, scale the DXF by `real / file` (in FreeCAD, scale before converting to a sketch, or edit the calibration).
- [ ] Print a **one-layer test cutout** of the clearance outline and drop the object in before committing to a deep nest.

## 5. Import into FreeCAD 1.1.1

> Verified against a FreeCAD 1.0 walkthrough. I could not check 1.1-specific changes (the FreeCAD wiki blocked access), so menu names may differ slightly. As far as I know, the Sketcher has no direct DXF import, so the path goes through the Draft workbench.

1. **File → Import**, pick `NAME_clearance.dxf`. In the dialog choose **Simple Part shapes**. To bring the dialog back: **Edit → Preferences → Import-Export → DXF**.
2. Switch to the **Draft** workbench. Select the imported shape. It should be one closed wire. If it came in as separate edges, select them and run **Modification → Upgrade** (shortcut `U`, `P`) to join them.
3. With the wire selected: **Modification → Draft to Sketch**. This makes a standalone sketch on the XY plane.
4. Switch to **Sketcher**, open the sketch, run **Sketch → Validate sketch**, and fix any gaps it reports.
5. **Check the size**: measure an edge or read the bounding box. *(example: 97.66 × 242.07 mm.)* If the units look wrong, it's the DXF import scaling.

The DXF origin is the **lower-left corner of the outline's bounding box**.

### Rotating the sketch if it still needs trimming
- **Inside the sketch:** open the sketch, `Ctrl+A`, then **Sketch → Sketcher tools → Rotate** (select a center, then the angle).
- **Whole sketch:** select it and edit **Attachment Offset → Rotation → Angle** (axis Z, `0 0 1`) if it's attached to a plane in a Body, or **Placement → Angle** if it's standalone. This pivots about the sketch origin (the lower-left corner).
- **To find the angle:** add a temporary **Constrain angle** on a long straight edge vs. the vertical axis, read the value, then delete the constraint.

## 6. Build the nest (Part Design)

1. **Part Design → Create body**, then drag the sketch into the Body in the tree.
2. Make a second sketch on XY with a rectangle larger than the outline by your wall thickness *t* on every side. Using the outline's lower-left origin, the corners are `(-t, -t)` and `(W + t, H + t)`, where `W × H` is the clearance outline size. **Pad** it to the base height (floor + pocket depth).
3. Attach (or reposition) the outline sketch to the top face of the pad so it sits inside the rectangle.
4. **Pocket** the outline sketch to the nest depth. A sensible depth is roughly half the object's thickness so it sits stable and can be lifted out.
5. Add a **finger notch**: a small extra pocket (sketch a circle or slot overlapping one edge of the outline, pocket to the same depth or deeper).
6. Export for printing: select the Body → **File → Export** → STL or 3MF.

The outline sketch is unconstrained geometry. That's fine for a Pocket, but it won't resize parametrically. To resize, scale the wire in Draft before converting it to a sketch.

## 7. Known limits

- **Parallax:** the reference lies on the surface, but tall objects' tops appear slightly larger. This can inflate the outline by a couple of percent. Always check against calipers (step 4).
- **Dark object on light background** is assumed. A light object on a dark background needs `g > threshold` instead of `g < threshold` in the segmentation step.
- **ArUco needs a sharp, flat, fully visible marker** with a white border. Curled paper, glare or motion blur make detection fail or the spread warning fire. If rectified coordinates matter: `KEEP_BOX` and the other boxes refer to the rectified photo, which keeps the marker's position and orientation, so they stay close to the original coordinates.
- **Straightening is a single rotation.** Residual ±0.5° errors usually come from camera perspective or real taper in the object, not tilt.
- **Flattened protrusions** use their widest point, so narrower sections get extra room. Edit the script to make a two-step shape if you want a snugger fit.
- **The reference is only as good as its true size.** Credit cards and bills are standardized; a homemade half banana is only as exact as your cutting, so measure it.
- **Flat or low objects** are better scanned on a flatbed scanner (no perspective error, scale known from DPI).

---

## Appendix A: `photo_to_outline.py`

```python
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
```

## Appendix B: find ruler tick positions (only for `REF = 'ruler'`)

Crop a band that covers the **long inch tick marks** of the ruler (adjust the rows), then list dark vertical peaks. Ticks 1/8 in apart show up as evenly spaced peaks; the inch marks are every 8th peak.

```python
import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks

im = np.array(Image.open('photo.jpg').convert('L')).astype(float)
ROW0, ROW1 = 2122, 2152                 # rows crossing the tick marks (inspect a crop first)
prof = im[ROW0:ROW1, :].mean(axis=0)
dark = uniform_filter1d(prof, 41) - prof
peaks, _ = find_peaks(dark, height=12, distance=8)
print(peaks.tolist())                    # x positions of ticks, in original pixels
```

*(example)* peaks were ~24.4 px apart (1/8 in); inch marks at x = 180, 377, 573, 769, 964, 1159, 1353, 1548, 1742 for 3 in through 11 in.

## Appendix C: `make_aruco_marker.py`

Writes a letter or A4 PDF with the marker at an exact physical size and a 100 mm check line. Print at 100% / Actual size, then measure the black square with calipers.

```python
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
```

## Appendix D: `make_aruco_stl.py`

Binary STL of the marker, checked watertight, with the correct (non-mirrored) orientation. Black = `BLACK_H`, white and border = `WHITE_H`.

```python
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
```

## Appendix E: `make_aruco_3mf.py`

Two bodies (white base, black cells) that touch but never overlap. Checked: both closed and consistently wound, volumes exact, marker decodes from the geometry.

```python
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
```
