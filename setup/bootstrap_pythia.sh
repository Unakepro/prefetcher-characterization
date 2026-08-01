#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/versions.env"

PYTHIA_SRC="${PYTHIA_SRC:-$REPO_ROOT/Pythia}"
BUILD_JOBS="${BUILD_JOBS:-2}"

require_clean_checkout() {
  local checkout="$1"
  if [[ -n "$(git -C "$checkout" status --porcelain --untracked-files=no)" ]]; then
    echo "error: refusing to modify dirty checkout: $checkout" >&2
    exit 1
  fi
}

if [[ ! -e "$PYTHIA_SRC" ]]; then
  git clone "$PYTHIA_REPO" "$PYTHIA_SRC"
elif [[ ! -d "$PYTHIA_SRC/.git" ]]; then
  echo "error: $PYTHIA_SRC exists but is not a Git checkout" >&2
  exit 1
fi

require_clean_checkout "$PYTHIA_SRC"
git -C "$PYTHIA_SRC" fetch origin "$PYTHIA_COMMIT"
git -C "$PYTHIA_SRC" checkout --detach "$PYTHIA_COMMIT"

if [[ ! -e "$PYTHIA_SRC/libbf" ]]; then
  git clone "$LIBBF_REPO" "$PYTHIA_SRC/libbf"
elif [[ ! -d "$PYTHIA_SRC/libbf/.git" ]]; then
  echo "error: $PYTHIA_SRC/libbf exists but is not a Git checkout" >&2
  exit 1
fi

require_clean_checkout "$PYTHIA_SRC/libbf"
git -C "$PYTHIA_SRC/libbf" fetch origin "$LIBBF_COMMIT"
git -C "$PYTHIA_SRC/libbf" checkout --detach "$LIBBF_COMMIT"

cmake -S "$PYTHIA_SRC/libbf" -B "$PYTHIA_SRC/libbf/build" \
  -DCMAKE_BUILD_TYPE=Release
cmake --build "$PYTHIA_SRC/libbf/build" --parallel "$BUILD_JOBS"

PYTHIA_SRC="$PYTHIA_SRC" BUILD_JOBS="$BUILD_JOBS" \
  "$SCRIPT_DIR/build_variants.sh"

echo "Pythia source: $(git -C "$PYTHIA_SRC" rev-parse HEAD)"
echo "libbf source:  $(git -C "$PYTHIA_SRC/libbf" rev-parse HEAD)"
echo "built binaries in $PYTHIA_SRC/bin"
