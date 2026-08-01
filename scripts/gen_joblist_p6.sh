#!/bin/bash
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
TRACEDIR="${TRACEDIR:-$PYTHIA_HOME/traces}"
CFG="$PYTHIA_HOME/config"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist_p6.txt}"
mkdir -p "$(dirname "$JOBLIST")"

source "$PYTHIA_HOME/scripts/load_trace_manifest.sh"

emit () {
  local pref="$1" base="$2" knob="$3"; shift 3
  for v in "$@"; do
    for j in "${!TRACE_NAMES[@]}"; do
      local tname="${TRACE_NAMES[$j]}" tfile="$TRACEDIR/${TRACE_FILES[$j]}"
      local vtag="${v//./p}"
      echo "${tname}|${tfile}|${pref}__${knob}_${vtag}|${base} --${knob}=${v}" >> "$JOBLIST"
    done
  done
}

> "$JOBLIST"
emit stride   "--l2c_prefetcher_types=stride --config=$CFG/stride.ini"     stride_pref_degree      1 4 8 16
emit streamer "--l2c_prefetcher_types=streamer --config=$CFG/streamer.ini" streamer_pref_degree    1 2 4 16
emit spp_dev2 "--l2c_prefetcher_types=spp_dev2 --config=$CFG/spp_dev2.ini" spp_dev2_pf_threshold   20 60 80
emit spp_dev2 "--l2c_prefetcher_types=spp_dev2 --config=$CFG/spp_dev2.ini" spp_dev2_fill_threshold 50 70 100
emit bingo    "--l2c_prefetcher_types=bingo --config=$CFG/bingo.ini"       bingo_l2c_thresh        0.5 0.65 0.95
emit bingo    "--l2c_prefetcher_types=bingo --config=$CFG/bingo.ini"       bingo_pht_size          1024 2048 8192
echo "wrote $JOBLIST ($(wc -l < "$JOBLIST") jobs)"
