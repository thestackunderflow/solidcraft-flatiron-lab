"""Panel text and card specs for the Flatiron video, from out/ and data/ only (no number typed by hand).

    python3 video/make_panels.py

Writes out/evidence/numbers.json, video/terminal-*.txt (<= 7 rows x 44 cols), video/toolcalls.json (the transcript row
each tool-call panel cites + the result substring + plain words), video/json-cards.json and video/python-cards.json.
tests/test_evidence.py re-derives the values. The agent-run rows appear once out/runs/SCORES.json exists.
"""
import json
import os
import re

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(LAB, *a)  # noqa: E731
PROBE = 'out/probe/0.19.0'


def jload(*a):
    with open(P(*a), encoding='utf-8') as f:
        return json.load(f)


def write(rel, text):
    os.makedirs(os.path.dirname(P(rel)), exist_ok=True)
    with open(P(rel), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if text.endswith('\n') else text + '\n')


def rows(rel):
    with open(P(rel), encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def call_row(rel, pred):
    for i, r in enumerate(rows(rel), 1):
        m = r.get('msg') or {}
        if r.get('dir') == 'client->server' and m.get('method') == 'tools/call' and pred(m['params']):
            return r['seq'], i, r
    raise LookupError(rel)


def reply_text(rel, seq):
    rs = rows(rel)
    call = next(r for r in rs if r['seq'] == seq)
    for r in rs[rs.index(call) + 1:]:
        m = r.get('msg') or {}
        if r['dir'] == 'server->client' and m.get('id') == call['msg']['id']:
            return ''.join(c.get('text', '') for c in m['result']['content'] if c.get('type') == 'text')
    raise LookupError(seq)


def line_no(rel, needle, after=0):
    with open(P(rel), encoding='utf-8') as f:
        for i, l in enumerate(f, 1):
            if i > after and needle in l:
                return i
    raise LookupError(needle)


def numbers():
    block = jload('data', 'block.json')
    c = {k: jload(PROBE, k, 'summary.json') for k in ('px', 'mm', 'north', 'block')}
    v22 = jload('out', 'probe', '0.22.0', 'px', 'summary.json')
    sl = jload('out', 'slice', 'slice-report.json')
    grid = jload('out', 'evidence', 'grid-count.json')
    f = block['focus']
    n = {
        'px_w': f"{c['px']['size_mm'][0]:.1f}", 'px_d': f"{c['px']['size_mm'][1]:.1f}", 'px_h': f"{c['px']['size_mm'][2]:.1f}",
        'hand_w': f"{c['px']['hand_size_mm'][0]:.1f}", 'hand_d': f"{c['px']['hand_size_mm'][1]:.1f}",
        'width_ratio': f"{c['px']['width_vs_hand']:.2f}", 'times_narrower': f"{1 / c['px']['width_vs_hand']:.1f}",
        'px_area': f"{c['px']['footprint_mm2']['measure']:,.1f}", 'px_volume': f"{c['px']['volume_mm3']:,.0f}",
        'px_volume_pct': f"{100 * c['px']['footprint_vs_hand']:.1f}",
        'hand_area': f"{f['area_mm2']:,.1f}", 'squares': f"{grid['squares_1m']:,}",
        'mm_w': f"{c['mm']['size_mm'][0]:.1f}", 'mm_d': f"{c['mm']['size_mm'][1]:.1f}", 'mm_h': f"{c['mm']['size_mm'][2]:.1f}",
        'mm_area': f"{c['mm']['footprint_mm2']['measure']:,.1f}", 'mm_area_stl': f"{c['mm']['footprint_mm2']['stl']:,.1f}",
        'mm_volume': f"{c['mm']['volume_mm3']:,.0f}", 'height_tag': f['height_tag'], 'levels': f['levels'],
        'map_bearing': f"{c['mm']['north_check']['map']['bearing_deg']:.1f}",
        'mm_bearing': f"{c['mm']['north_check']['model']['bearing_deg']:.1f}",
        'mirror_bearing': f"{c['north']['north_check']['model']['bearing_deg']:.1f}",
        'buildings': str(block['counts']['kept']), 'tagged': str(block['counts']['height_tag']),
        'by_rule': str(block['counts']['rule']), 'dropped': str(block['counts']['dropped']),
        'rule_names': [b['rule'] for b in block['buildings'] if b['rule'] != 'height tag'],
        'block_size': 'x'.join(f"{v:g}" for v in c['block']['size_mm']), 'block_bodies': str(c['block']['stl']['bodies']),
        'block_watertight': c['block']['stl']['watertight'], 'block_volume': f"{c['block']['volume_mm3']:,.0f}",
        'block_hand': f"{block['hand_volume_mm3']:,.0f}", 'block_pct': f"{abs(c['block']['volume_vs_hand_pct']):.2f}",
        'tallest_m': f"{max(b['height_m'] for b in block['buildings']):g}",
        'slice_time': sl['gcode']['print_time'], 'slice_g': f"{sl['gcode']['filament_g']:.0f}",
        'v22_px_w': f"{v22['size_mm'][0]:.1f}",
    }
    if os.path.exists(P('out', 'runs', 'SCORES.json')):
        runs = jload('out', 'runs', 'SCORES.json')['runs']
        ok = [r for r in runs if r['measured']]
        n.update({'runs': str(len(runs)), 'runs_total_usd': f"{sum(r['cost_usd'] or 0 for r in runs):.2f}",
                  'runs_right_size': str(sum(1 for r in ok if r['measured']['right_size'])),
                  'runs_height': str(sum(1 for r in ok if r['measured']['height_ok'])),
                  'runs_north': str(sum(1 for r in ok if r['measured']['north_ok'])),
                  'runs_fixes': sorted({r['fix'] for r in runs})})
    return n


def main():
    n = numbers()
    write('out/evidence/numbers.json', json.dumps(n, indent=1))
    write('video/terminal-size.txt', '\n'.join([
        'imported drawing, no unit:',
        f"  {n['px_w']} x {n['px_d']} mm, {n['px_h']} tall",
        "OSM's corners at 1 : 1000:",
        f"  {n['hand_w']} x {n['hand_d']} mm",
        f"{n['width_ratio']} as wide: about a quarter",
    ]))
    write('video/terminal-proof.txt', '\n'.join([
        'fresh build · the drawing says mm',
        f"footprint {n['mm_area']} mm2 (volume / {n['mm_h'][:-2]})",
        f"hand count {n['hand_area']} mm2",
        f"height {n['mm_h']} mm · OSM's tag \"{n['height_tag']}\"",
        f"narrow end points {n['mm_bearing']}°",
        f"the map's narrow end: {n['map_bearing']}°",
    ]))
    write('video/terminal-north.txt', '\n'.join([
        f"the map's narrow end: {n['map_bearing']}°",
        f"our model: {n['mm_bearing']}°",
        f"north left as screen-down: {n['mirror_bearing']}°",
    ]))
    write('video/terminal-block.txt', '\n'.join([
        f"{n['buildings']} buildings on a 120 x 90 mm plate",
        f"{n['tagged']} with a height tag, {n['by_rule']} by our rule",
        f"1 body, watertight, {n['block_size'].split('x')[2]} mm tall",
        f"volume {n['block_volume']} mm3",
        f"hand count {n['block_hand']} mm3",
    ]))
    write('video/terminal-slicer.txt', '\n'.join([
        'PrusaSlicer 2.9.2 · MK4S 0.4 · PLA',
        '0.2 mm layers · slicer estimate',
        f"{n['slice_time']} · {n['slice_g']} g",
        'one part, no open edges',
    ]))
    if 'runs' in n:
        write('video/terminal-runs.txt', '\n'.join([
            f"{n['runs']} runs · Claude Code · same prompt",
            f"right size: {n['runs_right_size']} of {n['runs']}",
            f"height 86 mm: {n['runs_height']} of {n['runs']}",
            f"narrow end north: {n['runs_north']} of {n['runs']}",
            f"agent cost: ${n['runs_total_usd']} at API prices",
        ]))

    ev = lambda c: f'{PROBE}/{c}/transcript.jsonl'  # noqa: E731
    tcs = []
    seq, _, _ = call_row(ev('px'), lambda p: p['name'] == 'batch')
    assert '"ok": true' in reply_text(ev('px'), seq) and '"warning": null' in reply_text(ev('px'), seq)
    tcs.append({'id': 'tc-import', 'evidence': f"{ev('px')}#seq={seq}", 'tool': 'batch', 'result': '"ok": true',
                'plain': 'drawing in, raised to 86: ok, no warning'})
    for cell, tid, plain in (('px', 'tc-px-volume', f"volume / 86 = {n['px_area']} mm2 of floor"),
                             ('mm', 'tc-mm-volume', f"volume / 86 = {n['mm_area']} mm2 of floor")):
        seq, _, _ = call_row(ev(cell), lambda p: p['name'] == 'measure')
        t = reply_text(ev(cell), seq)
        res = re.search(r'"volume_mm3": [\d.]+', t).group(0)
        tcs.append({'id': tid, 'evidence': f"{ev(cell)}#seq={seq}", 'tool': 'measure', 'result': res, 'plain': plain})
    write('video/toolcalls.json', json.dumps(tcs, indent=1))

    first = line_no('data/overpass.json', '"building:levels": "21"')
    h = line_no('data/overpass.json', '"height": "86"', first)
    cards = [{'id': 'json-tags', 'src': f'data/overpass.json#L{first}-{h + 1}', 'source_kind': 'the Overpass response we saved',
              'focus': [h], 'spoken': 'height, 86, in quotes'}]
    write('video/json-cards.json', json.dumps(cards, indent=1))
    a = line_no('city/footprints.py', 'def corner(')
    write('video/python-cards.json', json.dumps([
        {'id': 'py-corner', 'src': f'city/footprints.py#L{a}-{a + 5}', 'focus': [a + 2],
         'note': 'one corner (longitude, latitude) in: degrees east times metres per degree'},
        {'id': 'py-mm', 'src': f'city/footprints.py#L{a}-{a + 5}', 'focus': [a + 5],
         'note': 'metres in the city = millimetres at 1:1000'}], indent=1))
    print(json.dumps(n))


if __name__ == '__main__':
    main()
