#!/usr/bin/env bash
#SBATCH --job-name=pf_analyze
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --output=%x_%j.log
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
OUTDIR="${OUTDIR:-$STUDY_ROOT/results/slurm}"
ANALYSIS_DIR="${ANALYSIS_DIR:-$STUDY_ROOT/results/analysis}"
PYTHON="${PYTHON:-python3}"
ANALYZE_PLOTS="${ANALYZE_PLOTS:-1}"

mkdir -p "$ANALYSIS_DIR"
export PYTHIA_HOME="$STUDY_ROOT"
export OUTDIR
export PYTHON

count_matching_outputs() {
  find "$OUTDIR" -maxdepth 1 -type f -name '*.out' -print | wc -l | tr -d ' '
}

count_complete_outputs() {
  find "$OUTDIR" -maxdepth 1 -type f -name '*.out' \
    -exec grep -l '^Core_0_IPC ' {} + | wc -l | tr -d ' '
}

echo "== validate simulator outputs =="
OUTPUT_COUNT="$(count_matching_outputs)"
COMPLETE_COUNT="$(count_complete_outputs)"
[[ "$OUTPUT_COUNT" == "780" ]] || {
  echo "error: expected 780 .out files in $OUTDIR, found $OUTPUT_COUNT" >&2
  exit 1
}
[[ "$COMPLETE_COUNT" == "780" ]] || {
  echo "error: expected final IPC in 780 outputs, found $COMPLETE_COUNT" >&2
  exit 1
}

echo "== collect every configuration with matched baselines =="
COLLECT_SCOPE=all CSV="$ANALYSIS_DIR/characterization_all.csv" \
  bash "$STUDY_ROOT/scripts/collect.sh" > /dev/null

echo "== collect default configurations for selection-gain plots =="
COLLECT_SCOPE=default CSV="$ANALYSIS_DIR/characterization_default.csv" \
  bash "$STUDY_ROOT/scripts/collect.sh" > /dev/null

ALL_ROWS="$(($(wc -l < "$ANALYSIS_DIR/characterization_all.csv") - 1))"
DEFAULT_ROWS="$(($(wc -l < "$ANALYSIS_DIR/characterization_default.csv") - 1))"
[[ "$ALL_ROWS" == "741" ]] || {
  echo "error: expected 741 data rows in characterization_all.csv, found $ALL_ROWS" >&2
  exit 1
}
[[ "$DEFAULT_ROWS" == "78" ]] || {
  echo "error: expected 78 data rows in characterization_default.csv, found $DEFAULT_ROWS" >&2
  exit 1
}

{
  echo "PASS simulator outputs: $OUTPUT_COUNT/780 present"
  echo "PASS completed outputs: $COMPLETE_COUNT/780 contain final IPC"
  echo "PASS all-configuration CSV: $ALL_ROWS data rows"
  echo "PASS default-comparison CSV: $DEFAULT_ROWS data rows"
} | tee "$ANALYSIS_DIR/validation.txt"

"$PYTHON" "$STUDY_ROOT/scripts/py/compare_bases.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/compare_bases.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/bandwidth_sensitivity.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/channel_count.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/resource_pressure.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/resource_pressure.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/prefetch_diagnostics.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/prefetch_diagnostics.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/sensitivity.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/sensitivity.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/tuning.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/tuning.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/llc_size.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/llc_size.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/characterize.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/characterization_summary.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/suite_bootstrap.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/suite_bootstrap.txt"
"$PYTHON" "$STUDY_ROOT/scripts/py/prefix_stability.py" --results "$OUTDIR" \
  | tee "$ANALYSIS_DIR/prefix_stability.txt"

if [[ "$ANALYZE_PLOTS" == "1" ]]; then
  PLOT_CACHE_ROOT="${TMPDIR:-/tmp}/prefetcher-characterization-plot-cache"
  mkdir -p "$PLOT_CACHE_ROOT/matplotlib" "$PLOT_CACHE_ROOT/xdg"
  export MPLCONFIGDIR="${MPLCONFIGDIR:-$PLOT_CACHE_ROOT/matplotlib}"
  export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PLOT_CACHE_ROOT/xdg}"
  "$PYTHON" "$STUDY_ROOT/scripts/py/plot_selection_gain.py" \
    "$ANALYSIS_DIR/characterization_default.csv" --basis A \
    --out "$ANALYSIS_DIR/selection_gain_basis_A.png"
  "$PYTHON" "$STUDY_ROOT/scripts/py/plot_selection_gain.py" \
    "$ANALYSIS_DIR/characterization_default.csv" --basis B \
    --out "$ANALYSIS_DIR/selection_gain_basis_B.png"
else
  echo "ANALYZE_PLOTS=$ANALYZE_PLOTS; skipping optional plots"
fi

echo "analysis complete: $ANALYSIS_DIR"
