#!/usr/bin/env bash
# Source the authoritative study trace manifest into TRACE_NAMES/TRACE_FILES.

TRACE_MANIFEST="${TRACE_MANIFEST:-$PYTHIA_HOME/config/traces.csv}"
EXPECTED_TRACE_COUNT="${EXPECTED_TRACE_COUNT:-13}"
[[ -f "$TRACE_MANIFEST" ]] || {
  echo "error: trace manifest not found: $TRACE_MANIFEST" >&2
  return 1 2>/dev/null || exit 1
}

TRACE_NAMES=()
TRACE_FILES=()
while IFS=, read -r trace_name trace_file _; do
  [[ "$trace_name" == "trace" ]] && continue
  [[ -n "$trace_name" && -n "$trace_file" ]] || continue
  TRACE_NAMES+=("$trace_name")
  TRACE_FILES+=("$trace_file")
done < "$TRACE_MANIFEST"

if [[ "${#TRACE_NAMES[@]}" -ne "$EXPECTED_TRACE_COUNT" ]]; then
  echo "error: expected $EXPECTED_TRACE_COUNT traces, found ${#TRACE_NAMES[@]} in $TRACE_MANIFEST" >&2
  return 1 2>/dev/null || exit 1
fi
