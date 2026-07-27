#!/bin/bash
# run_debug.sh — Phase-0/3 debug pipeline: one trace, short runs, local loop.
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME first: . ./setvars.sh}"
BIN="${BIN:-$PYTHIA_HOME/bin/perceptron-multi-multi-no-ship-1core}"
PARSER="${PARSER:-$PYTHIA_HOME/scripts/py/parse_champsim.py}"
TRACE="${TRACE:-$PYTHIA_HOME/traces/437.leslie3d-134B.champsimtrace.xz}"
TRACE_NAME="${TRACE_NAME:-leslie3d}"
WARMUP="${WARMUP:-1000000}"
SIM="${SIM:-1000000}"
OUTDIR="${OUTDIR:-$PYTHIA_HOME/results/debug}"
CSV="${CSV:-$OUTDIR/results_${TRACE_NAME}.csv}"

NAMES=(nopref stride streamer spp_dev2 bingo ipcp)
FLAGS=(
  "--config=$PYTHIA_HOME/config/nopref.ini"
  "--l2c_prefetcher_types=stride --config=$PYTHIA_HOME/config/stride.ini"
  "--l2c_prefetcher_types=streamer --config=$PYTHIA_HOME/config/streamer.ini"
  "--l2c_prefetcher_types=spp_dev2 --config=$PYTHIA_HOME/config/spp_dev2.ini"
  "--l2c_prefetcher_types=bingo --config=$PYTHIA_HOME/config/bingo.ini"
  "--l1d_prefetcher_types=ipcp --l2c_prefetcher_types=ipcp"
)

mkdir -p "$OUTDIR"; rm -f "$CSV"
BASE_OUT="$OUTDIR/${TRACE_NAME}__nopref.out"
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"; flags="${FLAGS[$i]}"
  out="$OUTDIR/${TRACE_NAME}__${name}.out"
  echo ">> running $name ..."
  "$BIN" --warmup_instructions=$WARMUP --simulation_instructions=$SIM $flags -traces "$TRACE" > "$out" 2>&1
  grep -q "Core_0_IPC" "$out" || { echo "   !! no IPC for $name — see $out"; continue; }
  if [ "$name" = "nopref" ]; then
    python3 "$PARSER" --trace "$TRACE_NAME" --pref nopref --csv "$CSV" "$out"
  else
    python3 "$PARSER" --baseline "$BASE_OUT" --trace "$TRACE_NAME" --pref "$name" --csv "$CSV" "$out"
  fi
done
echo; echo "=== $CSV ==="; column -t -s, "$CSV" 2>/dev/null || cat "$CSV"
