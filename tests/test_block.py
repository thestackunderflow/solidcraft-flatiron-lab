"""The block (PLAN rev 2.1 §6.3): every building within the 120 x 90 mm plate around the Flatiron (way 264768896) at
1:1000, clipped to the plate, slivers under 1 mm dropped, a missing height filled by the stated rule, and the command
files: the trap (a drawing with no unit) and the fix (the drawing says millimetres)."""
import json
import os
import sys

import pytest

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, LAB)
from city import footprints as F  # noqa: E402
from city import make_block as B  # noqa: E402


@pytest.fixture(scope='module')
def block():
    return B.build(json.load(open(os.path.join(LAB, 'data', 'overpass.json'), encoding='utf-8')))


def test_the_flatiron_is_in_the_middle_with_its_height_tag(block):
    f = block['focus']
    assert f['id'] == 264768896 and f['name'] == 'Flatiron Building'
    assert f['height_m'] == 86.0 and f['rule'] == 'height tag' and f['levels'] == '21'
    xs = [x for x, _ in f['mm']]
    ys = [y for _, y in f['mm']]
    assert abs((min(xs) + max(xs)) / 2) < 20 and abs((min(ys) + max(ys)) / 2) < 20


def test_hand_count_of_the_flatiron_footprint(block):
    """The area from OSM's corner points: about 1,000 square metres (= mm2 at 1:1000), and the grid-square count agrees."""
    f = block['focus']
    assert 990 < f['area_mm2'] < 1015
    assert abs(F.grid_squares(f['mm'], 0.5) - f['area_mm2']) / f['area_mm2'] < 0.01


def test_every_building_is_on_the_plate(block):
    hw, hh = B.PLATE_MM[0] / 2, B.PLATE_MM[1] / 2
    for b in block['buildings']:
        for x, y in b['mm']:
            assert -hw - 1e-6 <= x <= hw + 1e-6 and -hh - 1e-6 <= y <= hh + 1e-6


def test_no_sliver_survives_and_the_dropped_ones_are_listed(block):
    for b in block['buildings']:
        assert not F.is_sliver(b['mm'])
    for d in block['dropped']:
        assert d['why'] in ('off the plate', 'sliver under 1 mm', 'a roof (no walls)')


def test_a_missing_height_is_labelled_with_its_rule(block):
    rules = {b['rule'] for b in block['buildings']}
    assert 'height tag' in rules
    assert all(r == 'height tag' or r.startswith('no height tag') for r in rules)
    assert block['counts']['height_tag'] + block['counts']['rule'] == len(block['buildings'])


def test_fits_the_bed(block):
    assert B.PLATE_MM[0] <= 170 and B.PLATE_MM[1] <= 170
    assert B.BASE_MM + max(b['height_m'] for b in block['buildings']) <= 170


def test_trap_drawing_has_no_unit_and_the_fix_says_mm(block):
    px, mm = B.flatiron_svg(block, None), B.flatiron_svg(block, 'mm')
    assert 'width=' not in px and 'width="120mm"' in mm and 'height="90mm"' in mm


def test_trap_command_file(block):
    c = B.steps_flatiron(block, unit=None)['commands']
    ins = [x for x in c if x['command'] == 'sketch.insert_svg']
    assert len(ins) == 1 and 'width=' not in ins[0]['params']['text'] and 'at' not in ins[0]['params']
    ext = [x for x in c if x['command'] == 'solid.extrude'][0]
    assert ext['params']['distance'] == 86.0


def test_fix_command_file_puts_the_drawing_centre_at_the_origin(block):
    c = B.steps_flatiron(block, unit='mm')['commands']
    ins = [x for x in c if x['command'] == 'sketch.insert_svg'][0]
    assert 'width="120mm"' in ins['params']['text']
    assert ins['params']['at'] == [-60.0, 45.0]     # the drawing's top-left corner lands at (-60, 45): measured in the probe


def test_block_command_file_has_a_plate_and_one_extrude_per_building(block):
    c = B.steps_block(block)['commands']
    assert c[0]['command'] == 'solid.box' and c[0]['params']['body_name'] == 'Plate'
    ext = [x for x in c if x['command'] == 'solid.extrude']
    assert len(ext) == len(block['buildings'])
    assert all(e['params']['operation'] == 'join' for e in ext)
    sk = [x for x in c if x['command'] == 'sketch.create']
    assert all(s['params']['offset'] == B.BASE_MM for s in sk)


def test_hand_volume_of_the_block(block):
    v = sum(b['area_mm2'] * b['height_m'] for b in block['buildings']) + B.PLATE_MM[0] * B.PLATE_MM[1] * B.BASE_MM
    assert block['hand_volume_mm3'] == pytest.approx(v)
