#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PYTHIA_SRC="${PYTHIA_SRC:-$STUDY_ROOT/Pythia}"
TRACEDIR="${TRACEDIR:-$STUDY_ROOT/traces}"
OUTDIR="${OUTDIR:-$STUDY_ROOT/results/slurm}"
ANALYSIS_DIR="${ANALYSIS_DIR:-$STUDY_ROOT/results/analysis}"
PYTHON="${PYTHON:-python3}"

PARTITION="${PARTITION:?set PARTITION to the Slurm partition}"
JOB_MEMORY="${JOB_MEMORY:?set JOB_MEMORY, for example 4G}"
ARRAY_LIMIT="${ARRAY_LIMIT:?set ARRAY_LIMIT to the maximum concurrent jobs}"
ARRAY_LIMIT_LLC="${ARRAY_LIMIT_LLC:-$ARRAY_LIMIT}"
ANALYSIS_MEMORY="${ANALYSIS_MEMORY:-$JOB_MEMORY}"
WARMUP="${WARMUP:-50000000}"
SIM="${SIM:-150000000}"

BASE_BINARY=perceptron-multi-multi-no-ship-1core
BIN_DEFAULT="$PYTHIA_SRC/bin/$BASE_BINARY"
BIN_2CH="$PYTHIA_SRC/bin/$BASE_BINARY-2ch"
BIN_1MB="$PYTHIA_SRC/bin/$BASE_BINARY-1MB"
BIN_4MB="$PYTHIA_SRC/bin/$BASE_BINARY-4MB"
RUNNER="$STUDY_ROOT/scripts/run_array.sbatch"
EXPERIMENT_DIR="$STUDY_ROOT/experiments"

command -v sbatch >/dev/null || { echo "error: sbatch is required" >&2; exit 1; }
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 8)' || {
  echo "error: PYTHON must select Python 3.8 or newer" >&2
  exit 1
}
for binary in "$BIN_DEFAULT" "$BIN_2CH" "$BIN_1MB" "$BIN_4MB"; do
  [[ -x "$binary" ]] || {
    echo "error: missing simulator variant $binary" >&2
    echo "run $STUDY_ROOT/setup/bootstrap_pythia.sh first" >&2
    exit 1
  }
done

TRACEDIR="$TRACEDIR" "$STUDY_ROOT/setup/fetch_traces.sh" --verify-only
mkdir -p "$EXPERIMENT_DIR" "$OUTDIR" "$ANALYSIS_DIR"

# The job-list generators predate the split between study files and the pinned
# Pythia checkout. PYTHIA_HOME intentionally points at the study root here:
# runtime configs, traces, scripts, and results live under STUDY_ROOT, while
# BIN points at the separately pinned PYTHIA_SRC checkout.
export PYTHIA_HOME="$STUDY_ROOT"
export TRACEDIR

submit_array() {
  local limit="$1" binary="$2" joblist="$3"
  local count
  count="$(wc -l < "$joblist" | tr -d ' ')"
  [[ "$count" =~ ^[1-9][0-9]*$ ]] || {
    echo "error: empty or invalid job list $joblist" >&2
    return 1
  }
  sbatch --parsable --partition="$PARTITION" --array="1-$count%$limit" \
    --mem="$JOB_MEMORY" \
    --export="ALL,STUDY_ROOT=$STUDY_ROOT,PYTHIA_SRC=$PYTHIA_SRC,BIN=$binary,JOBLIST=$joblist,OUTDIR=$OUTDIR,WARMUP=$WARMUP,SIM=$SIM" \
  "$RUNNER"
}

JOB3="$EXPERIMENT_DIR/joblist.txt"
JOBLIST="$JOB3" bash "$STUDY_ROOT/scripts/gen_joblist.sh"

JOB4="$EXPERIMENT_DIR/joblist_p4.txt"
JOBLIST="$JOB4" bash "$STUDY_ROOT/scripts/gen_joblist_p4.sh"

JOB5="$EXPERIMENT_DIR/joblist_p5.txt"
JOBLIST="$JOB5" bash "$STUDY_ROOT/scripts/gen_joblist_p5.sh"

JOB6="$EXPERIMENT_DIR/joblist_p6.txt"
JOBLIST="$JOB6" bash "$STUDY_ROOT/scripts/gen_joblist_p6.sh"

JOB7="$EXPERIMENT_DIR/joblist_p7.txt"
JOBLIST="$JOB7" bash "$STUDY_ROOT/scripts/gen_joblist_p7.sh"

JOB8A="$EXPERIMENT_DIR/joblist_p8_1MB.txt"
JOB8B="$EXPERIMENT_DIR/joblist_p8_4MB.txt"
SIZE=1MB JOBLIST="$JOB8A" bash "$STUDY_ROOT/scripts/gen_joblist_p8.sh"
SIZE=4MB JOBLIST="$JOB8B" bash "$STUDY_ROOT/scripts/gen_joblist_p8.sh"

STUDY_ROOT="$STUDY_ROOT" PYTHIA_SRC="$PYTHIA_SRC" \
  TRACEDIR="$TRACEDIR" EXPERIMENT_DIR="$EXPERIMENT_DIR" PYTHON="$PYTHON" \
  WARMUP="$WARMUP" SIM="$SIM" "$STUDY_ROOT/setup/record_provenance.sh" \
  > "$ANALYSIS_DIR/provenance.txt"

echo "== Phase 3: default prefetchers =="
J3="$(submit_array "$ARRAY_LIMIT" "$BIN_DEFAULT" "$JOB3")"

echo "== Phase 4: placement =="
J4="$(submit_array "$ARRAY_LIMIT" "$BIN_DEFAULT" "$JOB4")"

echo "== Phase 5: two-channel variant =="
J5="$(submit_array "$ARRAY_LIMIT" "$BIN_2CH" "$JOB5")"

echo "== Phase 6: one-parameter sensitivity screening =="
J6="$(submit_array "$ARRAY_LIMIT" "$BIN_DEFAULT" "$JOB6")"

echo "== Phase 7: follow-up joint SPP threshold grid =="
J7="$(submit_array "$ARRAY_LIMIT" "$BIN_DEFAULT" "$JOB7")"

echo "== Phase 8: LLC-capacity variants =="
J8A="$(submit_array "$ARRAY_LIMIT_LLC" "$BIN_1MB" "$JOB8A")"
J8B="$(submit_array "$ARRAY_LIMIT_LLC" "$BIN_4MB" "$JOB8B")"

DEPENDENCY="afterok:$J3:$J4:$J5:$J6:$J7:$J8A:$J8B"
echo "== analysis (dependency: $DEPENDENCY) =="
ANALYSIS_JOB="$(sbatch --parsable --partition="$PARTITION" \
  --dependency="$DEPENDENCY" --mem="$ANALYSIS_MEMORY" \
  --export="ALL,STUDY_ROOT=$STUDY_ROOT,PYTHIA_SRC=$PYTHIA_SRC,OUTDIR=$OUTDIR,ANALYSIS_DIR=$ANALYSIS_DIR,PYTHON=$PYTHON" \
  "$STUDY_ROOT/scripts/analyze.sh")"

echo "submitted simulation arrays: $J3 $J4 $J5 $J6 $J7 $J8A $J8B"
echo "submitted analysis job: $ANALYSIS_JOB"
echo "watch with: squeue -u \$USER"
