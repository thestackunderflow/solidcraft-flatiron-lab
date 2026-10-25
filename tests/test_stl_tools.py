"""The lab's own STL checks (numpy only), proven on synthetic meshes before they touch a SolidCraft export."""
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stl_tools import bodies, box_tris, read_stl, watertight, write_stl, x_intervals, z_gaps  # noqa: E402


def tmp(tris, binary=True):
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'm.stl')
    write_stl(p, tris, binary=binary)
    return p


def test_round_trip_binary_and_ascii():
    t = box_tris((0, 0, 0), (10, 20, 30))
    for binary in (True, False):
        r = read_stl(tmp(t, binary))
        assert r.shape == (12, 3, 3)
        assert np.allclose(np.sort(r.reshape(-1, 3), axis=0), np.sort(t.reshape(-1, 3), axis=0))


def test_one_box_is_watertight_and_one_body():
    t = read_stl(tmp(box_tris((0, 0, 0), (10, 20, 30))))
    assert watertight(t) is True
    assert bodies(t) == 1


def test_two_separate_boxes_are_two_bodies():
    t = np.concatenate([box_tris((0, 0, 0), (1, 1, 1)), box_tris((5, 0, 0), (6, 1, 1))])
    assert bodies(read_stl(tmp(t))) == 2


def test_a_missing_face_is_not_watertight():
    t = box_tris((0, 0, 0), (1, 1, 1))[:-2]
    assert watertight(t) is False


def test_x_intervals_of_a_square_ring():
    # a ring: outer 10 x 10, inner 6 x 6, 4 tall, as four boxes that share faces
    t = np.concatenate([box_tris((-5, -5, 0), (5, -3, 4)), box_tris((-5, 3, 0), (5, 5, 4)),
                        box_tris((-5, -3, 0), (-3, 3, 4)), box_tris((3, -3, 0), (5, 3, 4))])
    iv = x_intervals(t, z=2.0, y=0.0)
    assert [tuple(round(v, 6) for v in i) for i in iv] == [(-5.0, -3.0), (3.0, 5.0)]
    assert x_intervals(t, z=9.0, y=0.0) == []


def test_z_gaps_between_two_stacked_boxes():
    t = np.concatenate([box_tris((0, -1, 0), (1, 1, 2)), box_tris((0, -1, 2.2), (1, 1, 3))])
    assert [tuple(round(v, 6) for v in g) for g in z_gaps(t, x=0.5, y=0.0)] == [(2.0, 2.2)]


@pytest.mark.parametrize('n', [0, 1])
def test_bodies_of_empty_or_single_triangle(n):
    t = box_tris((0, 0, 0), (1, 1, 1))[:n]
    assert bodies(t) == n


# --- flatiron lab additions: volume (the second measurement of the footprint) and the north check ---------------------
from stl_tools import poly_segments, prism_tris, prow, section_segments, volume  # noqa: E402


def test_volume_of_a_box():
    assert volume(box_tris((0, 0, 0), (10, 20, 30))) == pytest.approx(6000.0)


def test_volume_of_a_triangular_prism_is_area_times_height():
    t = prism_tris([(0, 0), (30, 0), (0, 60)], 0, 86)
    assert volume(t) == pytest.approx(900.0 * 86)
    assert watertight(t) and bodies(t) == 1


def rot(poly, deg):
    import math
    a = math.radians(-deg)        # a compass bearing turns clockwise
    return [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)) for x, y in poly]


WEDGE = [(-15, 0), (15, 0), (1, 60), (-1, 60)]      # the Flatiron's shape, simplified: narrow end north


def test_prow_of_a_wedge_pointing_north():
    p = prow(poly_segments(WEDGE))
    assert p['bearing_deg'] == pytest.approx(0.0, abs=1.0) and p['narrow_end'] == 'north'
    assert p['narrow_width'] < p['wide_width']


def test_prow_of_a_turned_wedge():
    p = prow(poly_segments(rot(WEDGE, 30)))
    assert p['bearing_deg'] == pytest.approx(30.0, abs=1.0)


def test_prow_of_the_mirror_image_points_south():
    p = prow(poly_segments([(x, -y) for x, y in rot(WEDGE, 20)]))
    assert p['bearing_deg'] == pytest.approx(160.0, abs=1.0) and p['narrow_end'] == 'south'


def test_prow_from_an_stl_section_matches_the_outline():
    t = prism_tris(rot(WEDGE, 30), 0, 10)
    assert prow(section_segments(t, 5.0))['bearing_deg'] == pytest.approx(30.0, abs=1.0)
