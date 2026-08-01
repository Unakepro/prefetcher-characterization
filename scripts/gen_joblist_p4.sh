#!/bin/bash
# Phase 4 placement: ipcp@L2-only, ipcp@L1D-only, stride@L1D across all traces.
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist_p4.txt}"
mkdir -p "$(dirname "$JOBLIST")"

source "$PYTHIA_HOME/scripts/load_trace_manifest.sh"
# name | flags   (name encodes placement so .out files don't collide)
CF_NAMES=(ipcp_L2only ipcp_L1only stride_L1)
CF_FLAGS=(
  "--l2c_prefetcher_types=ipcp"
  "--l1d_prefetcher_types=ipcp"
  "--l1d_prefetcher_types=stride --config=$CFG/stride.ini"
)

> "$JOBLIST"
for j in "${!TRACE_NAMES[@]}"; do
  tname="${TRACE_NAMES[$j]}"; tfile="$TRACEDIR/${TRACE_FILES[$j]}"
  [ -f "$tfile" ] || echo "WARN: missing $tfile" >&2
  for i in "${!CF_NAMES[@]}"; do
    echo "${tname}|${tfile}|${CF_NAMES[$i]}|${CF_FLAGS[$i]}" >> "$JOBLIST"
  done
done
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
