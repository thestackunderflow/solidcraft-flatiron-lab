"""claude-run/score.py on synthetic run folders (the probe's STLs stand in for Claude's export): how Claude sized the
drawing (scale on import, a resize afterwards, a re-drawn outline, or nothing), and the lab's own checks of the
exported flatiron.stl against OpenStreetMap: the footprint area vs the hand count, the height vs OSM's height tag, and
the north check (the narrow end points the way the map does)."""
import json
import os
import shutil
import sys
import tempfile

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(LAB, 'claude-run'))
import score  # noqa: E402

PROBE = os.path.join(LAB, 'out', 'probe', '0.19.0')


def row(d, msg):
    return json.dumps({'t': 'x', 'seq': 1, 'dir': d, 'msg': msg})


def call(i, name, args):
    return row('client->server', {'jsonrpc': '2.0', 'id': i, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})


def reply(i, body, err=False):
    return row('server->client', {'jsonrpc': '2.0', 'id': i, 'result': {'isError': err, 'content': [{'type': 'text', 'text': json.dumps(body)}]}})


def make_run(cmds, stl_from=None, final='Done.'):
    d = tempfile.mkdtemp()
    rows = []
    for i, (name, args) in enumerate(cmds, 1):
        rows += [call(i, name, args), reply(i, {'ok': True})]
    with open(os.path.join(d, 'transcript.jsonl'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows) + '\n')
    with open(os.path.join(d, 'claude-output.json'), 'w', encoding='utf-8') as f:
        json.dump({'total_cost_usd': 0.4, 'num_turns': 9, 'result': final}, f)
    if stl_from:
        shutil.copy(os.path.join(PROBE, stl_from, 'model.stl'), os.path.join(d, 'flatiron.stl'))
    return d


IMPORT = ('execute', {'command': 'sketch.insert_svg', 'params': {'path': '/lab/data/flatiron.svg'}})


def test_no_fix_comes_in_a_quarter_as_wide():
    s = score.score_run(make_run([IMPORT, ('execute', {'command': 'solid.extrude', 'params': {'distance': 86}})], 'px'))
    assert s['fix'] == 'none' and s['cost_usd'] == 0.4
    m = s['measured']
    assert m['right_size'] is False and 0.06 < m['footprint_vs_hand'] < 0.08
    assert abs(m['width_vs_hand'] - 25.4 / 96) < 0.001
    assert m['height_mm'] == 86.0 and m['height_ok'] is True


def test_scale_on_import_is_the_right_size_and_points_north():
    s = score.score_run(make_run([('execute', {'command': 'sketch.insert_svg',
                                               'params': {'path': '/lab/data/flatiron.svg', 'scale': 3.7795}})], 'scale'))
    assert s['fix'] == 'scale on import'
    m = s['measured']
    assert m['right_size'] is True and m['north_ok'] is True and m['pieces'] == 1 and m['watertight'] is True


def test_a_resize_afterwards_is_named():
    s = score.score_run(make_run([IMPORT, ('batch', {'commands': [{'command': 'solid.scale', 'params': {'factor': 3.78}}]})], 'mm'))
    assert s['fix'] == 'resize afterwards'


def test_a_redrawn_outline_is_named():
    s = score.score_run(make_run([IMPORT, ('execute', {'command': 'sketch.line', 'params': {'points': [[0, 0], [1, 1]]}})], 'mm'))
    assert s['fix'] == 'redrawn outline'


def test_the_mirror_image_fails_the_north_check():
    s = score.score_run(make_run([IMPORT], 'north'))
    assert s['measured']['right_size'] is True and s['measured']['north_ok'] is False


def test_no_stl_is_no_measurement():
    assert score.score_run(make_run([IMPORT]))['measured'] is None
