#!/bin/bash

set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist_p5.txt}"
mkdir -p "$(dirname "$JOBLIST")"

source "$PYTHIA_HOME/scripts/load_trace_manifest.sh"
PF_NAMES=(nopref stride streamer spp_dev2 bingo ipcp)
pf_flags () { case "$1" in
  nopref)   echo "--config=$CFG/nopref.ini";;
  stride)   echo "--l2c_prefetcher_types=stride --config=$CFG/stride.ini";;
  streamer) echo "--l2c_prefetcher_types=streamer --config=$CFG/streamer.ini";;
  spp_dev2) echo "--l2c_prefetcher_types=spp_dev2 --config=$CFG/spp_dev2.ini";;
  bingo)    echo "--l2c_prefetcher_types=bingo --config=$CFG/bingo.ini";;
  ipcp)     echo "--l1d_prefetcher_types=ipcp --l2c_prefetcher_types=ipcp";;
esac; }

> "$JOBLIST"
for j in "${!TRACE_NAMES[@]}"; do
  tname="${TRACE_NAMES[$j]}"; tfile="$TRACEDIR/${TRACE_FILES[$j]}"
  [ -f "$tfile" ] || echo "WARN: missing $tfile" >&2
  for p in "${PF_NAMES[@]}"; do
    echo "${tname}|${tfile}|${p}_2ch|$(pf_flags "$p")" >> "$JOBLIST"
  done
done
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
