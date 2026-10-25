"""Render-ready stills, all drawn by SolidCraft 0.19.0's product renderer (`solidcraft-cli render`), no AI, no repainting.

    docker run --rm -v <lab>:/work -w /work solidcraft-flatiron-lab:0.19.0 python3 video/make_frames.py [names...]

Each script that was rendered is kept next to its PNG (video/frames/*.script.json). The camera is set with view.apply
(target, yaw, pitch, distance; yaw 0 looks north from the south). "Floor" is a thin plate at z 0 and the north arrows
are flat shapes on it that we add (disclosed in the captions); the buildings come from the lab's command files as is,
except that the shrunk copy is moved beside the right one (solid.move, a translation only) and the bodies are coloured.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, LAB)
OUT = os.path.join(HERE, 'frames')
BLOCK = json.load(open(os.path.join(LAB, 'data', 'block.json'), encoding='utf-8'))
PX_SUMMARY = json.load(open(os.path.join(LAB, 'out', 'probe', '0.19.0', 'px', 'summary.json'), encoding='utf-8'))
MM_SUMMARY = json.load(open(os.path.join(LAB, 'out', 'probe', '0.19.0', 'mm', 'summary.json'), encoding='utf-8'))
STONE, RED, INK, FLOOR = '#cbc7ac', '#e53935', '#1f2937', '#e2e8f0'   # STONE = the building:colour tag in OSM


def steps(name):
    return json.load(open(os.path.join(LAB, 'steps', name + '.json'), encoding='utf-8'))['commands']


def renamed(commands, body):
    c = json.loads(json.dumps(commands))
    for x in c:
        if x['command'] == 'solid.extrude':
            x['params']['body_name'] = body
        if x['command'] == 'sketch.create':
            x['params']['name'] = body + 'Sketch'
        if x['command'] == 'solid.extrude':
            x['params']['sketch'] = body + 'Sketch'
    return c


def colour(body, c):
    return [{'command': 'appearance.assign', 'params': {'bodies': [body], 'color': c}}]


def floor(x0, y0, length, width):
    return [{'command': 'solid.box', 'params': {'length': length, 'width': width, 'height': 0.4, 'corner': [x0, y0, -0.4],
                                                'body_name': 'Floor'}}] + colour('Floor', FLOOR)


def arrow(name, x, y, size=14.0):
    """A flat north arrow on the floor at (x, y): a triangle tip pointing +Y (north) on a short bar."""
    s = size
    pts = [[x - s * 0.12, y - s * 0.5], [x + s * 0.12, y - s * 0.5], [x + s * 0.12, y + s * 0.1], [x + s * 0.32, y + s * 0.1],
           [x, y + s * 0.6], [x - s * 0.32, y + s * 0.1], [x - s * 0.12, y + s * 0.1]]
    return [{'command': 'sketch.create', 'params': {'plane': 'XY', 'name': name + 'Sketch'}},
            {'command': 'sketch.line', 'params': {'points': pts, 'closed': True}},
            {'command': 'sketch.finish', 'params': {}},
            {'command': 'solid.extrude', 'params': {'sketch': name + 'Sketch', 'distance': 0.6, 'body_name': name}}] + colour(name, INK)


def view(target, yaw, pitch, distance):
    return [{'command': 'view.apply', 'params': {'camera': {'target': target, 'yaw': yaw, 'pitch': pitch, 'distance': distance}}}]


def render(name, commands, w=1920, h=1080):
    os.makedirs(OUT, exist_ok=True)
    script = os.path.join(OUT, name + '.script.json')
    with open(script, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'commands': commands}, f)
    png = os.path.join(OUT, name + '.png')
    p = subprocess.run(['solidcraft-cli', 'render', script, '--out', png, '--width', str(w), '--height', str(h),
                        '--overwrite', '--timeout', '600'], capture_output=True, text=True, timeout=900)
    print(name, p.returncode, (p.stderr or '')[-300:], flush=True)
    if p.returncode != 0:
        raise SystemExit(f'{name} failed')


def centre(summary):
    a, b = summary['bbox_min'], summary['bbox_max']
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]


def pair():
    """The shrunk import (no unit) moved 45 mm to the west of the right one, both on one floor, a north arrow beside each."""
    px, mm = centre(PX_SUMMARY), centre(MM_SUMMARY)
    dx, dy = -45.0 - px[0], mm[1] - px[1]
    return (renamed(steps('flatiron-px'), 'Shrunk') +
            [{'command': 'solid.move', 'params': {'bodies': ['Shrunk'], 'translate': [dx, dy, 0]}}] +
            renamed(steps('flatiron-mm'), 'Flatiron') + colour('Shrunk', RED) + colour('Flatiron', STONE) +
            floor(-70, -40, 105, 80) + arrow('ArrowA', -28, -30, 16) + arrow('ArrowB', 24, -30, 16))


FRONT = view([-20, 2, 38], 0.0, 0.18, 205)          # from the south, a little above: widths and heights side by side
PAIR_ISO = view([-20, 2, 30], -0.55, 0.5, 215)      # from the south-west, looking down a little
BLOCK_ISO = view([0, 0, 18], -0.7854, 0.6, 250)
BLOCK_SW = view([0, 0, 20], 0.5, 0.45, 245)        # from the south-east, lower


def block():
    return steps('block-mm') + colour('Plate', STONE)     # every building is joined into the plate: one body


JOBS = {
    'pair-front': lambda: pair() + FRONT,
    'pair-iso': lambda: pair() + PAIR_ISO,
    'block-iso': lambda: block() + BLOCK_ISO,
    'block-se': lambda: block() + BLOCK_SW,
}

if __name__ == '__main__':
    for name, make in JOBS.items():
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        render(name, make())
