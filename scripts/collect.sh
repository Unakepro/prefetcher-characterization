#!/bin/bash
set -u
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
PARSER="$PYTHIA_HOME/scripts/py/parse_champsim.py"
OUTDIR="${OUTDIR:-$PYTHIA_HOME/results/slurm}"
CSV="${CSV:-$OUTDIR/characterization.csv}"
rm -f "$CSV"
for base in "$OUTDIR"/*__nopref.out; do
  [ -f "$base" ] || continue
  tname="$(basename "$base")"; tname="${tname%%__*}"
  python3 "$PARSER" --trace "$tname" --pref nopref --csv "$CSV" "$base" >/dev/null
  for out in "$OUTDIR/${tname}__"*.out; do
    pname="$(basename "$out")"; pname="${pname#*__}"; pname="${pname%.out}"
    [ "$pname" = "nopref" ] && continue
    python3 "$PARSER" --baseline "$base" --trace "$tname" --pref "$pname" --csv "$CSV" "$out" >/dev/null
  done
done
echo "=== $CSV ==="; column -t -s, "$CSV" 2>/dev/null || cat "$CSV"
