#!/usr/bin/env python3
"""The icon of GPUCheck as the PNGs its Info.plist names (no asset catalog: actool is a Mac program): the first thing
every graphics program draws -- a triangle with a red, a green and a blue corner, the colours blended across it -- on
a dark blue to violet gradient, and over its lower right corner a green disc in a white ring with a white check mark.
SpringBoard rounds the corners itself.
usage: python3 -I mkicon.py APP_DIR"""
import math
import os
import struct
import sys
import zlib

TOP, BOTTOM = (0x0e, 0x14, 0x38), (0x3c, 0x1a, 0x62)
CORNERS = ((0.47, 0.13), (0.10, 0.78), (0.86, 0.72))       # top, bottom left, right (u right, v down)
COLOURS = ((0xff, 0x3b, 0x30), (0x34, 0xc7, 0x59), (0x0a, 0x84, 0xff))
SHADOW = 0.025                                              # how far below and right the triangle's shadow falls
BADGE = (0.765, 0.765, 0.150)                               # the check's disc: centre and radius
RING = 0.022
GREEN = (0x30, 0xd1, 0x58)
WHITE = (0xff, 0xff, 0xff)
CHECK = ((0.695, 0.770), (0.745, 0.822), (0.842, 0.712))   # the check mark's three points
STROKE = 0.024
SS = 4      # samples per pixel along each side


def mix(c, d, a):
    return tuple(x + (y - x) * a for x, y in zip(c, d))


def barycentric(u, v):
    (x1, y1), (x2, y2), (x3, y3) = CORNERS
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    a = ((y2 - y3) * (u - x3) + (x3 - x2) * (v - y3)) / d
    b = ((y3 - y1) * (u - x3) + (x1 - x3) * (v - y3)) / d
    return a, b, 1 - a - b


def segment(u, v, p, q):
    (px, py), (qx, qy) = p, q
    dx, dy = qx - px, qy - py
    t = max(0.0, min(1.0, ((u - px) * dx + (v - py) * dy) / (dx * dx + dy * dy)))
    return math.hypot(u - px - t * dx, v - py - t * dy)


def color(u, v, bg):
    c = bg
    # a soft shadow under the triangle, then the triangle: each corner's colour, blended by how near it is
    if min(barycentric(u - SHADOW, v - SHADOW)) >= 0:
        c = mix(c, (0, 0, 0), 0.35)
    w = barycentric(u, v)
    if min(w) >= 0:
        c = tuple(sum(wi * col[k] for wi, col in zip(w, COLOURS)) for k in range(3))
        c = mix(c, WHITE, 0.10 * max(0.0, 1 - 3 * min(w)))
    # the badge: a white ring, the green disc, the check mark
    bx, by, br = BADGE
    r = math.hypot(u - bx, v - by)
    if r < br + RING:
        c = WHITE
    if r < br:
        c = GREEN
        if min(segment(u, v, CHECK[0], CHECK[1]), segment(u, v, CHECK[1], CHECK[2])) < STROKE:
            c = WHITE
    return c


def png(size):
    rows = []
    for y in range(size):
        row = bytearray([0])
        bg = [a + (b - a) * y / (size - 1) for a, b in zip(TOP, BOTTOM)]
        for x in range(size):
            total = [0, 0, 0]
            for i in range(SS):
                for j in range(SS):
                    c = color((x + (i + 0.5) / SS) / size, (y + (j + 0.5) / SS) / size, bg)
                    total = [t + k for t, k in zip(total, c)]
            row += bytes(min(255, round(t / (SS * SS))) for t in total)
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for scale in (2, 3):
        with open(os.path.join(sys.argv[1], 'AppIcon60x60@%dx.png' % scale), 'wb') as f:
            f.write(png(60 * scale))


main()
