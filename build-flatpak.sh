#!/usr/bin/env bash
# Build dist/MAKO_Assistant-<version>-x86_64.flatpak, a single-file Flatpak bundle.
#
# Needs flatpak and flatpak-builder. The KDE SDK and the PyQt BaseApp are
# downloaded from Flathub on the first build (about 1 GB). Users installing the
# bundle get the KDE runtime from Flathub automatically.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app_id="io.github.mosesmoon.MakoAssistant"
manifest="$here/packaging/flatpak/$app_id.yml"
build="$here/build/flatpak"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$here/mako_assistant/__init__.py")"
output="$here/dist/MAKO_Assistant-${version}-x86_64.flatpak"
flathub="https://dl.flathub.org/repo/flathub.flatpakrepo"

for tool in flatpak flatpak-builder; do
    command -v "$tool" >/dev/null || { echo "需要 $tool（例如 sudo pacman -S flatpak-builder）" >&2; exit 1; }
done
grep -q "<release version=\"$version\"" "$here/packaging/flatpak/$app_id.metainfo.xml" || {
    echo "錯誤：$app_id.metainfo.xml 的 <releases> 缺少版本 $version" >&2; exit 1; }

flatpak --user remote-add --if-not-exists flathub "$flathub"

echo "==> 建置 Flatpak"
mkdir -p "$build" "$here/dist"
flatpak-builder --user --install-deps-from=flathub --force-clean --disable-rofiles-fuse \
    --state-dir="$build/state" --repo="$build/repo" \
    --default-branch=stable "$build/app" "$manifest"

echo "==> 打包單一檔案"
rm -f "$output"
flatpak build-bundle --runtime-repo="$flathub" "$build/repo" "$output" "$app_id" stable

echo "==> 檢查是否含有建置機器的路徑"
for leak in "$HOME" "$here"; do
    if grep -r -a -l -F "$leak" "$build/app/files" >/dev/null 2>&1; then
        echo "錯誤：Flatpak 內含建置機器的路徑 $leak：" >&2
        grep -r -a -l -F "$leak" "$build/app/files" | head -5 >&2
        exit 1
    fi
done

notes="$here/dist/MAKO_Assistant-${version}-README.md"
if [[ -f "$notes" ]]; then
    echo "==> 在更新說明加上檢查碼"
    "$here/packaging/add-checksum.sh" "$notes" "$output"
fi

echo
echo "完成：$output ($(du -h "$output" | cut -f1))"
echo "安裝：flatpak install --user $(basename "$output")"
