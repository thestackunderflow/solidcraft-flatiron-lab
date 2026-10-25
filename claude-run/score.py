"""Score every agent run in out/runs/<arm>-<n>/: cost, turns, tool calls, failed calls, how Claude sized the drawing
(scale on import / resize afterwards / redrawn outline / none), and the lab's checks of the exported flatiron.stl
against OpenStreetMap (data/block.json): the footprint area (volume / height) vs the hand count from OSM's corner
points (right size = within 1%), the height vs OSM's height tag (86), the north check (the narrow end's bearing within
5 degrees of the map's). Writes out/runs/SCORES.json.

    python3 claude-run/score.py
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(LAB, 'tests'))
from stl_tools import bodies, poly_segments, prow, read_stl, section_segments, volume, watertight  # noqa: E402

BLOCK = json.load(open(os.path.join(LAB, 'data', 'block.json'), encoding='utf-8'))
FOCUS = BLOCK['focus']


def _rows(p):
    with open(p, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def _commands(name, args):
    if name == 'batch':
        return [c for c in args.get('commands', []) if isinstance(c, dict)]
    if name == 'execute':
        return [{'command': args.get('command'), 'params': args.get('params') or {}}]
    return [{'command': name, 'params': args}]


def classify(cmds):
    for c in cmds:
        p = c.get('params') or {}
        if c.get('command') == 'sketch.insert_svg' and p.get('scale') not in (None, 1, 1.0):
            return 'scale on import'
    names = [c.get('command') for c in cmds]
    if 'solid.scale' in names or any(n and n.startswith('solid.scale') for n in names):
        return 'resize afterwards'
    if any(n in ('sketch.line', 'sketch.polyline', 'sketch.polygon') for n in names):
        return 'redrawn outline'
    return 'none'


def measure(d):
    p = os.path.join(d, 'flatiron.stl')
    if not os.path.exists(p):
        return None
    t = read_stl(p)
    v = t.reshape(-1, 3)
    lo, hi = v.min(axis=0), v.max(axis=0)
    h = float(hi[2] - lo[2])
    area = volume(t) / h if h > 0 else 0.0
    hx = [x for x, _ in FOCUS['mm']]
    mine, data = prow(section_segments(t, float(lo[2]) + h / 2)), prow(poly_segments(FOCUS['mm']))
    off = abs((mine['bearing_deg'] - data['bearing_deg'] + 180) % 360 - 180)
    return {'footprint_mm2': round(area, 2), 'hand_count_mm2': round(FOCUS['area_mm2'], 2),
            'footprint_vs_hand': round(area / FOCUS['area_mm2'], 5), 'right_size': bool(abs(area / FOCUS['area_mm2'] - 1) < 0.01),
            'width_vs_hand': round(float(hi[0] - lo[0]) / (max(hx) - min(hx)), 5),
            'height_mm': round(h, 3), 'height_ok': bool(abs(h - FOCUS['height_m']) < 0.1),
            'prow_bearing_deg': mine['bearing_deg'], 'map_bearing_deg': data['bearing_deg'], 'north_ok': bool(off < 5.0),
            'bbox_min': [round(float(a), 3) for a in lo], 'bbox_max': [round(float(a), 3) for a in hi],
            'watertight': watertight(t), 'pieces': bodies(t)}


def score_run(d):
    rows = _rows(os.path.join(d, 'transcript.jsonl'))
    calls, replies = {}, {}
    for r in rows:
        m = r.get('msg') or {}
        if r.get('dir') == 'client->server' and m.get('method') == 'tools/call':
            calls[m['id']] = m['params']
        elif r.get('dir') == 'server->client' and 'id' in m and 'result' in m:
            replies[m['id']] = m['result']
    cmds, failed, errors = [], 0, []
    for i, p in calls.items():
        cmds += _commands(p['name'], p.get('arguments') or {})
        res = replies.get(i) or {}
        t = '\n'.join(c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text')
        try:
            body = json.loads(t)
        except (json.JSONDecodeError, TypeError):
            body = t
        if res.get('isError') or (isinstance(body, dict) and body.get('ok') is False):
            failed += 1
            errors.append((body.get('failed') or {}).get('error') if isinstance(body, dict) else str(body)[:200])
    try:
        out = json.load(open(os.path.join(d, 'claude-output.json'), encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        out = {}
    return {'run': os.path.basename(d.rstrip('/\\')), 'cost_usd': out.get('total_cost_usd'), 'turns': out.get('num_turns'),
            'tool_calls': len(calls), 'failed_calls': failed, 'failed_errors': errors, 'fix': classify(cmds),
            'final_answer': (out.get('result') or '')[:1500], 'measured': measure(d)}


def main():
    root = os.path.join(LAB, 'out', 'runs')
    runs = [score_run(d) for d in sorted(glob.glob(os.path.join(root, '*-*'))) if os.path.isdir(d)]
    with open(os.path.join(root, 'SCORES.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'runs': runs}, f, indent=1)
    for r in runs:
        print(json.dumps({k: r[k] for k in ('run', 'cost_usd', 'fix', 'failed_calls', 'measured')}))


if __name__ == '__main__':
    main()
