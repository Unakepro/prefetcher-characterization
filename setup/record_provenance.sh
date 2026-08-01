#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PYTHIA_SRC="${PYTHIA_SRC:-$STUDY_ROOT/Pythia}"
TRACEDIR="${TRACEDIR:-$STUDY_ROOT/traces}"
EXPERIMENT_DIR="${EXPERIMENT_DIR:-$STUDY_ROOT/experiments}"
BASE_BINARY=perceptron-multi-multi-no-ship-1core

sha256_file() {
  if command -v sha256sum >/dev/null; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "unavailable"
  fi
}

git_value() {
  local checkout="$1"
  if [[ -d "$checkout/.git" ]]; then
    git -C "$checkout" rev-parse HEAD
  else
    echo "unavailable"
  fi
}

git_state() {
  local checkout="$1"
  if [[ ! -d "$checkout/.git" ]]; then
    echo "unavailable"
  elif [[ -n "$(git -C "$checkout" status --porcelain --untracked-files=no)" ]]; then
    echo "dirty"
  else
    echo "clean"
  fi
}

printf 'recorded_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'study_commit=%s\n' "$(git_value "$STUDY_ROOT")"
printf 'study_tracked_state=%s\n' "$(git_state "$STUDY_ROOT")"
printf 'pythia_commit=%s\n' "$(git_value "$PYTHIA_SRC")"
printf 'pythia_tracked_state=%s\n' "$(git_state "$PYTHIA_SRC")"
printf 'libbf_commit=%s\n' "$(git_value "$PYTHIA_SRC/libbf")"
printf 'libbf_tracked_state=%s\n' "$(git_state "$PYTHIA_SRC/libbf")"
printf 'system=%s\n' "$(uname -a)"
printf 'cxx=%s\n' "$(c++ --version 2>/dev/null | head -n 1 || echo unavailable)"
printf 'python=%s\n' "$("${PYTHON:-python3}" --version 2>&1 || echo unavailable)"
printf 'slurm=%s\n' "$(sbatch --version 2>/dev/null || echo unavailable)"
printf 'warmup_instructions=%s\n' "${WARMUP:-50000000}"
printf 'simulation_instructions=%s\n' "${SIM:-150000000}"

for suffix in "" "-2ch" "-1MB" "-4MB"; do
  binary="$PYTHIA_SRC/bin/$BASE_BINARY$suffix"
  [[ -f "$binary" ]] || { echo "error: missing binary $binary" >&2; exit 1; }
  printf 'binary_sha256[%s]=%s\n' "${suffix:-default}" "$(sha256_file "$binary")"
done

for config in "$STUDY_ROOT"/config/*.ini; do
  [[ -f "$config" ]] || continue
  printf 'config_sha256[%s]=%s\n' "$(basename "$config")" "$(sha256_file "$config")"
done

while IFS=, read -r trace filename md5 url; do
  [[ "$trace" == "trace" ]] && continue
  trace_path="$TRACEDIR/$filename"
  [[ -f "$trace_path" ]] || {
    echo "error: missing trace while recording provenance: $trace_path" >&2
    exit 1
  }
  printf 'trace_sha256[%s]=%s\n' "$filename" "$(sha256_file "$trace_path")"
done < "$STUDY_ROOT/config/traces.csv"

for joblist in "$EXPERIMENT_DIR"/joblist*.txt; do
  [[ -f "$joblist" ]] || continue
  printf 'joblist_sha256[%s]=%s\n' \
    "$(basename "$joblist")" "$(sha256_file "$joblist")"
done

echo "trace_manifest_begin"
sed -n '1,200p' "$STUDY_ROOT/config/traces.csv"
echo "trace_manifest_end"
