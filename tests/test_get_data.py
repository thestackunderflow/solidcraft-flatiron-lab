"""The Overpass request (PLAN rev 2.1 §6.3, ACCURACY D11-D12): it says who we are (a User-Agent: without one the public
server answered HTTP 406), retries once after 30 s, and falls back to the cached ODbL response, so the lab runs offline.
No network here: the opener and the clock are fakes."""
import io
import json
import os
import sys
import tempfile
import urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from city import get_data as G  # noqa: E402

BODY = json.dumps({'elements': [{'type': 'way', 'id': 1, 'tags': {'building': 'yes'}, 'geometry': []}]}).encode()


class Opener:
    def __init__(self, *results):
        self.results = list(results)
        self.requests = []

    def __call__(self, req, timeout):
        self.requests.append(req)
        r = self.results.pop(0)
        if isinstance(r, Exception):
            raise r
        return io.BytesIO(r)


def http(code):
    return urllib.error.HTTPError('https://x', code, 'err', {}, None)


def test_query_names_the_focus_way_and_the_radius():
    q = G.query(264768896, 80)
    assert 'way(264768896)' in q and 'around.f:80' in q and 'out geom' in q and '[out:json]' in q


def test_request_has_a_user_agent():
    op, slept = Opener(BODY), []
    body, how = G.fetch('q', opener=op, sleep=slept.append, cache=None)
    assert body == BODY and how == 'live'
    ua = op.requests[0].get_header('User-agent')
    assert ua and 'solidcraft-flatiron-lab' in ua


def test_one_retry_after_30_seconds():
    op, slept = Opener(http(429), BODY), []
    body, how = G.fetch('q', opener=op, sleep=slept.append, cache=None)
    assert body == BODY and how == 'live after one retry' and slept == [30]


def test_falls_back_to_the_cache_after_two_failures():
    p = os.path.join(tempfile.mkdtemp(), 'cache.json')
    with open(p, 'wb') as f:
        f.write(BODY)
    op, slept = Opener(http(504), http(504)), []
    body, how = G.fetch('q', opener=op, sleep=slept.append, cache=p)
    assert body == BODY and how == 'cached' and slept == [30] and len(op.requests) == 2


def test_no_cache_and_two_failures_raises():
    op = Opener(http(504), http(504))
    with pytest.raises(urllib.error.HTTPError):
        G.fetch('q', opener=op, sleep=lambda s: None, cache=None)


def test_offline_flag_uses_the_cache_without_asking():
    p = os.path.join(tempfile.mkdtemp(), 'cache.json')
    with open(p, 'wb') as f:
        f.write(BODY)
    op = Opener()
    body, how = G.fetch('q', opener=op, sleep=lambda s: None, cache=p, offline=True)
    assert body == BODY and how == 'cached' and op.requests == []


def test_the_cached_response_is_in_the_lab():
    """The lab's tests run offline: the response we used is committed, with its checksum."""
    lab = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    src = json.load(open(os.path.join(lab, 'data', 'SOURCE.json'), encoding='utf-8'))
    raw = open(os.path.join(lab, src['file']), 'rb').read()
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == src['sha256']
    assert src['licence'] == 'ODbL 1.0' and 'openstreetmap.org/copyright' in src['credit']
    d = json.loads(raw)
    assert any(e['id'] == 264768896 for e in d['elements'])
