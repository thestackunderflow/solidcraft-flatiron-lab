# SolidCraft Flatiron lab: a city block from OpenStreetMap, at the right scale

The lab behind "SolidCraft + Claude: The Flatiron Block from Map Data" (SolidCraft for Beginners #6, The Stack
Underflow). OpenStreetMap's building outlines around the Flatiron Building in New York become an SVG drawing, SolidCraft
imports it, and each building stands at its height on a printable plate. Everything runs in Docker on SolidCraft 0.19.0.

What it found (24-25 Oct 2026):
- The drawing written as a plain script writes it, numbers with no unit (`viewBox="-60 -45 120 90"`, metres meant),
  imported with `sketch.insert_svg` and raised 86 mm: `ok: true`, no warning, and the building is 8.3 x 15.8 mm instead of
  31.2 x 59.8. A quarter as wide (0.26), full height. An SVG number with no unit is a screen pixel, and 96 pixels make an
  inch (25.4 mm), so one unit became 0.26 mm.
- The fix: the drawing says its size, `width="120mm" height="90mm"`. Now one unit is one millimetre: map scale 1:1000.
  The floor area is 1,002.0 mm², the same as the hand count from OSM's corner points (1,002.0 m²; 1,001 squares of 1 m
  graph paper). `scale: 3.7795` on import does the same.
- The height is 86 mm because OpenStreetMap's height tag says "86" (text; the script makes it a number).
- North check: the Flatiron's narrow end points 11.6° east of north on the map and in the model. Written without turning
  north into SVG's screen-up (minus y), the model is a mirror image: 168.4°.
- The block: 11 buildings on a 120 x 90 x 2 mm plate, joined into one watertight body, 88 mm tall.
- Claude Code (claude-sonnet-5-5), the same prompt, 3 runs: each imported the drawing, read the sketch back, saw it
  was about four times too small and re-imported it with `scale` 3.7795. Right size, 86 mm and north 3 of 3; $0.43 in all.
- SolidCraft 0.22.0 (released 24 Oct 2026) behaves the same.
Every number and its file: `ACCURACY.md`. Nothing here was printed; times and weights are the slicer's estimate.

## Your place: change one line
`city/get_data.py`: `FOCUS_WAY = 264768896`, the OpenStreetMap id of a building way (on openstreetmap.org, click the
building: the address bar says /way/<id>). Then run the steps below. Limits: the plate is 120 x 90 m around that building;
a building with no height tag gets its floors x 3 m, or one floor (3 m) with no floors either; a tower over 168 m will not
fit a 170 mm printer at 1:1000. Pieces thinner than 1 mm are dropped (`out/slice/thin-*.json`: a 0.84 mm piece got one
printed line). Please use the public Overpass server lightly (one request per run, a User-Agent, a cached copy).

## Follow along: three ways
1. **Just print it.** `out/probe/0.19.0/block/model.stl`: 120 x 90 x 88 mm. Slicer estimate on an MK4S profile, 0.2 mm
   layers, 15% infill: about 3 h 7 min, 103 g.
2. **Build it with no AI.** `solidcraft-cli run steps/block-mm.json --out block.stl` (SolidCraft 0.19.0; the CLI is in
   the release download). `steps/flatiron-px.json` is the Flatiron alone from the drawing with no unit: try it.
3. **Ask Claude.** Give Claude the prompt in `claude-run/run.sh` with `data/flatiron.svg`. We ran Claude Code in a
   terminal with only SolidCraft's tools.

## Run the lab
```
docker build -t solidcraft-flatiron-lab:0.19.0 .
docker run --rm -v "$PWD:/work" -w /work solidcraft-flatiron-lab:0.19.0 python3 -m pytest -q tests/
docker run --rm -v "$PWD:/work" -w /work solidcraft-flatiron-lab:0.19.0 python3 city/get_data.py --offline
docker run --rm -v "$PWD:/work" -w /work solidcraft-flatiron-lab:0.19.0 python3 city/make_block.py
docker run --rm -v "$PWD:/work" -v "$PWD/out/probe/0.19.0:/lab/out" -w /work solidcraft-flatiron-lab:0.19.0 python3 probe/probe.py 0.19.0
```
The tests run offline: the Overpass response we used is in `data/overpass.json` (checksum in `data/SOURCE.json`).

## Credit and licences
Map data © OpenStreetMap contributors, https://www.openstreetmap.org/copyright . The data in `data/`, the command files
and the STL files made from it are under the Open Database License (ODbL) 1.0 (`LICENSE-DATA`): credit OpenStreetMap,
and share what you build from the data under the same licence. The code is Apache-2.0 (`LICENSE`).
Contains data © OpenStreetMap contributors, ODbL, openstreetmap.org/copyright. Narration of the video: AI-generated voice.
