"""Download the buildings: OpenStreetMap via the public Overpass API (no account).

    python3 city/get_data.py              (needs network; falls back to the cached response)
    python3 city/get_data.py --offline    (the cached response only)

Change ONE line for your own place: FOCUS_WAY, the OpenStreetMap id of a building way (find it on openstreetmap.org:
click the building, the address bar says /way/<id>). The query asks for that building and every building within RADIUS_M
of it, with corner points and tags. Etiquette for the public server (wiki.openstreetmap.org/wiki/Overpass_API): say who
you are (a User-Agent: without one the server answered HTTP 406 in our probe), one retry after 30 s, and keep a cached copy.

Data © OpenStreetMap contributors, available under the Open Database License (ODbL) 1.0:
https://www.openstreetmap.org/copyright . data/ is under ODbL 1.0 (LICENSE-DATA), the code under Apache-2.0.
"""
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FOCUS_WAY = 264768896          # the Flatiron Building, New York: change this line for your place
RADIUS_M = 80                  # covers the 120 x 90 m plate around it (half-diagonal 75 m)
URL = 'https://overpass-api.de/api/interpreter'
UA = 'StackUnderflow-solidcraft-flatiron-lab/1.0 (lab for a YouTube tutorial; one request per run)'
CREDIT = '© OpenStreetMap contributors, https://www.openstreetmap.org/copyright (ODbL)'
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
CACHE = os.path.join(DATA, 'overpass.json')


def query(way, radius):
    return f'[out:json][timeout:60];way({way})->.f;(.f;way["building"](around.f:{radius}););out geom tags;'


def fetch(q, opener=urllib.request.urlopen, sleep=time.sleep, cache=CACHE, offline=False):
    """(body bytes, how): 'live', 'live after one retry' or 'cached'."""
    if offline:
        with open(cache, 'rb') as f:
            return f.read(), 'cached'
    req = urllib.request.Request(URL, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': UA})
    err = None
    for attempt in range(2):
        try:
            return opener(req, timeout=120).read(), 'live' if attempt == 0 else 'live after one retry'
        except (urllib.error.URLError, OSError) as e:
            err = e
            if attempt == 0:
                sleep(30)
    if cache and os.path.exists(cache):
        with open(cache, 'rb') as f:
            return f.read(), 'cached'
    raise err


def main(offline=False):
    os.makedirs(DATA, exist_ok=True)
    q = query(FOCUS_WAY, RADIUS_M)
    body, how = fetch(q, offline=offline)
    json.loads(body)                      # it must be JSON
    if how != 'cached':
        with open(CACHE, 'wb') as f:
            f.write(body)
        src = {'source': 'OpenStreetMap via the Overpass API', 'url': URL, 'query': q, 'focus_way': FOCUS_WAY,
               'radius_m': RADIUS_M, 'fetched_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'file': 'data/overpass.json', 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
               'licence': 'ODbL 1.0', 'credit': CREDIT}
        with open(os.path.join(DATA, 'SOURCE.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(src, f, indent=1, ensure_ascii=False)
            f.write('\n')
    print(how, len(body), 'bytes')


if __name__ == '__main__':
    main(offline='--offline' in sys.argv)
