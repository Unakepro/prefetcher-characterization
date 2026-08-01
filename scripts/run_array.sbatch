#!/bin/bash
#SBATCH --job-name=pf_char
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --output=%x_%A_%a.log
# Supply --partition and --mem when invoking sbatch.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PYTHIA_SRC="${PYTHIA_SRC:-$STUDY_ROOT/Pythia}"
BIN="${BIN:-$PYTHIA_SRC/bin/perceptron-multi-multi-no-ship-1core}"
JOBLIST="${JOBLIST:-$STUDY_ROOT/experiments/joblist.txt}"
OUTDIR="${OUTDIR:-$STUDY_ROOT/results/slurm}"
WARMUP="${WARMUP:-50000000}"
SIM="${SIM:-150000000}"
FORCE="${FORCE:-0}"

[[ -x "$BIN" ]] || { echo "error: simulator is not executable: $BIN" >&2; exit 1; }
[[ -f "$JOBLIST" ]] || { echo "error: job list not found: $JOBLIST" >&2; exit 1; }
: "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}"
mkdir -p "$OUTDIR"

line=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$JOBLIST")
[[ -n "$line" ]] || {
  echo "error: no job-list row for task $SLURM_ARRAY_TASK_ID" >&2
  exit 1
}
IFS='|' read -r tname tfile pname flags <<< "$line"
[[ -n "$tname" && -n "$tfile" && -n "$pname" && -n "$flags" ]] || {
  echo "error: malformed job-list row $SLURM_ARRAY_TASK_ID: $line" >&2
  exit 1
}
[[ -f "$tfile" ]] || { echo "error: trace not found: $tfile" >&2; exit 1; }

out="$OUTDIR/${tname}__${pname}.out"
if [[ "$FORCE" != "1" && -f "$out" ]] && grep -q '^Core_0_IPC ' "$out"; then
  echo "SKIP: complete output exists -> $out"
  exit 0
fi

read -r -a flag_args <<< "$flags"
partial="${out}.partial.${SLURM_JOB_ID:-local}.${SLURM_ARRAY_TASK_ID}"

echo "[task $SLURM_ARRAY_TASK_ID] $tname / $pname"
"$BIN" --warmup_instructions="$WARMUP" --simulation_instructions="$SIM" \
  "${flag_args[@]}" -traces "$tfile" > "$partial" 2>&1
if ! grep -q '^Core_0_IPC ' "$partial"; then
  echo "FAIL: no final IPC in $partial" >&2
  exit 1
fi
mv "$partial" "$out"
echo "OK -> $out"
