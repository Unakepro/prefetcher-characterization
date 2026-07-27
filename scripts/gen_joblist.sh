#!/bin/bash
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist.txt}"
mkdir -p "$(dirname "$JOBLIST")"

TR_NAMES=(leslie3d mcf bwaves gcc omnetpp xalancbmk astar soplex lbm libquantum GemsFDTD milc sjeng)
TR_FILES=(437.leslie3d-134B 429.mcf-184B 410.bwaves-1963B 403.gcc-16B \
          471.omnetpp-188B 483.xalancbmk-716B 473.astar-153B 450.soplex-247B \
          470.lbm-1274B 462.libquantum-714B 459.GemsFDTD-765B 433.milc-127B 458.sjeng-283B)
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
for j in "${!TR_NAMES[@]}"; do
  tname="${TR_NAMES[$j]}"; tfile="$TRACEDIR/${TR_FILES[$j]}.champsimtrace.xz"
  [ -f "$tfile" ] || echo "WARN: missing $tfile" >&2
  for p in "${PF_NAMES[@]}"; do
    echo "${tname}|${tfile}|${p}|$(pf_flags "$p")" >> "$JOBLIST"
  done
done
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
