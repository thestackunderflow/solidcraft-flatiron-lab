# LAB-STATUS (25 Oct 2026)

**State: video done (PUBLISH/60, release Fri 13 Nov only if the release gate holds); lab stays local, no remote, until the
video ships.** Plan: `Refream-Canvas/inputs/video-plans/2026-10-22-solidcraft-open-data/` (PLAN rev 2.1 §6.3;
DECISIONS-script-flatiron.md). Cards pinned at the commit in `video/panel-sources.json`.

- Data: OpenStreetMap via Overpass (way 264768896 + buildings within 80 m), cached in `data/overpass.json` (ODbL, LICENSE-DATA).
- Probe (no AI, $0, 0.19.0): no unit = 8.3 x 15.8 mm (0.2646 = 25.4/96), floor 7.0%; width="120mm" = 1,002.0 mm2 = hand
  count; scale 3.7795 the same; north 11.6 deg (map 11.6), flipped drawing 168.4; block 1 watertight body, 120 x 90 x 88.
  0.22.0: the same numbers.
- Slicer: PrusaSlicer 2.9.2, MK4S 0.4 FAST DETAIL preset at 0.2 mm, PLA, 15%: 3h 6m 33s, 103 g (estimate). Sliver rule
  1 mm (a 0.84 mm piece got one line).
- Agent runs: 3 plain, $0.43 (shared ledger); 3 of 3 read the sketch back and re-imported with scale; right size, 86 mm,
  north 3 of 3.
- Tests: 82 passed (`out/green-phase-all.log`); red logs `out/red-phase-*.log`.
- Video: 6:22, -14.0 LUFS / -1.2 dBTP, QA no real problems; Short 26.5 s, -14.5 / -1.4. Kit in
  `Refream-Canvas/inputs/mcp-usecases/solidcraft-flatiron/`.
