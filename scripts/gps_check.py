#!/usr/bin/env python3
"""Find GPS location data in JPEG and PNG images (EXIF GPS tags or XMP GPS fields).

Usage:
  python gps_check.py photo.jpg ...    check these files
  python gps_check.py --staged         check images staged for commit (used by .githooks/pre-commit)
Exit code 1 if any file has location data. Standard library only.
"""
import subprocess, struct, sys

IMAGE_EXT = ('.jpg', '.jpeg', '.png')


def tiff_has_gps(t):
    """True if a TIFF/EXIF block has a GPS IFD with any tag besides GPSVersionID."""
    if len(t) < 8 or t[:2] not in (b'II', b'MM'):
        return False
    e = '<' if t[:2] == b'II' else '>'
    try:
        ifd0 = struct.unpack(e + 'I', t[4:8])[0]
        for k in range(struct.unpack(e + 'H', t[ifd0:ifd0 + 2])[0]):
            tag, _, _, val = struct.unpack(e + 'HHII', t[ifd0 + 2 + 12 * k: ifd0 + 14 + 12 * k])
            if tag == 0x8825:                                          # GPS IFD pointer
                n = struct.unpack(e + 'H', t[val:val + 2])[0]
                tags = [struct.unpack(e + 'H', t[val + 2 + 12 * j: val + 4 + 12 * j])[0] for j in range(n)]
                return any(g != 0 for g in tags)
    except struct.error:
        return True                                                    # malformed: flag it rather than miss it
    return False


def xmp_has_gps(x):
    return b'GPSLatitude' in x or b'GPSLongitude' in x


def jpeg_has_gps(d):
    i = 2
    while i + 4 <= len(d) and d[i] == 0xFF:
        m, n = d[i + 1], int.from_bytes(d[i + 2:i + 4], 'big')
        body = d[i + 4:i + 2 + n]
        if m == 0xE1 and body[:6] == b'Exif\0\0' and tiff_has_gps(body[6:]):
            return True
        if m == 0xE1 and xmp_has_gps(body):
            return True
        if m == 0xDA:
            break
        i += 2 + n
    return False


def png_has_gps(d):
    i = 8
    while i + 8 <= len(d):
        n, typ = struct.unpack('>I4s', d[i:i + 8])
        body = d[i + 8:i + 8 + n]
        if typ == b'eXIf' and tiff_has_gps(body):
            return True
        if typ in (b'iTXt', b'tEXt', b'zTXt') and xmp_has_gps(body):
            return True
        i += 12 + n
    return False


def has_gps(d):
    if d[:2] == b'\xff\xd8':
        return jpeg_has_gps(d)
    if d[:8] == b'\x89PNG\r\n\x1a\n':
        return png_has_gps(d)
    return False


def staged_images():
    out = subprocess.run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'],
                         capture_output=True, check=True).stdout.decode()
    for p in filter(None, out.split('\0')):
        if p.lower().endswith(IMAGE_EXT):
            yield p, subprocess.run(['git', 'show', ':' + p], capture_output=True, check=True).stdout


def main(args):
    if args == ['--staged']:
        files = staged_images()
    else:
        files = ((p, open(p, 'rb').read()) for p in args)
    bad = [p for p, d in files if has_gps(d)]
    for p in bad:
        print('GPS location data found:', p)
    if bad and args == ['--staged']:
        print('\nCommit blocked. Strip it with:  python scripts/strip_metadata.py <file> ...  then git add it again.'
              '\n(To commit anyway: git commit --no-verify)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
