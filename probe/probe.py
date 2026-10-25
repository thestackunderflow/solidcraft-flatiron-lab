"""THE PROBE (no AI, $0): the Flatiron Building's OpenStreetMap footprint imported into SolidCraft as an SVG drawing,
over MCP, behind the logging proxy.

    docker run --rm -v <lab>:/work -v <lab>/out/probe/<ver>:/lab/out -w /work solidcraft-flatiron-lab:<ver> \
        python3 probe/probe.py <ver>

Cells (each a fresh new_design):
  px       steps/flatiron-px.json: the drawing has no unit (as a plain script writes it), extruded to OSM's height tag
  mm       steps/flatiron-mm.json: the drawing says width="120mm" (the fix)
  scale    the no-unit drawing imported with scale 3.7795 (96 / 25.4): the other way to fix it (not taught)
  north    the mm drawing written WITHOUT turning north into SVG's screen-up (y kept, not negated): a mirror image
  block    steps/block-mm.json: the plate + every building, joined
After each: measure, export STL, and the lab's own checks (tests/stl_tools.py): watertight, pieces, volume, the footprint
area (volume / height, two ways: SolidCraft's measure and the STL), and the north check (which way the narrow end
points, in the model's section and in OSM's corners).
Every request and reply: <cell>/transcript.jsonl (proxy format: the video's tool-call panels cite these rows).
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(LAB, 'tests'))
sys.path.insert(0, LAB)
from mcp_client import Hang, McpClient, SERVER_CMD  # noqa: E402
from stl_tools import bodies, poly_segments, prow, read_stl, section_segments, volume, watertight  # noqa: E402
from city import footprints as F  # noqa: E402
from city import make_block as B  # noqa: E402

VER = sys.argv[1] if len(sys.argv) > 1 else '0.19.0'
CELLS = sys.argv[2:] or ['px', 'mm', 'scale', 'north', 'block']
OUT = '/lab/out'
PROXY = os.path.join(LAB, 'proxy', 'mcp_log_proxy.py')
BLOCK = json.load(open(os.path.join(LAB, 'data', 'block.json'), encoding='utf-8'))
H = BLOCK['focus']['height_m']
HAND = BLOCK['focus']['area_mm2']


def steps(name):
    with open(os.path.join(LAB, 'steps', name + '.json'), encoding='utf-8') as f:
        return json.load(f)['commands']


def with_svg(commands, svg, **extra):
    c = json.loads(json.dumps(commands))
    for x in c:
        if x['command'] == 'sketch.insert_svg':
            x['params']['text'] = svg
            x['params'].update(extra)
    return c


class Session:
    def __init__(self):
        self.c = None

    def start(self, transcript):
        self.stop()
        self.c = McpClient(['python3', PROXY, '--log', transcript, '--watchdog', '180', '--'] + SERVER_CMD, timeout_s=240)
        self.c.start()

    def stop(self):
        if self.c is not None:
            self.c.close()
        self.c = None

    def call(self, name, args):
        r = self.c.call_tool(name, args)
        t = '\n'.join(b['text'] for b in r.get('content', []) if b.get('type') == 'text')
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return t


S = Session()


def save(d, name, obj):
    with open(os.path.join(d, name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write('\n')


def run_cell(name, commands, height=H, focus=True):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    res = {'cell': name, 'version': VER, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    try:
        S.start(os.path.join(d, 'transcript.jsonl'))
        S.call('new_design', {'name': name})
        r = S.call('batch', {'commands': commands})
        res['ok'] = r.get('ok') if isinstance(r, dict) else False
        res['failed'] = r.get('failed') if isinstance(r, dict) else str(r)[:400]
        res['warnings'] = [x.get('warning') for x in (r.get('results') or []) if isinstance(x, dict) and x.get('warning')] \
            if isinstance(r, dict) else []
        m = S.call('measure', {})
        save(d, 'measure.json', m)
        b = m['bodies']
        res['bodies'] = [x['name'] for x in b]
        res['volume_mm3'] = round(sum(x['volume_mm3'] for x in b), 3)
        res['bbox_min'] = [round(min(x['bbox']['min'][i] for x in b), 4) for i in range(3)]
        res['bbox_max'] = [round(max(x['bbox']['max'][i] for x in b), 4) for i in range(3)]
        res['size_mm'] = [round(res['bbox_max'][i] - res['bbox_min'][i], 3) for i in range(3)]
        p = f'{OUT}/{name}/model.stl'
        S.call('export', {'path': p})
        t = read_stl(p)
        res['stl'] = {'watertight': watertight(t), 'bodies': bodies(t), 'triangles': int(len(t)),
                      'volume_mm3': round(volume(t), 3)}
        if focus:
            res['footprint_mm2'] = {'measure': round(res['volume_mm3'] / height, 3),
                                    'stl': round(res['stl']['volume_mm3'] / height, 3), 'hand_count': round(HAND, 3)}
            res['footprint_vs_hand'] = round(res['footprint_mm2']['measure'] / HAND, 5)
            hx = [x for x, _ in BLOCK['focus']['mm']]
            res['hand_size_mm'] = [round(max(hx) - min(hx), 3),
                                   round(max(y for _, y in BLOCK['focus']['mm']) - min(y for _, y in BLOCK['focus']['mm']), 3)]
            res['width_vs_hand'] = round(res['size_mm'][0] / res['hand_size_mm'][0], 5)
            mine, data = prow(section_segments(t, height / 2)), prow(poly_segments(BLOCK['focus']['mm']))
            diff = abs((mine['bearing_deg'] - data['bearing_deg'] + 180) % 360 - 180)
            res['north_check'] = {'model': mine, 'map': data, 'off_by_deg': round(diff, 2), 'same_way': diff < 2.0}
        else:
            res['hand_volume_mm3'] = round(BLOCK['hand_volume_mm3'], 3)
            res['volume_vs_hand_pct'] = round(100 * (res['volume_mm3'] / BLOCK['hand_volume_mm3'] - 1), 4)
    except Hang as e:
        res['HANG'] = str(e)
    finally:
        S.stop()
    save(d, 'summary.json', res)
    print(json.dumps({k: res.get(k) for k in ('cell', 'ok', 'size_mm', 'volume_mm3', 'footprint_mm2', 'footprint_vs_hand',
                                              'width_vs_hand', 'north_check', 'stl', 'volume_vs_hand_pct', 'failed')}, default=str),
          flush=True)
    return res


def main():
    noflip = F.svg_text([(f"w{BLOCK['focus']['id']}", [(x, -y) for x, y in BLOCK['focus']['mm']])], *B.PLATE_MM, unit='mm')
    cells = {
        'px': lambda: run_cell('px', steps('flatiron-px')),
        'mm': lambda: run_cell('mm', steps('flatiron-mm')),
        'scale': lambda: run_cell('scale', with_svg(steps('flatiron-px'), B.flatiron_svg(BLOCK, None), scale=96 / 25.4)),
        'north': lambda: run_cell('north', with_svg(steps('flatiron-mm'), noflip)),
        'block': lambda: run_cell('block', steps('block-mm'), focus=False),
    }
    for c in CELLS:
        cells[c]()


if __name__ == '__main__':
    main()
