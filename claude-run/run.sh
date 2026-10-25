#!/usr/bin/env bash
# One logged, headless Claude Code run against SolidCraft 0.19.0 (flatiron lab) (clean: no user CLAUDE.md, no user settings, no memory).
#   bash claude-run/run.sh plain RUN_ID
# plain: import data/flatiron.svg (the Flatiron footprint from OpenStreetMap, drawn with no unit, one unit = one metre),
# build it at 1:1000 to OSM's height tag (86), export flatiron.stl, report footprint area, bbox, height. The trap is not named. Claude Code --stdio--> docker run -i ... [mcp_log_proxy.py
# --watchdog 180 --stdio--> solidcraft-cli mcp]; only the solidcraft tools. From solidcraft-fillet-shell-lab, plus:
#   1. the SHARED ledger of the four SolidCraft open-data labs ($20 total, owner 22 Oct 2026; claude-run/budget.py),
#      checked before the run: no start when the logged total + this run's cap would pass $20;
#   2. cost survives a kill: an empty claude-output.json is logged at the run's full cap ("killed-floor");
#   3. the proxy's watchdog writes HANG after 180 s without a reply and kills the server; this script then kills claude.
set -euo pipefail
ARM=$1; RUN=$2
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
OUT=out/runs/$ARM-$RUN
LEDGER="${LEDGER:-$LAB/../solidcraft-opendata-BUDGET.tsv}"
MODEL="${MODEL:-claude-sonnet-5-5}"
BUDGET="${BUDGET:-1.00}"
python claude-run/budget.py check "$LEDGER" "$BUDGET" || { echo "BUDGET STOP"; exit 2; }
[ -e "$OUT/run-meta.json" ] && { echo "refusing to overwrite $OUT"; exit 3; }
mkdir -p "$OUT"
NAME="flatiron-$ARM-$RUN-$$"

cat > "$OUT/mcp-config.json" <<JSON
{"mcpServers": {"solidcraft": {"command": "docker", "args": ["run", "-i", "--rm", "--name", "$NAME", "-v", "$LAB/proxy:/proxy:ro", "-v", "$LAB/data:/lab/data:ro", "-v", "$LAB/$OUT:/lab/out", "solidcraft-flatiron-lab:0.19.0", "python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/out/transcript.jsonl", "--png-dir", "/lab/out", "--watchdog", "180", "--", "solidcraft-cli", "mcp", "--allow-path", "/lab/out", "--allow-path", "/lab/data"]}}}
JSON

PROMPT="Use the solidcraft MCP tools. /lab/data/flatiron.svg is a drawing of the Flatiron Building's footprint in New York, made from OpenStreetMap data: one unit in the drawing is one metre, and north is up. OpenStreetMap's height tag for the building is 86 (metres). Make a 1:1000 scale model, so 1 metre becomes 1 millimetre: import the drawing into a sketch on the XY plane, extrude it to the right height, and export it as STL to /lab/out/flatiron.stl. Report the footprint area in square millimetres, the bounding box and the height."
printf '%s\n' "$PROMPT" > "$OUT/prompt.txt"

T0=$(date +%s)
set +e
MSYS_NO_PATHCONV=1 timeout 900 "${CLAUDE:-claude}" -p "$PROMPT" --model "$MODEL" \
  --mcp-config "$OUT/mcp-config.json" --strict-mcp-config \
  --tools "" --allowedTools "mcp__solidcraft__*" --permission-mode dontAsk \
  --max-budget-usd "$BUDGET" --no-session-persistence \
  --setting-sources project,local --settings '{"claudeMdExcludes":["**/.claude/CLAUDE.md"],"autoMemoryEnabled":false}' \
  --output-format json < /dev/null > "$OUT/claude-output.json" &
PID=$!
HUNG=0
while kill -0 "$PID" 2>/dev/null; do
  if grep -q '"HANG"' "$OUT/transcript.jsonl" 2>/dev/null; then
    HUNG=1
    WP=$(cat /proc/$PID/winpid 2>/dev/null || true)
    kill "$PID" 2>/dev/null; [ -n "$WP" ] && taskkill //F //T //PID "$WP" >/dev/null 2>&1
    docker kill "$NAME" >/dev/null 2>&1
    break
  fi
  sleep 3
done
wait "$PID"; RC=$?
set -e
docker kill "$NAME" >/dev/null 2>&1 || true
# no host path in the saved config (the lab may be published)
sed -i "s#$LAB#\$LAB#g" "$OUT/mcp-config.json"
COST=$(python -c "import json,sys
try: print(json.load(open(sys.argv[1]))['total_cost_usd'])
except Exception: print('')" "$OUT/claude-output.json")
python claude-run/budget.py record "$LEDGER" "flatiron-$ARM-$RUN" "$COST" "$BUDGET" flatiron
echo "{\"arm\": \"$ARM\", \"run\": \"$RUN\", \"model\": \"$MODEL\", \"budget_usd\": $BUDGET, \"exit\": $RC, \"hang_killed\": $HUNG, \"wall_s\": $(( $(date +%s) - T0 )), \"claude_version\": \"$(${CLAUDE:-claude} --version | head -1)\", \"solidcraft\": \"0.19.0\"}" > "$OUT/run-meta.json"
cat "$OUT/run-meta.json"; echo "cost ${COST:-killed (counted at cap)}"
