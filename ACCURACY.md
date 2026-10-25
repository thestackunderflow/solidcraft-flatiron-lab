# ACCURACY: every number in the video and its file (SolidCraft 0.19.0, 24-25 Oct 2026)

Run the lab (README) to re-make every file below. `tests/test_evidence.py` re-derives the panel numbers from these files.

| Claim (as said or shown) | Value | File | Kind |
|---|---|---|---|
| Data: OpenStreetMap via the public Overpass API, way 264768896 + every building within 80 m | 37 ways | `data/overpass.json` (sha256 in `data/SOURCE.json`, fetched 2026-10-25 00:34 UTC, OSM base 00:32:51Z) | fetched |
| OSM's height tag for the Flatiron Building is text "86"; building:levels "21" | "86", "21" | `data/overpass.json` (lines 810-813) | quoted |
| Plate 120 x 90 mm at 1:1000 around the Flatiron; 11 buildings kept, 10 with a height tag, 1 by the rule (a kiosk: `shop=kiosk`, no height, no floors: one floor, 3 m); 26 dropped (24 off the plate, 1 roof with no walls, 1 piece under 1 mm) | | `data/block.json` | computed |
| The hand count of the Flatiron's footprint from OSM's corner points | 1,002.0 m² = 1,002.0 mm² at 1:1000 | `data/block.json` (`focus.area_mm2`, the shoelace sum, tested in `tests/test_footprints.py`) | computed |
| 1 m graph-paper squares whose centre is inside the outline | 1,001 | `out/evidence/grid-count.json` | computed |
| Imported with no unit: `ok: true`, no warning | | `out/probe/0.19.0/px/transcript.jsonl` seq 8-9 | measured |
| Imported with no unit: 8.3 x 15.8 x 86.0 mm; the corners say 31.2 x 59.8 mm | width ratio 0.26458 = 25.4 / 96 | `out/probe/0.19.0/px/summary.json` | measured |
| Its floor area (volume / 86) | 70.1 mm² (7.0% of 1,002.0; 7.0% of the volume) | `out/probe/0.19.0/px/summary.json`, measure reply seq 10-11 | measured |
| Cause: a unitless SVG number is a user unit = a CSS pixel; 96 px = 1 in = 25.4 mm, so 1 unit = 0.2646 mm | | w3.org/TR/SVG2/coords.html, w3.org/TR/css-values-3 (plan ACCURACY F4); our ratio matches to 5 digits | quoted + measured |
| Fix: `width="120mm" height="90mm"` on a 120-unit viewBox: 31.2 x 59.8 x 86.0 mm, floor 1,002.0 mm² (measure) and 1,002.0 (STL) | | `out/probe/0.19.0/mm/summary.json` | measured |
| `scale: 3.7795` (96 / 25.4) on import gives the same size (not taught) | | `out/probe/0.19.0/scale/summary.json` | measured |
| North check: the narrow end's bearing, map 11.6°, model 11.6°; the drawing written without north as minus y: 168.4° | | `out/probe/0.19.0/{mm,north}/summary.json` (`tests/stl_tools.py` `prow`) | measured |
| Block: one body, watertight, 120 x 90 x 88 mm, volume 193,971 mm³ vs the hand count 193,971 (0.0002%) | | `out/probe/0.19.0/block/summary.json` | measured |
| SolidCraft 0.22.0 (released 24 Oct 2026): the same 8.3 x 15.8 mm and 1,002.0 mm² | | `out/probe/0.22.0/*/summary.json` | measured |
| Slicer estimate: PrusaSlicer 2.9.2, MK4S 0.4, PLA, 0.2 mm layers, 15% infill: 3h 6m 33s, 103 g, one part, no open edges | | `out/slice/slice-report.json` | measured (estimate) |
| Thin features in the G-code: a 0.84 mm piece got 1 line (so the rule is 1 mm); the next thinnest piece 5 lines; the Flatiron's narrow end 0.4 mm under its top 4 lines | | `out/slice/thin-*.json` | measured |
| Agent runs: Claude Code 2.1.310, claude-sonnet-5-5, the same prompt (it says one unit is one metre, north is up, 1:1000, height tag 86), 3 runs: each imported plainly, read the sketch back (`inspect_design`), re-imported with `scale` 3.7795; right size (STL footprint within 1% of 1,002.0), height 86.0 and north (within 5°) 3 of 3; $0.43 | | `out/runs/SCORES.json`, `out/runs/plain-*/transcript.jsonl`, `run-meta.json`, the shared ledger | measured |
| Not quoted: run 1's final answer says the long Fifth Ave side is on the east (it is the west side); no Claude text goes on screen | | `out/runs/plain-1/claude-output.json` | checked |

Not claimed: that the Flatiron is 86 m tall (only "OpenStreetMap's height tag says 86"); any print time or strength beyond
the slicer's estimate; anything about SolidCraft versions other than 0.19.0 and 0.22.0.
