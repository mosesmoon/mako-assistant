#!/usr/bin/env bash
# add-checksum.sh <release notes> <file>: list <file> and its SHA-256 at the end
# of the release notes that ship next to it (replacing an older line for it).
set -euo pipefail
notes="$1"; file="$2"
[[ -f "$notes" ]] || { echo "找不到更新說明 $notes（請先執行 ./build-appimage.sh）" >&2; exit 1; }
name="$(basename "$file")"
sha="$(sha256sum "$file" | cut -d' ' -f1)"
if ! grep -q '^## Downloads / 下載檔案$' "$notes"; then
    printf '\n---\n\n## Downloads / 下載檔案\n\n| File / 檔案 | SHA-256 |\n|---|---|\n' >> "$notes"
fi
grep -v -F "| \`$name\` |" "$notes" > "$notes.tmp" || true
printf '| `%s` | `%s` |\n' "$name" "$sha" >> "$notes.tmp"
mv "$notes.tmp" "$notes"
