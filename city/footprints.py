"""OpenStreetMap footprints -> millimetres at 1:1000 (1 m in the city = 1 mm on the print).

Corners come as (longitude, latitude). Near one place the Earth is flat enough to treat a degree as a fixed number of
metres ("about", a sphere): 110,574 m per degree north, 111,320 x cos(latitude) per degree east. Then the footprint is a
flat outline, its area is a hand count (grid squares, or the shoelace sum the tests check it with), and the SVG drawing
says its size in millimetres or, as the trap, says nothing at all.
"""
import math

M_PER_DEG_N = 110574.0
M_PER_DEG_E_EQ = 111320.0
FLOOR_M = 3.0             # the stated rule for a building with no height tag: its floors x 3 m
DEFAULT_HEIGHT_M = 3.0    # ... and with no floors either: one floor, 3 m (shown as a label in the video)
SLIVER_MM = 1.0           # thinner than this does not print well: the plan said 0.8, but PrusaSlicer gave a 0.84 mm
                          # piece (a corner clipped off at the plate's edge) one line, so 1 mm (out/slice/thin-*.json)


def _open(poly):
    pts = [tuple(p) for p in poly]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def centre(geom):
    """Mean of the corners (the closing corner, which repeats the first, counted once): (lat, lon)."""
    pts = _open([(p['lat'], p['lon']) for p in geom])
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def east_m(lat0):
    """Metres per degree east at latitude lat0 (about: a sphere)."""
    return M_PER_DEG_E_EQ * math.cos(math.radians(lat0))


def corner(lon, lat, lon0, lat0):
    # one corner in: longitude, latitude
    east = (lon - lon0) * east_m(lat0)
    north = (lat - lat0) * M_PER_DEG_N
    # metres in the city = mm at 1:1000
    return east, north


def to_metres(geom, lat0, lon0):
    """Every corner -> metres east and north of (lat0, lon0)."""
    return [corner(p['lon'], p['lat'], lon0, lat0) for p in geom]


def area(poly):
    """The footprint's area: the shoelace sum over the corners (either way round)."""
    p = _open(poly)
    s = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
    return abs(s) / 2.0


def perimeter(poly):
    p = _open(poly)
    return sum(math.dist(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))


def inside(pt, poly):
    x, y = pt
    p, c = _open(poly), False
    for i in range(len(p)):
        (x1, y1), (x2, y2) = p[i], p[(i + 1) % len(p)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def grid_squares(poly, cell=1.0):
    """The video's hand count: lay graph paper over the outline and count the squares whose centre is inside."""
    p = _open(poly)
    x0, x1 = math.floor(min(x for x, _ in p)), math.ceil(max(x for x, _ in p))
    y0, y1 = math.floor(min(y for _, y in p)), math.ceil(max(y for _, y in p))
    n = 0
    for i in range(int((x1 - x0) / cell)):
        for j in range(int((y1 - y0) / cell)):
            if inside((x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell), p):
                n += 1
    return n * cell * cell


def clip_rect(poly, x0, y0, x1, y1):
    """The part of the outline on the plate (Sutherland-Hodgman against the plate's four edges); [] if none."""
    out = _open(poly)
    for keep, cut in ((lambda q: q[0] >= x0, lambda a, b: _at_x(a, b, x0)),
                      (lambda q: q[0] <= x1, lambda a, b: _at_x(a, b, x1)),
                      (lambda q: q[1] >= y0, lambda a, b: _at_y(a, b, y0)),
                      (lambda q: q[1] <= y1, lambda a, b: _at_y(a, b, y1))):
        src, out = out, []
        for i in range(len(src)):
            a, b = src[i - 1], src[i]
            if keep(b):
                if not keep(a):
                    out.append(cut(a, b))
                out.append(b)
            elif keep(a):
                out.append(cut(a, b))
        if not out:
            return []
    dedup = []
    for q in out:
        if not dedup or math.dist(q, dedup[-1]) > 1e-9:
            dedup.append(q)
    if len(dedup) > 1 and math.dist(dedup[0], dedup[-1]) <= 1e-9:
        dedup.pop()
    return dedup if len(dedup) >= 3 and area(dedup) > 1e-9 else []


def _at_x(a, b, x):
    t = (x - a[0]) / (b[0] - a[0])
    return (x, a[1] + t * (b[1] - a[1]))


def _at_y(a, b, y):
    t = (y - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), y)


def strip_width(poly):
    """How wide a thin strip is: 2 x area / perimeter (exact for a long strip; half the side for a square)."""
    return 2.0 * area(poly) / perimeter(poly)


def is_sliver(poly_mm):
    return strip_width(poly_mm) < SLIVER_MM


def _num(text):
    t = text.strip().lower().replace(',', '.')
    for suffix in (' m', 'm'):
        if t.endswith(suffix):
            t = t[: -len(suffix)].strip()
    return float(t)


def height_m(tags):
    """(metres, which rule): OSM's height tag (text, e.g. "86") when there is one; else floors x 3 m; else one floor, 3 m."""
    if 'height' in tags:
        try:
            return _num(tags['height']), 'height tag'
        except ValueError:
            pass
    if 'building:levels' in tags:
        try:
            n = float(tags['building:levels'])
            return n * FLOOR_M, f'no height tag: {n:g} floors x {FLOOR_M:g} m'
        except ValueError:
            pass
    return DEFAULT_HEIGHT_M, f'no height tag, no floors: one floor, {DEFAULT_HEIGHT_M:g} m'


def svg_text(paths, w, h, unit=None):
    """An SVG drawing of outlines in metres, centred on (0, 0), north up. SVG's y grows downward, so north is written
    as -y. With unit='mm' the drawing says how big it is (width="120mm"): one drawing unit = one millimetre. Without a
    unit, the numbers are just numbers, and an SVG reader takes them as screen pixels."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg"']          # one attribute group per line: a 44-column card shows them
    if unit:
        out.append(f'  width="{w:g}{unit}" height="{h:g}{unit}"')
    out.append(f'  viewBox="{-w / 2:g} {-h / 2:g} {w:g} {h:g}">')
    for pid, poly in paths:
        p = _open(poly)
        d = 'M ' + ' L '.join(f'{x:.3f} {-y + 0.0:.3f}' for x, y in p) + ' Z'
        out.append(f'<path id="{pid}" d="{d}"/>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'
