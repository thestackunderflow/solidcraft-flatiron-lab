"""Buildings -> the block on a plate -> SolidCraft command files (PLAN rev 2.1 §6.3).

    python3 city/make_block.py        (after get_data.py; in the lab image)

Map scale 1:1000: 1 m in the city = 1 mm on the print. The plate is 120 x 90 mm around the Flatiron Building, 2 mm thick;
every building's footprint is clipped to the plate, slivers thinner than 0.8 mm are dropped, and each building stands on
the plate at its height (OSM's height tag; with none, its floors x 3 m; with neither, one floor, 3 m: labelled in the video).
Writes:
  data/block.json            every building kept (corners in mm, height and its rule, area) + what was dropped and why
  data/flatiron.svg          the Flatiron drawn as a plain script would: numbers, no unit (the trap)
  data/flatiron-mm.svg       the same drawing saying its size in millimetres (the fix)
  data/block-mm.svg          every building, in millimetres
  steps/flatiron-px.json     import the no-unit drawing, extrude 86: comes in a quarter as wide
  steps/flatiron-mm.json     import the millimetre drawing, extrude 86: the right size
  steps/block-mm.json        the plate + every building, joined into one body
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, LAB)
from city import footprints as F  # noqa: E402
from city.get_data import FOCUS_WAY  # noqa: E402

PLATE_MM = (120.0, 90.0)
BASE_MM = 2.0
MM_PER_M = 1.0                     # 1:1000
AT_MM = [-PLATE_MM[0] / 2, PLATE_MM[1] / 2]   # SolidCraft puts the drawing's top-left corner at `at` (probe: measured)


def build(overpass):
    ways = [e for e in overpass['elements'] if e['type'] == 'way' and e.get('geometry')]
    focus = next(e for e in ways if e['id'] == FOCUS_WAY)
    lat0, lon0 = F.centre(focus['geometry'])
    hw, hh = PLATE_MM[0] / 2, PLATE_MM[1] / 2
    kept, dropped = [], []
    for w in sorted(ways, key=lambda e: e['id']):
        tags = w.get('tags', {})
        if 'building' not in tags:
            continue
        if tags.get('building') == 'roof':
            dropped.append({'id': w['id'], 'why': 'a roof (no walls)'})
            continue
        mm = [(x * MM_PER_M, y * MM_PER_M) for x, y in F.to_metres(w['geometry'], lat0, lon0)]
        cut = F.clip_rect(mm, -hw, -hh, hw, hh)
        if not cut:
            dropped.append({'id': w['id'], 'why': 'off the plate'})
            continue
        if F.is_sliver(cut):
            dropped.append({'id': w['id'], 'why': 'sliver under 0.8 mm', 'width_mm': round(F.strip_width(cut), 3)})
            continue
        h, rule = F.height_m(tags)
        kept.append({'id': w['id'], 'name': tags.get('name'), 'height_tag': tags.get('height'),
                     'levels': tags.get('building:levels'), 'height_m': h, 'rule': rule,
                     'clipped': len(cut) != len(F._open(mm)) or F.area(cut) < F.area(mm) - 1e-6,
                     'area_mm2': F.area(cut), 'mm': [(round(x, 4), round(y, 4)) for x, y in cut]})
    f = next(b for b in kept if b['id'] == FOCUS_WAY)
    return {'focus': f, 'buildings': kept, 'dropped': dropped, 'centre_lat_lon': [lat0, lon0],
            'plate_mm': list(PLATE_MM), 'base_mm': BASE_MM, 'scale': '1:1000',
            'counts': {'kept': len(kept), 'height_tag': sum(1 for b in kept if b['rule'] == 'height tag'),
                       'rule': sum(1 for b in kept if b['rule'] != 'height tag'), 'dropped': len(dropped)},
            'hand_volume_mm3': sum(b['area_mm2'] * b['height_m'] for b in kept) + PLATE_MM[0] * PLATE_MM[1] * BASE_MM}


def flatiron_svg(block, unit):
    return F.svg_text([(f"w{block['focus']['id']}", block['focus']['mm'])], *PLATE_MM, unit=unit)


def _one(name, svg, unit, height, offset=0.0, op='new'):
    p = {'text': svg}
    if unit:
        p['at'] = list(AT_MM)
    sk = {'plane': 'XY', 'name': name + 'Sketch'}
    if offset:
        sk['offset'] = offset
    ext = {'sketch': name + 'Sketch', 'distance': height, 'operation': op}
    if op == 'new':
        ext['body_name'] = name
    return [{'command': 'sketch.create', 'params': sk}, {'command': 'sketch.insert_svg', 'params': p},
            {'command': 'sketch.finish', 'params': {}}, {'command': 'solid.extrude', 'params': ext}]


def steps_flatiron(block, unit):
    return {'commands': _one('Flatiron', flatiron_svg(block, unit), unit, block['focus']['height_m'])}


def steps_block(block):
    c = [{'command': 'solid.box', 'params': {'corner': [-PLATE_MM[0] / 2, -PLATE_MM[1] / 2, 0], 'length': PLATE_MM[0],
                                             'width': PLATE_MM[1], 'height': BASE_MM, 'body_name': 'Plate'}}]
    for b in block['buildings']:
        svg = F.svg_text([(f"w{b['id']}", b['mm'])], *PLATE_MM, unit='mm')
        c += _one(f"W{b['id']}", svg, 'mm', b['height_m'], offset=BASE_MM, op='join')
    return {'commands': c}


def write(rel, text):
    with open(os.path.join(LAB, rel), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def main():
    block = build(json.load(open(os.path.join(LAB, 'data', 'overpass.json'), encoding='utf-8')))
    write('data/block.json', json.dumps(block, indent=1) + '\n')
    write('data/flatiron.svg', flatiron_svg(block, None))
    write('data/flatiron-mm.svg', flatiron_svg(block, 'mm'))
    write('data/block-mm.svg', F.svg_text([(f"w{b['id']}", b['mm']) for b in block['buildings']], *PLATE_MM, unit='mm'))
    os.makedirs(os.path.join(LAB, 'steps'), exist_ok=True)
    write('steps/flatiron-px.json', json.dumps(steps_flatiron(block, None)) + '\n')
    write('steps/flatiron-mm.json', json.dumps(steps_flatiron(block, 'mm')) + '\n')
    write('steps/block-mm.json', json.dumps(steps_block(block)) + '\n')
    print(json.dumps({k: block[k] for k in ('counts', 'dropped', 'hand_volume_mm3')}, indent=1))
    print('flatiron area mm2', round(block['focus']['area_mm2'], 1))


if __name__ == '__main__':
    main()
