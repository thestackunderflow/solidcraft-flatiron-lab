"""Every number on a video panel comes from out/ or data/ (re-derived here), every panel fits a phone card, and every
tool-call panel's result really is in the reply it cites."""
import json
import os
import re

import pytest

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(LAB, *a)  # noqa: E731


def jload(*a):
    with open(P(*a), encoding='utf-8') as f:
        return json.load(f)


N = jload('out', 'evidence', 'numbers.json')
BLOCK = jload('data', 'block.json')
PX = jload('out', 'probe', '0.19.0', 'px', 'summary.json')
MM = jload('out', 'probe', '0.19.0', 'mm', 'summary.json')


def test_the_trap_numbers():
    assert N['px_w'] == f"{PX['size_mm'][0]:.1f}" and N['px_h'] == '86.0'
    assert abs(PX['width_vs_hand'] - 25.4 / 96) < 0.001             # CSS: 96 px per inch, 25.4 mm per inch
    assert abs(PX['footprint_vs_hand'] - (25.4 / 96) ** 2) < 0.001   # 7% of the floor, and of the volume
    assert N['width_ratio'] == '0.26' and N['times_narrower'] == '3.8'


def test_the_fix_numbers():
    assert MM['footprint_vs_hand'] == pytest.approx(1.0, abs=1e-4)
    assert N['mm_area'] == N['hand_area'] == f"{BLOCK['focus']['area_mm2']:,.1f}"
    assert N['height_tag'] == '86' and N['mm_h'] == '86.0'
    assert MM['north_check']['same_way'] is True
    assert jload('out', 'probe', '0.19.0', 'north', 'summary.json')['north_check']['same_way'] is False


def test_the_newer_release_behaves_the_same():
    v = jload('out', 'probe', '0.22.0', 'px', 'summary.json')
    assert v['version'] == '0.22.0' and v['size_mm'] == PX['size_mm']


@pytest.mark.parametrize('name', sorted(f for f in os.listdir(P('video')) if f.startswith('terminal-')))
def test_terminal_panels_fit_a_phone_card(name):
    lines = open(P('video', name), encoding='utf-8').read().splitlines()
    assert 1 <= len(lines) <= 7 and all(len(l) <= 44 for l in lines), lines


def test_toolcall_results_are_in_the_cited_replies():
    for tc in jload('video', 'toolcalls.json'):
        rel, seq = tc['evidence'].split('#seq=')
        rows = [json.loads(l) for l in open(P(rel), encoding='utf-8') if l.strip()]
        call = next(r for r in rows if r['seq'] == int(seq))
        reply = next(r for r in rows[rows.index(call):] if r['dir'] == 'server->client' and r['msg'].get('id') == call['msg']['id'])
        text = re.sub(r'\s+', ' ', ''.join(c.get('text', '') for c in reply['msg']['result']['content']))
        assert tc['result'] in text, tc['id']


def test_json_card_shows_the_height_tag_as_text():
    c = jload('video', 'json-cards.json')[0]
    f, r = c['src'].split('#L')
    a, b = map(int, r.split('-'))
    lines = open(P(f), encoding='utf-8').read().splitlines()
    assert lines[c['focus'][0] - 1].strip() == '"height": "86",'
    assert b - a + 1 <= 6


def test_python_cards_fit():
    for c in jload('video', 'python-cards.json'):
        f, r = c['src'].split('#L')
        a, b = map(int, r.split('-'))
        rows = open(P(f), encoding='utf-8').read().splitlines()[a - 1:b]
        assert len(rows) <= 6 and all(len(l) <= 45 for l in rows)
