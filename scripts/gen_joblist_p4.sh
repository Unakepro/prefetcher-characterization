#!/bin/bash
# Phase 4 placement: ipcp@L2-only, ipcp@L1D-only, stride@L1D across all traces.
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist_p4.txt}"
mkdir -p "$(dirname "$JOBLIST")"

TR_NAMES=(leslie3d mcf bwaves gcc omnetpp xalancbmk astar soplex lbm libquantum GemsFDTD milc sjeng)
TR_FILES=(437.leslie3d-134B 429.mcf-184B 410.bwaves-1963B 403.gcc-16B \
          471.omnetpp-188B 483.xalancbmk-716B 473.astar-153B 450.soplex-247B \
          470.lbm-1274B 462.libquantum-714B 459.GemsFDTD-765B 433.milc-127B 458.sjeng-283B)
# name | flags   (name encodes placement so .out files don't collide)
CF_NAMES=(ipcp_L2only ipcp_L1only stride_L1)
CF_FLAGS=(
  "--l2c_prefetcher_types=ipcp"
  "--l1d_prefetcher_types=ipcp"
  "--l1d_prefetcher_types=stride --config=$CFG/stride.ini"
)

> "$JOBLIST"
for j in "${!TR_NAMES[@]}"; do
  tname="${TR_NAMES[$j]}"; tfile="$TRACEDIR/${TR_FILES[$j]}.champsimtrace.xz"
  [ -f "$tfile" ] || echo "WARN: missing $tfile" >&2
  for i in "${!CF_NAMES[@]}"; do
    echo "${tname}|${tfile}|${CF_NAMES[$i]}|${CF_FLAGS[$i]}" >> "$JOBLIST"
  done
done
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
