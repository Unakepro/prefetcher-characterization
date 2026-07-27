#!/bin/bash
# run_hetero.sh — all candidates across several traces into ONE combined CSV.
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME first: . ./setvars.sh}"
BIN="${BIN:-$PYTHIA_HOME/bin/perceptron-multi-multi-no-ship-1core}"
PARSER="${PARSER:-$PYTHIA_HOME/scripts/py/parse_champsim.py}"
WARMUP="${WARMUP:-1000000}"
SIM="${SIM:-1000000}"
OUTDIR="${OUTDIR:-$PYTHIA_HOME/results/hetero}"
CSV="${CSV:-$OUTDIR/hetero_all.csv}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"

TR_NAMES=(leslie3d mcf bwaves gcc)
TR_FILES=(
  "$TRACEDIR/437.leslie3d-134B.champsimtrace.xz"
  "$TRACEDIR/429.mcf-184B.champsimtrace.xz"
  "$TRACEDIR/410.bwaves-1963B.champsimtrace.xz"
  "$TRACEDIR/403.gcc-16B.champsimtrace.xz"
)
PF_NAMES=(nopref stride streamer spp_dev2 bingo ipcp)
PF_FLAGS=(
  "--config=$PYTHIA_HOME/config/nopref.ini"
  "--l2c_prefetcher_types=stride --config=$PYTHIA_HOME/config/stride.ini"
  "--l2c_prefetcher_types=streamer --config=$PYTHIA_HOME/config/streamer.ini"
  "--l2c_prefetcher_types=spp_dev2 --config=$PYTHIA_HOME/config/spp_dev2.ini"
  "--l2c_prefetcher_types=bingo --config=$PYTHIA_HOME/config/bingo.ini"
  "--l1d_prefetcher_types=ipcp --l2c_prefetcher_types=ipcp"
)

mkdir -p "$OUTDIR"; rm -f "$CSV"
for j in "${!TR_NAMES[@]}"; do
  tname="${TR_NAMES[$j]}"; tfile="${TR_FILES[$j]}"
  [ -f "$tfile" ] || { echo "!! missing trace: $tfile — skipping $tname"; continue; }
  base_out="$OUTDIR/${tname}__nopref.out"
  echo "===== TRACE: $tname ====="
  for i in "${!PF_NAMES[@]}"; do
    name="${PF_NAMES[$i]}"; flags="${PF_FLAGS[$i]}"
    out="$OUTDIR/${tname}__${name}.out"
    echo ">> $tname / $name ..."
    "$BIN" --warmup_instructions=$WARMUP --simulation_instructions=$SIM $flags -traces "$tfile" > "$out" 2>&1
    grep -q "Core_0_IPC" "$out" || { echo "   !! no IPC for $tname/$name"; continue; }
    if [ "$name" = "nopref" ]; then
      python3 "$PARSER" --trace "$tname" --pref nopref --csv "$CSV" "$out" >/dev/null
    else
      python3 "$PARSER" --baseline "$base_out" --trace "$tname" --pref "$name" --csv "$CSV" "$out" >/dev/null
    fi
  done
done
echo; echo "=== combined: $CSV ==="; column -t -s, "$CSV" 2>/dev/null || cat "$CSV"
