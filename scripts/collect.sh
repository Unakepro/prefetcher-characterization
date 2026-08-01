#!/bin/bash
set -eu
: "${PYTHIA_HOME:?set PYTHIA_HOME}"
PARSER="$PYTHIA_HOME/scripts/py/parse_champsim.py"
OUTDIR="${OUTDIR:-$PYTHIA_HOME/results/slurm}"
CSV="${CSV:-$OUTDIR/characterization.csv}"
PYTHON="${PYTHON:-python3}"
COLLECT_SCOPE="${COLLECT_SCOPE:-all}"

case "$COLLECT_SCOPE" in
  all|default) ;;
  *)
    echo "ERROR: COLLECT_SCOPE must be 'all' or 'default' (got '$COLLECT_SCOPE')" >&2
    exit 2
    ;;
esac

# Configuration variants must be normalized against a no-prefetch run with the
# same hardware configuration. Keep the configuration suffix in the prefetcher
# column so existing consumers can distinguish the rows without a schema change.
baseline_for () {
  local trace="$1" pref="$2"
  case "$pref" in
    *_2ch) echo "$OUTDIR/${trace}__nopref_2ch.out" ;;
    *_1MB) echo "$OUTDIR/${trace}__nopref_1MB.out" ;;
    *_4MB) echo "$OUTDIR/${trace}__nopref_4MB.out" ;;
    *)     echo "$OUTDIR/${trace}__nopref.out" ;;
  esac
}

: > "$CSV"
for base in "$OUTDIR"/*__nopref.out; do
  [ -f "$base" ] || continue
  tname="$(basename "$base")"; tname="${tname%%__*}"
  "$PYTHON" "$PARSER" --trace "$tname" --pref nopref --csv "$CSV" "$base" >/dev/null
  for out in "$OUTDIR/${tname}__"*.out; do
    [ -f "$out" ] || continue
    pname="$(basename "$out")"; pname="${pname#*__}"; pname="${pname%.out}"
    # Baselines are inputs, never prefetcher candidates.
    case "$pname" in
      nopref|nopref_*) continue ;;
    esac
    if [ "$COLLECT_SCOPE" = "default" ]; then
      case "$pname" in
        stride|streamer|spp_dev2|bingo|ipcp) ;;
        *) continue ;;
      esac
    fi
    matched_base="$(baseline_for "$tname" "$pname")"
    if [ ! -f "$matched_base" ]; then
      echo "ERROR: missing matched baseline for $out: $matched_base" >&2
      exit 1
    fi
    "$PYTHON" "$PARSER" --baseline "$matched_base" --trace "$tname" \
      --pref "$pname" --csv "$CSV" "$out" >/dev/null
  done
done
echo "=== $CSV ==="; column -t -s, "$CSV" 2>/dev/null || cat "$CSV"
