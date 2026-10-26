# pocket

Turn a photo of an irregular object into a true-scale outline, then into a 3D-printable storage pocket (a "nest") in FreeCAD.

Scale comes from a reference of known size lying in the photo, ideally a printed **ArUco marker**, which is found automatically and also lets the script correct a tilted camera. A credit card, dollar bill, half banana (100 × 40 mm), any known rectangle, or a ruler also work.

The full step-by-step guide is in [`photo-to-freecad-nest.md`](photo-to-freecad-nest.md).

## Workflow

1. **Print a marker.** Use the ready-made 60 mm marker in `marker/` (paper PDF, single-STL with a filament change at Z = 1 mm, or two-material 3MF), or generate one with the scripts below. Measure its black square with calipers.
2. **Take the photo.** Object and marker flat on a plain, high-contrast background, shot straight down from as far away as practical.
3. **Trace it.**
   ```
   python scripts/photo_to_outline.py my_photo.jpg --aruco-size 60.2
   ```
   Output goes to `out/`: an exact outline, a clearance outline (grown by 0.4 mm per side by default) as DXF and SVG, and an overlay image to check the trace.
4. **Check it.** Look at the overlay, compare the reported size with calipers, and print a one-layer test of the clearance outline.
5. **Model it.** Import the clearance DXF into FreeCAD, convert it to a sketch, and pocket it out of a block in Part Design.

## Setup

Python 3.10+:

```
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

## Repository layout

| Path | Contents |
|---|---|
| `photo-to-freecad-nest.md` | the full guide: photography, calibration, script flags, FreeCAD steps, known limits |
| `scripts/photo_to_outline.py` | photo → scaled, straightened, simplified DXF + SVG (run with `-h` for all flags) |
| `scripts/make_aruco_marker.py` | printable marker sheet (PDF) |
| `scripts/make_aruco_stl.py` | 3D-printable marker, single STL for a filament-change print |
| `scripts/make_aruco_3mf.py` | 3D-printable marker, two-material 3MF |
| `scripts/strip_metadata.py` | losslessly removes EXIF/GPS/XMP metadata from JPEGs, in place |
| `scripts/gps_check.py` | reports images that contain GPS location data |
| `.githooks/pre-commit` | blocks commits of images with GPS data (see below) |
| `marker/` | the 60 mm `DICT_4X4_50` id 7 marker, ready to print |
| `match_outline/` | finished outline from the worked example (DXF, SVG, preview) |
| `*.FCStd` | FreeCAD models (`mpocket.FCStd` is the pocket assembly) |
| `mpocket-AssemblyCut.3mf` | sliceable export of the pocket |
| `20261025_*.jpg` | source photos |

Generated output in `out/`, the virtual environment and FreeCAD backup files (`*.FCBak`) are not tracked.

## Photo privacy

Phone photos usually embed the GPS location where they were taken. Strip it before committing:

```
python scripts/strip_metadata.py my_photo.jpg
```

A pre-commit hook refuses to commit JPEG or PNG files that still contain location data. Git does not enable repository hooks automatically, so turn it on once per clone:

```
git config core.hooksPath .githooks
```

## Requirements

- Python with `opencv-python` (4.7+ or 5.x, with the `aruco` module), `numpy`, `scipy`, `shapely`, `ezdxf`, `pillow`
- [FreeCAD](https://www.freecad.org/) 1.0 or later
