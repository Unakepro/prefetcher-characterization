#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
MANIFEST="${TRACE_MANIFEST:-$REPO_ROOT/config/traces.csv}"
TRACEDIR="${TRACEDIR:-$REPO_ROOT/traces}"
VERIFY_ONLY=0

if [[ "${1:-}" == "--verify-only" ]]; then
  VERIFY_ONLY=1
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--verify-only]" >&2
  exit 2
fi

command -v curl >/dev/null || {
  echo "error: curl is required to download traces" >&2
  exit 1
}

md5_file() {
  if command -v md5sum >/dev/null; then
    md5sum "$1" | awk '{print $1}'
  elif command -v md5 >/dev/null; then
    md5 -q "$1"
  else
    echo "error: md5sum or md5 is required to verify traces" >&2
    return 1
  fi
}

mkdir -p "$TRACEDIR"
checked=0

while IFS=, read -r trace filename expected_md5 url; do
  [[ "$trace" == "trace" ]] && continue
  [[ -n "$trace" && -n "$filename" && -n "$expected_md5" && -n "$url" ]] || {
    echo "error: malformed row in $MANIFEST" >&2
    exit 1
  }

  destination="$TRACEDIR/$filename"
  if [[ -f "$destination" ]]; then
    actual_md5="$(md5_file "$destination")"
    if [[ "$actual_md5" != "$expected_md5" ]]; then
      echo "error: checksum mismatch for $destination" >&2
      echo "       expected $expected_md5, found $actual_md5" >&2
      exit 1
    fi
    echo "verified $trace: $filename"
  else
    if [[ "$VERIFY_ONLY" -eq 1 ]]; then
      echo "error: missing trace $destination" >&2
      exit 1
    fi
    partial="$destination.partial"
    echo "downloading $trace: $filename"
    curl --fail --location --retry 3 --continue-at - --output "$partial" "$url"
    actual_md5="$(md5_file "$partial")"
    if [[ "$actual_md5" != "$expected_md5" ]]; then
      echo "error: checksum mismatch for downloaded $filename" >&2
      echo "       expected $expected_md5, found $actual_md5" >&2
      exit 1
    fi
    mv "$partial" "$destination"
    echo "verified $trace: $filename"
  fi
  checked=$((checked + 1))
done < "$MANIFEST"

if [[ "$checked" -ne 13 ]]; then
  echo "error: expected 13 trace records in $MANIFEST, found $checked" >&2
  exit 1
fi

echo "trace manifest verified ($checked/13)"
