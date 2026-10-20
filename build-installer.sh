#!/usr/bin/env bash
# Build dist/MAKO_Assistant-<version>-x86_64.bin: one self-extracting file that
# installs MAKO Assistant for the current user (see packaging/installer-header.sh).
#
# It packs the same AppDir as the AppImage (portable Python + trimmed PyQt6),
# so run ./build-appimage.sh first; this script does that itself when needed.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
build="$here/build"
appdir="$build/AppDir"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$here/mako_assistant/__init__.py")"
output="$here/dist/MAKO_Assistant-${version}-x86_64.bin"
payload="$build/installer-payload.tar.xz"

appdir_version() {
    sed -n 's/^__version__ = "\(.*\)"/\1/p' \
        "$appdir"/usr/python/lib/python3*/site-packages/mako_assistant/__init__.py 2>/dev/null || true
}
if [[ ! -x "$appdir/AppRun" || "$(appdir_version)" != "$version" ]]; then
    echo "==> 先建置 AppDir（./build-appimage.sh）"
    "$here/build-appimage.sh"
fi
# The AppDir must hold exactly the current sources.
if ! diff -rq -x __pycache__ "$here/mako_assistant" \
        "$(dirname "$appdir"/usr/python/lib/python3*/site-packages/mako_assistant/__init__.py)" >/dev/null; then
    echo "==> AppDir 與原始碼不同，重新建置"
    "$here/build-appimage.sh"
fi

echo "==> 壓縮安裝內容"
mkdir -p "$here/dist"
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2000-01-01 00:00Z' \
    -C "$appdir" -cf - . | xz -9 -T0 > "$payload"
sha="$(sha256sum "$payload" | cut -d' ' -f1)"

echo "==> 產生安裝檔"
header="$here/packaging/installer-header.sh"
[[ "$(tail -n 1 "$header")" == "__MAKO_ASSISTANT_PAYLOAD__" ]] || {
    echo "錯誤：$header 最後一行必須是 __MAKO_ASSISTANT_PAYLOAD__" >&2; exit 1; }
rm -f "$output"
sed -e "s/@VERSION@/$version/g" -e "s/@PAYLOAD_SHA256@/$sha/" "$header" > "$output"
cat "$payload" >> "$output"
chmod 755 "$output"
rm -f "$payload"

echo "==> 檢查是否含有建置機器的路徑"
for leak in "$HOME" "$here"; do
    if head -n 200 "$output" | grep -a -q -F "$leak"; then
        echo "錯誤：安裝檔內含建置機器的路徑 $leak" >&2; exit 1
    fi
done

notes="$here/dist/MAKO_Assistant-${version}-README.md"
if [[ -f "$notes" ]]; then
    echo "==> 在更新說明加上檢查碼"
    "$here/packaging/add-checksum.sh" "$notes" "$output"
fi

echo
echo "完成：$output ($(du -h "$output" | cut -f1))"
