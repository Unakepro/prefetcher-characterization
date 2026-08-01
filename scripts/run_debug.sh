#!/usr/bin/env bash
# run_debug.sh - Phase-0/3 debug pipeline: one trace, short runs, local loop.
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PYTHIA_SRC="${PYTHIA_SRC:-$STUDY_ROOT/Pythia}"
BIN="${BIN:-$PYTHIA_SRC/bin/perceptron-multi-multi-no-ship-1core}"
PARSER="${PARSER:-$STUDY_ROOT/scripts/py/parse_champsim.py}"
PYTHON="${PYTHON:-python3}"
TRACE="${TRACE:-$STUDY_ROOT/traces/437.leslie3d-134B.champsimtrace.xz}"
TRACE_NAME="${TRACE_NAME:-leslie3d}"
WARMUP="${WARMUP:-1000000}"
SIM="${SIM:-1000000}"
OUTDIR="${OUTDIR:-$STUDY_ROOT/results/debug}"
CSV="${CSV:-$OUTDIR/results_${TRACE_NAME}.csv}"

NAMES=(nopref stride streamer spp_dev2 bingo ipcp)
FLAGS=(
  "--config=$STUDY_ROOT/config/nopref.ini"
  "--l2c_prefetcher_types=stride --config=$STUDY_ROOT/config/stride.ini"
  "--l2c_prefetcher_types=streamer --config=$STUDY_ROOT/config/streamer.ini"
  "--l2c_prefetcher_types=spp_dev2 --config=$STUDY_ROOT/config/spp_dev2.ini"
  "--l2c_prefetcher_types=bingo --config=$STUDY_ROOT/config/bingo.ini"
  "--l1d_prefetcher_types=ipcp --l2c_prefetcher_types=ipcp"
)

[[ -x "$BIN" ]] || { echo "error: simulator is not executable: $BIN" >&2; exit 1; }
[[ -f "$TRACE" ]] || { echo "error: trace not found: $TRACE" >&2; exit 1; }
mkdir -p "$OUTDIR"
: > "$CSV"
BASE_OUT="$OUTDIR/${TRACE_NAME}__nopref.out"
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"; flags="${FLAGS[$i]}"
  read -r -a flag_args <<< "$flags"
  out="$OUTDIR/${TRACE_NAME}__${name}.out"
  echo ">> running $name ..."
  "$BIN" --warmup_instructions="$WARMUP" --simulation_instructions="$SIM" \
    "${flag_args[@]}" -traces "$TRACE" > "$out" 2>&1
  grep -q '^Core_0_IPC ' "$out" || { echo "error: no IPC for $name - see $out" >&2; exit 1; }
  if [ "$name" = "nopref" ]; then
    "$PYTHON" "$PARSER" --trace "$TRACE_NAME" --pref nopref --csv "$CSV" "$out"
  else
    "$PYTHON" "$PARSER" --baseline "$BASE_OUT" --trace "$TRACE_NAME" \
      --pref "$name" --csv "$CSV" "$out"
  fi
done
echo
echo "=== $CSV ==="
column -t -s, "$CSV" 2>/dev/null || command cat "$CSV"
