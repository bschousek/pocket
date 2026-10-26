#!/usr/bin/env python3
"""Losslessly strip metadata (EXIF incl. GPS, XMP, IPTC, comments) from JPEGs, in place.

The image data is copied as-is, not re-encoded, so pixels are unchanged. Keeps the JFIF header
and ICC colour profile; drops other APPn segments and anything after the end of the image
(Samsung/MPF trailers, embedded previews). Warns if a photo relied on an EXIF rotation tag.

Usage:  python strip_metadata.py photo.jpg ...
Standard library only.
"""
import sys


def orientation(d):
    """EXIF orientation value (1 = upright) or None."""
    i = 2
    while i + 4 <= len(d) and d[i] == 0xFF:
        m, n = d[i + 1], int.from_bytes(d[i + 2:i + 4], 'big')
        body = d[i + 4:i + 2 + n]
        if m == 0xE1 and body[:6] == b'Exif\0\0':
            t = body[6:]
            bo = 'little' if t[:2] == b'II' else 'big'
            ifd = int.from_bytes(t[4:8], bo)
            for k in range(int.from_bytes(t[ifd:ifd + 2], bo)):
                e = t[ifd + 2 + 12 * k: ifd + 14 + 12 * k]
                if int.from_bytes(e[:2], bo) == 0x0112:
                    return int.from_bytes(e[8:10], bo)
        if m == 0xDA:
            break
        i += 2 + n
    return None


def strip(d):
    if d[:2] != b'\xff\xd8':
        raise ValueError('not a JPEG')
    out, i = bytearray(b'\xff\xd8'), 2
    while True:
        m, n = d[i + 1], int.from_bytes(d[i + 2:i + 4], 'big')
        seg = d[i:i + 2 + n]
        icc = m == 0xE2 and seg[4:16] == b'ICC_PROFILE\0'
        if not (0xE1 <= m <= 0xEF or m == 0xFE) or icc:
            out += seg
        i += 2 + n
        if m == 0xDA:                                  # start of scan: entropy-coded data follows
            break
    j = i
    while True:                                        # real EOI: skip stuffed FF00, RSTn and fill bytes
        j = d.index(b'\xff', j)
        if d[j + 1] == 0xD9:
            break
        j += 1 if d[j + 1] == 0xFF else 2
    out += d[i:j + 2]
    return bytes(out)


if __name__ == '__main__':
    for f in sys.argv[1:]:
        d = open(f, 'rb').read()
        o = orientation(d)
        s = strip(d)
        open(f, 'wb').write(s)
        print('%s: %d -> %d bytes' % (f, len(d), len(s)))
        if o not in (None, 1):
            print('  warning: EXIF orientation was %d; the image may now display rotated' % o)
