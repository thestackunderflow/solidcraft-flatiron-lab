"""Footprints from OpenStreetMap corner points (PLAN rev 2.1 §6.3): corners (longitude, latitude) -> metres -> millimetres
at 1:1000, the hand count of the footprint area, clipping to the plate, slivers, the missing-height rule, and the SVG
drawing with and without a unit. Proven on hand-made shapes before any real map data."""
import math
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from city import footprints as F  # noqa: E402


def ll(points):
    return [{'lat': la, 'lon': lo} for la, lo in points]


def test_one_corner_to_metres_north_and_east():
    lat0, lon0 = 40.0, -74.0
    (x, y), = F.to_metres(ll([(40.001, -74.0)]), lat0, lon0)
    assert x == pytest.approx(0.0) and y == pytest.approx(110.574)
    (x, y), = F.to_metres(ll([(40.0, -73.999)]), lat0, lon0)
    assert x == pytest.approx(111.320 * math.cos(math.radians(40.0))) and y == pytest.approx(0.0)


def test_centre_ignores_the_repeated_closing_corner():
    g = ll([(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)])
    assert F.centre(g) == pytest.approx((1.0, 1.0))


def test_area_of_a_square_either_way_round_and_closed_or_open():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert F.area(sq) == pytest.approx(100.0)
    assert F.area(sq[::-1]) == pytest.approx(100.0)
    assert F.area(sq + [sq[0]]) == pytest.approx(100.0)


def test_area_of_a_triangle_is_half_its_box():
    assert F.area([(0, 0), (30, 0), (0, 60)]) == pytest.approx(900.0)


def test_grid_squares_count_agrees_with_the_area():
    """The video's picture: count the 1 m grid squares inside the outline (centres inside). Close to the area."""
    tri = [(0, 0), (30, 0), (0, 60)]
    assert abs(F.grid_squares(tri, 1.0) - F.area(tri)) / F.area(tri) < 0.02


def test_clip_keeps_a_shape_inside_the_plate():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert F.area(F.clip_rect(sq, -50, -50, 50, 50)) == pytest.approx(100.0)


def test_clip_cuts_a_shape_across_the_edge():
    sq = [(40, 0), (60, 0), (60, 10), (40, 10)]
    c = F.clip_rect(sq, -50, -50, 50, 50)
    assert F.area(c) == pytest.approx(100.0)
    assert max(x for x, _ in c) == pytest.approx(50.0)


def test_clip_drops_a_shape_outside():
    assert F.clip_rect([(60, 0), (70, 0), (70, 10)], -50, -50, 50, 50) == []


def test_strip_width_of_a_long_thin_strip():
    strip = [(0, 0), (100, 0), (100, 0.5), (0, 0.5)]
    assert F.strip_width(strip) == pytest.approx(0.5, rel=0.01)


def test_sliver_rule_is_point_eight_mm():
    assert F.is_sliver([(0, 0), (100, 0), (100, 0.5), (0, 0.5)]) is True
    assert F.is_sliver([(0, 0), (10, 0), (10, 10), (0, 10)]) is False


@pytest.mark.parametrize('tags,expect', [
    ({'height': '86'}, (86.0, 'height tag')),
    ({'height': '86 m', 'building:levels': '21'}, (86.0, 'height tag')),
    ({'height': '12.5'}, (12.5, 'height tag')),
    ({'building:levels': '5'}, (15.0, 'no height tag: 5 floors x 3 m')),
])
def test_height_rule(tags, expect):
    assert F.height_m(tags) == expect


def test_no_height_and_no_floors_gets_the_stated_default():
    h, rule = F.height_m({'building': 'yes'})
    assert h == F.DEFAULT_HEIGHT_M and 'no height tag' in rule


def test_height_tag_is_text_in_osm():
    """OSM stores "86" as text: the script turns it into a number (the video's Python beat)."""
    assert isinstance(F.height_m({'height': '86'})[0], float)


def test_svg_without_a_unit_has_no_width():
    s = F.svg_text([('b1', [(0, 0), (10, 0), (10, 20)])], 120, 90)
    assert 'viewBox="-60 -45 120 90"' in s
    assert 'width=' not in s and 'height=' not in s


def test_svg_with_millimetres_says_so():
    s = F.svg_text([('b1', [(0, 0), (10, 0), (10, 20)])], 120, 90, unit='mm')
    assert 'width="120mm"' in s and 'height="90mm"' in s


def test_svg_turns_north_into_screen_up():
    """SVG's y grows downward, so a point 20 m north is written as y = -20."""
    s = F.svg_text([('b1', [(0, 0), (10, 0), (10, 20)])], 120, 90)
    d = re.search(r' d="([^"]+)"', s).group(1)
    assert d == 'M 0.000 0.000 L 10.000 0.000 L 10.000 -20.000 Z'


def test_svg_one_path_per_building_with_its_id():
    s = F.svg_text([('w1', [(0, 0), (1, 0), (1, 1)]), ('w2', [(2, 2), (3, 2), (3, 3)])], 120, 90)
    assert s.count('<path ') == 2 and 'id="w1"' in s and 'id="w2"' in s


def test_svg_header_lines_fit_a_phone_card():
    """The video shows the drawing's first lines as they are in the file: each fits 44 columns."""
    for unit, n in ((None, 2), ('mm', 3)):
        head = F.svg_text([('b1', [(0, 0), (1, 0), (1, 1)])], 120, 90, unit=unit).splitlines()[:n]
        assert all(len(l) <= 44 for l in head), head
        assert head[-1].endswith('>') and not any(l.endswith('>') for l in head[:-1])


def test_corner_is_what_to_metres_uses_and_fits_a_card():
    """The video's Python card: one corner (longitude, latitude) in, millimetres at 1:1000 out, in six short rows."""
    import inspect
    assert F.corner(-73.999, 40.001, -74.0, 40.0) == pytest.approx(F.to_metres(ll([(40.001, -73.999)]), 40.0, -74.0)[0])
    src = inspect.getsource(F.corner).splitlines()
    assert len(src) <= 6 and all(len(l) <= 45 for l in src)
