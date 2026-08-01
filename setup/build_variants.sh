#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHIA_SRC="${PYTHIA_SRC:-$REPO_ROOT/Pythia}"
BUILD_JOBS="${BUILD_JOBS:-2}"
BASE_BINARY=perceptron-multi-multi-no-ship-1core
CHAMPSIM_HEADER="$PYTHIA_SRC/inc/champsim.h"
CHAMPSIM_HEADER_BACKUP="$PYTHIA_SRC/inc/champsim.h.bak"
CACHE_HEADER="$PYTHIA_SRC/inc/cache.h"

for required in \
  "$PYTHIA_SRC/build_champsim.sh" \
  "$PYTHIA_SRC/libbf/build/lib/libbf.a" \
  "$CHAMPSIM_HEADER" \
  "$CACHE_HEADER"; do
  [[ -e "$required" ]] || {
    echo "error: missing prerequisite $required" >&2
    echo "run setup/bootstrap_pythia.sh first" >&2
    exit 1
  }
done

if [[ -d "$PYTHIA_SRC/.git" ]] &&
   [[ -n "$(git -C "$PYTHIA_SRC" status --porcelain --untracked-files=no)" ]]; then
  echo "error: refusing to build from a dirty Pythia checkout: $PYTHIA_SRC" >&2
  exit 1
fi

variant_tmp="$(mktemp -d)"
cp "$CHAMPSIM_HEADER" "$variant_tmp/champsim.h"
cp "$CACHE_HEADER" "$variant_tmp/cache.h"
if [[ -f "$CHAMPSIM_HEADER_BACKUP" ]]; then
  cp "$CHAMPSIM_HEADER_BACKUP" "$variant_tmp/champsim.h.bak"
fi

restore_sources() {
  cp "$variant_tmp/champsim.h" "$CHAMPSIM_HEADER"
  cp "$variant_tmp/cache.h" "$CACHE_HEADER"
  if [[ -f "$variant_tmp/champsim.h.bak" ]]; then
    cp "$variant_tmp/champsim.h.bak" "$CHAMPSIM_HEADER_BACKUP"
  fi
}

cleanup() {
  restore_sources
  rm -r -- "$variant_tmp"
}
trap cleanup EXIT INT TERM

set_channels() {
  local channels="$1" log2_channels="$2"
  perl -0pi -e \
    "s/^#define DRAM_CHANNELS [^\\n]*/#define DRAM_CHANNELS $channels/m; s/^#define LOG2_DRAM_CHANNELS [^\\n]*/#define LOG2_DRAM_CHANNELS $log2_channels/m" \
    "$CHAMPSIM_HEADER"
}

set_llc_sets() {
  local sets_per_core="$1"
  perl -0pi -e \
    "s/^#define LLC_SET [^\\n]*/#define LLC_SET NUM_CPUS*$sets_per_core/m" \
    "$CACHE_HEADER"
}

build_one() {
  local label="$1" channels="$2" log2_channels="$3" sets_per_core="$4"
  restore_sources
  set_channels "$channels" "$log2_channels"
  set_llc_sets "$sets_per_core"
  echo "building $label: channels=$channels, LLC sets/core=$sets_per_core"
  (
    cd "$PYTHIA_SRC"
    MAKEFLAGS="-j$BUILD_JOBS" TERM="${TERM:-dumb}" \
      ./build_champsim.sh multi multi no 1
  )
  mv "$PYTHIA_SRC/bin/$BASE_BINARY" "$variant_tmp/$label"
}

build_one default 1 0 2048
build_one 2ch     2 1 2048
build_one 1MB     1 0 1024
build_one 4MB     1 0 4096

restore_sources
install -m 0755 "$variant_tmp/default" "$PYTHIA_SRC/bin/$BASE_BINARY"
install -m 0755 "$variant_tmp/2ch" "$PYTHIA_SRC/bin/$BASE_BINARY-2ch"
install -m 0755 "$variant_tmp/1MB" "$PYTHIA_SRC/bin/$BASE_BINARY-1MB"
install -m 0755 "$variant_tmp/4MB" "$PYTHIA_SRC/bin/$BASE_BINARY-4MB"

if [[ -d "$PYTHIA_SRC/.git" ]] &&
   [[ -n "$(git -C "$PYTHIA_SRC" status --porcelain --untracked-files=no)" ]]; then
  echo "error: build did not restore the Pythia checkout to a clean state" >&2
  git -C "$PYTHIA_SRC" status --short >&2
  exit 1
fi

echo "built simulator variants:"
for binary in \
  "$PYTHIA_SRC/bin/$BASE_BINARY" \
  "$PYTHIA_SRC/bin/$BASE_BINARY-2ch" \
  "$PYTHIA_SRC/bin/$BASE_BINARY-1MB" \
  "$PYTHIA_SRC/bin/$BASE_BINARY-4MB"; do
  printf '  %s\n' "$binary"
done
