#!/usr/bin/env bash
# Copy preset speaker WAVs from TTS-API-SPRINT3 into this backend.
set -euo pipefail

SRC="${1:-$HOME/Documents/GitHub/TTS-API-SPRINT3/assets/reference_voices}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/assets/reference_voices"

if [[ ! -d "$SRC" ]]; then
  echo "Source not found: $SRC" >&2
  echo "Usage: $0 [path-to-TTS-API-SPRINT3/assets/reference_voices]" >&2
  exit 1
fi

mkdir -p "$DEST"
cp -v "$SRC"/*.wav "$DEST"/
echo "Done. $(ls -1 "$DEST"/*.wav 2>/dev/null | wc -l) WAV files in $DEST"
