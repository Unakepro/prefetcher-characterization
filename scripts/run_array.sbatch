#!/bin/bash
#SBATCH --job-name=pf_char
#SBATCH --partition=PARTITION   # <-- set to your Slurm partition
#SBATCH --cpus-per-task=1
#SBATCH --mem=<MEMORY>
#SBATCH --time=02:00:00
#SBATCH --output=%x_%A_%a.log
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
BIN="$PYTHIA_HOME/bin/perceptron-multi-multi-no-ship-1core"
JOBLIST="${JOBLIST:-$PYTHIA_HOME/experiments/joblist.txt}"
OUTDIR="${OUTDIR:-$PYTHIA_HOME/results/slurm}"
WARMUP="${WARMUP:-50000000}"
SIM="${SIM:-150000000}"
mkdir -p "$OUTDIR"

line=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$JOBLIST")
tname="${line%%|*}"; rest="${line#*|}"
tfile="${rest%%|*}"; rest="${rest#*|}"
pname="${rest%%|*}"; flags="${rest#*|}"
out="$OUTDIR/${tname}__${pname}.out"

echo "[task $SLURM_ARRAY_TASK_ID] $tname / $pname"
$BIN --warmup_instructions=$WARMUP --simulation_instructions=$SIM $flags -traces "$tfile" > "$out" 2>&1
grep -q Core_0_IPC "$out" && echo "OK -> $out" || { echo "FAIL: no IPC in $out"; exit 1; }
