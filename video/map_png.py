"""Our drawings of the OpenStreetMap data for the video (not a map tile; words go on later in video/make_hook.sh):

    python3 video/map_png.py

  data-map.png      the 120 x 90 m plate, north up, on graph paper (a line every 10 m), every building kept (the
                    Flatiron darker): the data picture of chapter 1
  grid-count.png    the Flatiron's corners on 1 m graph paper, the squares whose centre is inside filled: the hand count
  north-map.png     the Flatiron from OSM's corners, north up, an arrow from its middle to its narrow end
  north-model.png   the same from a section through the fixed model's STL (out/probe/0.19.0/mm/model.stl)
  north-mirror.png  the same from the model drawn WITHOUT turning north to screen-up (out/probe/0.19.0/north/model.stl)
Writes out/evidence/grid-count.json (the square count) for the panels.
"""
import json
import math
import os
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, LAB)
sys.path.insert(0, os.path.join(LAB, 'tests'))
from city import footprints as F  # noqa: E402
from stl_tools import poly_segments, prow, read_stl, section_segments  # noqa: E402

PAPER, GRID, GRID10, EDGE = (255, 255, 255), (226, 232, 240), (176, 190, 210), (71, 85, 105)
STONE, STONE_DARK, INK, GREEN, RED = (214, 210, 186), (170, 160, 120), (31, 41, 55), (27, 94, 32), (183, 28, 28)
FILL = (190, 214, 238)


def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].tobytes() for i in range(h))

    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


class Canvas:
    """A picture of the plane: (x, y) in metres (or mm), north up, `ppm` pixels per unit, centred on (cx, cy)."""

    def __init__(self, w, h, ppm, cx=0.0, cy=0.0):
        self.img = np.full((h, w, 3), PAPER, dtype=np.uint8)
        self.w, self.h, self.ppm, self.cx, self.cy = w, h, ppm, cx, cy
        jj, ii = np.meshgrid(np.arange(w), np.arange(h))
        self.X = cx + (jj + 0.5 - w / 2) / ppm
        self.Y = cy - (ii + 0.5 - h / 2) / ppm

    def px(self, x, y):
        return (self.w / 2 + (x - self.cx) * self.ppm, self.h / 2 - (y - self.cy) * self.ppm)

    def grid(self, step, colour, width=1):
        for k in range(math.floor((self.cx - self.w / 2 / self.ppm) / step), math.ceil((self.cx + self.w / 2 / self.ppm) / step) + 1):
            j = int(round(self.px(k * step, 0)[0]))
            self.img[:, max(j - width // 2, 0):max(j - width // 2, 0) + width] = colour
        for k in range(math.floor((self.cy - self.h / 2 / self.ppm) / step), math.ceil((self.cy + self.h / 2 / self.ppm) / step) + 1):
            i = int(round(self.px(0, k * step)[1]))
            if 0 <= i < self.h:
                self.img[max(i - width // 2, 0):max(i - width // 2, 0) + width, :] = colour

    def mask(self, poly):
        p = F._open(poly)
        inside = np.zeros(self.X.shape, dtype=bool)
        for k in range(len(p)):
            (x1, y1), (x2, y2) = p[k], p[(k + 1) % len(p)]
            if y1 == y2:
                continue
            cross = ((y1 > self.Y) != (y2 > self.Y)) & (self.X < x1 + (self.Y - y1) * (x2 - x1) / (y2 - y1))
            inside ^= cross
        return inside

    def fill(self, poly, colour):
        self.img[self.mask(poly)] = colour

    def line(self, a, b, colour, width=3):
        (x0, y0), (x1, y1) = self.px(*a), self.px(*b)
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for t in np.linspace(0, 1, n):
            x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            i0, j0 = int(y - width / 2), int(x - width / 2)
            self.img[max(i0, 0):max(i0 + width, 0), max(j0, 0):max(j0 + width, 0)] = colour

    def outline(self, poly, colour, width=3):
        p = F._open(poly)
        for k in range(len(p)):
            self.line(p[k], p[(k + 1) % len(p)], colour, width)

    def arrow(self, a, bearing, length, colour, width=6):
        d = (math.sin(math.radians(bearing)), math.cos(math.radians(bearing)))
        b = (a[0] + d[0] * length, a[1] + d[1] * length)
        self.line(a, b, colour, width)
        for side in (150, -150):
            r = math.radians(bearing + side)
            self.line(b, (b[0] + math.sin(r) * length * 0.3, b[1] + math.cos(r) * length * 0.3), colour, width)


def seg_poly(segs):
    """Order a section's segments into one closed outline (they share endpoints)."""
    segs = [(tuple(np.round(a, 6)), tuple(np.round(b, 6))) for a, b in segs]
    out = [segs[0][0], segs[0][1]]
    rest = segs[1:]
    while rest:
        last = out[-1]
        k = min(range(len(rest)), key=lambda i: min(math.dist(rest[i][0], last), math.dist(rest[i][1], last)))
        a, b = rest.pop(k)
        out.append(b if math.dist(a, last) <= math.dist(b, last) else a)
    return out[:-1]


def north_picture(poly, name, colour):
    c = Canvas(900, 900, 12.0, *np.mean(np.array(F._open(poly)), axis=0))
    c.grid(10, GRID10, 1)
    c.fill(poly, STONE)
    c.outline(poly, EDGE, 3)
    p = prow(poly_segments(poly))
    mid = tuple(np.mean(np.array(F._open(poly)), axis=0))
    c.arrow(mid, p['bearing_deg'], 26, colour, 8)
    write_png(os.path.join(HERE, 'frames', name), c.img)
    return p


def main():
    block = json.load(open(os.path.join(LAB, 'data', 'block.json'), encoding='utf-8'))
    os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)
    # 1. the data picture: the plate, north up, graph paper every 10 m
    c = Canvas(1200, 900, 10.0)
    c.grid(2, (241, 245, 249), 1)
    c.grid(10, GRID10, 2)
    for b in block['buildings']:
        c.fill(b['mm'], STONE_DARK if b['id'] == block['focus']['id'] else STONE)
        c.outline(b['mm'], EDGE, 2)
    c.img[:3, :], c.img[-3:, :], c.img[:, :3], c.img[:, -3:] = EDGE, EDGE, EDGE, EDGE
    write_png(os.path.join(HERE, 'frames', 'data-map.png'), c.img)
    # 2. the hand count: 1 m graph paper, squares whose centre is inside
    f = block['focus']['mm']
    xs, ys = [x for x, _ in f], [y for _, y in f]
    c = Canvas(1080, 1440, 22.0, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    cells = (np.floor(c.X) + 0.5, np.floor(c.Y) + 0.5)
    sub = Canvas(1, 1, 1.0)
    sub.X, sub.Y = cells
    c.img[sub.mask(f)] = FILL
    c.grid(1, GRID, 1)
    c.grid(10, GRID10, 2)
    c.outline(f, INK, 4)
    write_png(os.path.join(HERE, 'frames', 'grid-count.png'), c.img)
    n = F.grid_squares(f, 1.0)
    os.makedirs(os.path.join(LAB, 'out', 'evidence'), exist_ok=True)
    with open(os.path.join(LAB, 'out', 'evidence', 'grid-count.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump({'squares_1m': int(round(n)), 'shoelace_m2': round(block['focus']['area_mm2'], 2)}, fh, indent=1)
        fh.write('\n')
    # 3. the north check: the map, the fixed model, the model drawn without turning north to screen-up
    out = {'map': north_picture(f, 'north-map.png', GREEN)}
    for cell, name, col in (('mm', 'north-model.png', GREEN), ('north', 'north-mirror.png', RED)):
        t = read_stl(os.path.join(LAB, 'out', 'probe', '0.19.0', cell, 'model.stl'))
        out[cell] = north_picture(seg_poly(section_segments(t, 43.0)), name, col)
    print(json.dumps({'squares_1m': n, **{k: v['bearing_deg'] for k, v in out.items()}}))


if __name__ == '__main__':
    main()
