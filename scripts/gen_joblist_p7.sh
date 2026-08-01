#!/bin/bash
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist_p7.txt}"
mkdir -p "$(dirname "$JOBLIST")"

source "$PYTHIA_HOME/scripts/load_trace_manifest.sh"
COMBOS=("20 50" "20 70" "20 90" "20 100" "40 50" "40 70" "40 90" "40 100" "60 70" "60 90" "60 100" "80 90" "80 100")
BASE="--l2c_prefetcher_types=spp_dev2 --config=$CFG/spp_dev2.ini"

> "$JOBLIST"
for c in "${COMBOS[@]}"; do
  set -- $c; pf=$1; fill=$2
  for j in "${!TRACE_NAMES[@]}"; do
    tname="${TRACE_NAMES[$j]}"; tfile="$TRACEDIR/${TRACE_FILES[$j]}"
    echo "${tname}|${tfile}|spp_dev2__pf${pf}_fill${fill}|${BASE} --spp_dev2_pf_threshold=${pf} --spp_dev2_fill_threshold=${fill}" >> "$JOBLIST"
  done
done
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
