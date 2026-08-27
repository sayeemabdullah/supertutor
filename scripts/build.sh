#!/usr/bin/env bash
# Build supertutor.skill deterministically.
#
# zip embeds file mtimes, so a naive rebuild produces different bytes on every
# run even when nothing changed — which would make CI commit a phantom change
# on every push, and each bot push would retrigger the build. Normalizing
# timestamps and sorting the file list makes identical content produce an
# identical archive, so "did this actually change?" is just a byte comparison.
set -euo pipefail

# Both matter for byte-identical output across machines:
#   LC_ALL=C  - sort order is locale-dependent. Under macOS's UTF-8 collation
#               "references/" sorts before "SKILL.md"; under C it's the reverse,
#               so a mac build and a Linux build disagreed on entry order.
#   TZ=UTC    - zip stores DOS-local timestamps; a fixed zone keeps them stable.
export LC_ALL=C TZ=UTC

cd "$(dirname "$0")/.."
OUT="$(pwd)/${1:-supertutor.skill}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp -R supertutor "$TMP/supertutor"
find "$TMP/supertutor" -name '.DS_Store' -delete
find "$TMP/supertutor" -name '__pycache__' -type d -prune -exec rm -rf {} +
# 1980-01-01 is the earliest timestamp the zip format can represent.
find "$TMP/supertutor" -exec touch -t 198001010000 {} +

rm -f "$OUT"
( cd "$TMP" && find supertutor | sort | zip -qX "$OUT" -@ )

# Claude.ai rejects an archive whose paths don't start with supertutor/
if unzip -Z1 "$OUT" | grep -qv '^supertutor/'; then
  echo "error: archive contains paths outside supertutor/" >&2
  unzip -Z1 "$OUT" | grep -v '^supertutor/' >&2
  exit 1
fi

echo "built $(basename "$OUT") — $(unzip -Z1 "$OUT" | wc -l | tr -d ' ') entries, $(du -h "$OUT" | cut -f1 | tr -d ' ')"
