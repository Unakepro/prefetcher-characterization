#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STUDY_ROOT="${STUDY_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
SOURCE_DIR="${SOURCE_DIR:-$STUDY_ROOT/results/slurm}"
DEST_DIR="${DEST_DIR:-$STUDY_ROOT/results/raw}"
EXPECTED_COUNT="${EXPECTED_COUNT:-780}"

PRIVATE_PREFIX="${PRIVATE_PREFIX:-}"
PUBLIC_PREFIX='$PYTHIA_HOME'

[[ -d "$SOURCE_DIR" ]] || {
  echo "error: source directory not found: $SOURCE_DIR" >&2
  exit 1
}

if [[ -n "$PRIVATE_PREFIX" ]]; then
  [[ "$PRIVATE_PREFIX" == /* && "$PRIVATE_PREFIX" != "/" ]] || {
    echo "error: PRIVATE_PREFIX must be a non-root absolute path" >&2
    exit 1
  }
  [[ "$PRIVATE_PREFIX" != *'#'* ]] || {
    echo "error: PRIVATE_PREFIX must not contain '#'" >&2
    exit 1
  }
fi

source_count="$({ find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.out' -print; } | wc -l | tr -d ' ')"
if [[ "$source_count" != "$EXPECTED_COUNT" ]]; then
  echo "error: expected $EXPECTED_COUNT source outputs, found $source_count" >&2
  exit 1
fi

stage_dir="$(mktemp -d "${TMPDIR:-/tmp}/pf-sanitized.XXXXXX")"
cleanup() {
  rm -r -- "$stage_dir"
}
trap cleanup EXIT INT TERM

replacement_count=0
while IFS= read -r -d '' source_file; do
  filename="$(basename "$source_file")"
  staged_file="$stage_dir/$filename"

  file_matches=0
  if [[ -n "$PRIVATE_PREFIX" ]]; then
    file_matches="$({ grep -F -o "$PRIVATE_PREFIX" "$source_file" || true; } \
      | wc -l | tr -d ' ')"
  fi

  if [[ "$file_matches" -gt 0 ]]; then
    LC_ALL=C sed "s#${PRIVATE_PREFIX}#${PUBLIC_PREFIX}#g" \
      "$source_file" > "$staged_file"
  else
    cp "$source_file" "$staged_file"
  fi
  replacement_count=$((replacement_count + file_matches))

  if [[ -n "$PRIVATE_PREFIX" ]] && grep -F -q "$PRIVATE_PREFIX" "$staged_file"; then
    echo "error: private path remains in $staged_file" >&2
    exit 1
  fi
  if grep -E -q '(/home/|/Users/)' "$staged_file"; then
    [[ -n "$PRIVATE_PREFIX" ]] || \
      echo "error: set PRIVATE_PREFIX to redact unsanitized inputs" >&2
    echo "error: identifying path data remains in $staged_file" >&2
    exit 1
  fi
done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.out' -print0)

staged_count="$({ find "$stage_dir" -maxdepth 1 -type f -name '*.out' -print; } | wc -l | tr -d ' ')"
if [[ "$staged_count" != "$EXPECTED_COUNT" ]]; then
  echo "error: expected $EXPECTED_COUNT sanitized outputs, created $staged_count" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
find "$stage_dir" -maxdepth 1 -type f -name '*.out' -exec cp {} "$DEST_DIR/" \;

dest_count="$({ find "$DEST_DIR" -maxdepth 1 -type f -name '*.out' -print; } | wc -l | tr -d ' ')"
if [[ "$dest_count" != "$EXPECTED_COUNT" ]]; then
  echo "error: expected $EXPECTED_COUNT destination outputs, found $dest_count" >&2
  exit 1
fi

echo "sanitized outputs: $staged_count"
echo "replaced path occurrences: $replacement_count"
echo "destination: $DEST_DIR"
