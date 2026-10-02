#!/usr/bin/env bash
# Build MAKO_Assistant-<version>-x86_64.AppImage.
#
# The AppImage bundles a relocatable CPython (python-build-standalone, via uv)
# and PyQt6 wheels, so it runs without any Python/Qt packages on the host.
set -euo pipefail
# Python run during the build must not leave bytecode (it records build paths).
export PYTHONDONTWRITEBYTECODE=1

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
build="$here/build"
appdir="$build/AppDir"
python_version="${PYTHON_VERSION:-3.13}"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$here/mako_assistant/__init__.py")"
output="$here/dist/MAKO_Assistant-${version}-x86_64.AppImage"
release_notes="$here/docs/releases/${version}.md"
notes_output="$here/dist/MAKO_Assistant-${version}-README.md"
appimagetool_url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

command -v uv >/dev/null || { echo "需要 uv：https://docs.astral.sh/uv/" >&2; exit 1; }
# Every release ships with its multilingual release notes.
[[ -f "$release_notes" ]] || {
    echo "錯誤：找不到版本 $version 的更新說明 $release_notes（12 語系），請先撰寫再打包" >&2
    exit 1
}

echo "==> 準備 AppDir"
rm -rf "$appdir"
mkdir -p "$appdir/usr" "$here/dist"

echo "==> 複製可攜式 Python $python_version"
uv python find "$python_version" >/dev/null 2>&1 || uv python install "$python_version"
# uv's install dir is usually a symlink (cpython-3.13-… -> cpython-3.13.14-…);
# resolve it and copy the real tree so nothing is ever written back into it.
python_home="$(readlink -f "$(dirname "$(dirname "$(readlink -f "$(uv python find "$python_version")")")")")"
mkdir -p "$appdir/usr/python"
cp -a "$python_home/." "$appdir/usr/python/"
# uv records its install location in text files such as _sysconfigdata*.py
# (build-time variables only); neutralise it so no build path ships.
grep -rlIF "$python_home" "$appdir/usr/python" 2>/dev/null | while read -r f; do
    sed -i "s|$python_home|/usr/python|g" "$f"
done
py="$appdir/usr/python/bin/python3"
prefix="$("$py" -c 'import sys; print(sys.prefix)')"
if [[ -L "$appdir/usr/python" || "$(readlink -f "$prefix")" != "$(readlink -f "$appdir/usr/python")" ]]; then
    echo "錯誤：打包用 Python 的 prefix ($prefix) 不在 AppDir 內，停止以免修改系統 Python" >&2
    exit 1
fi
site="$("$py" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
# Drop anything the source interpreter had installed (pip etc.).
find "$site" -mindepth 1 -maxdepth 1 ! -name README.txt -exec rm -rf {} +

echo "==> 安裝 PyQt6"
uv pip install --python "$py" --target "$site" --link-mode copy --no-cache PyQt6

echo "==> 複製 MAKO 助手"
cp -r "$here/mako_assistant" "$site/"

echo "==> 精簡體積"
qt="$site/PyQt6/Qt6"
# Only QtCore/QtGui/QtWidgets (+ their platform plugins) are used.
keep_libs='^lib(Qt6(Core|Gui|Widgets|DBus|XcbQpa|WaylandClient|WaylandEglClientHwIntegration|OpenGL|EglFSDeviceIntegration|Svg)|icu|ffi)'
find "$qt/lib" -maxdepth 1 -name 'lib*.so*' | while read -r lib; do
    basename "$lib" | grep -Eq "$keep_libs" || rm -f "$lib"
done
find "$qt/plugins" -mindepth 1 -maxdepth 1 -type d \
    ! -name platforms ! -name platformthemes ! -name imageformats ! -name xcbglintegrations \
    ! -name wayland-shell-integration ! -name wayland-decoration-client \
    ! -name wayland-graphics-integration-client ! -name iconengines ! -name platforminputcontexts \
    -exec rm -rf {} +
rm -rf "$qt/qml" "$qt/qsci"
# Keep Qt's own texts (context menus, dialogs) for the UI languages only.
keep_qm='^qt(base)?_(zh_TW|zh_CN|en|ja|de|fr|es|it|th|vi|ms|hi)\.qm$'
find "$qt/translations" -type f 2>/dev/null | while read -r qm; do
    basename "$qm" | grep -Eq "$keep_qm" || rm -f "$qm"
done
find "$site/PyQt6" -maxdepth 1 -name 'Qt*.abi3.so' \
    ! -name 'QtCore.*' ! -name 'QtGui.*' ! -name 'QtWidgets.*' ! -name 'QtDBus.*' -delete
find "$site/PyQt6" -maxdepth 1 -name '*.pyi' -delete
rm -rf "$appdir/usr/python/lib/python3"*/{test,idlelib,tkinter,turtledemo,ensurepip,lib2to3} \
       "$appdir/usr/python/lib/"{libtcl*,libtk*,tcl*,tk*,itcl*,thread*} \
       "$appdir/usr/python/include" "$appdir/usr/python/share" \
       "$site/pip" "$site/pip-"* "$site/bin"  # bin: PyQt6 dev tools with build-path shebangs
find "$appdir" -name '__pycache__' -prune -exec rm -rf {} +
# Strip the build directory from the recorded source paths.
"$py" -m compileall -q -s "$appdir" -p / "$site/mako_assistant" >/dev/null

echo "==> 寫入 AppRun / desktop / icon"
cat > "$appdir/AppRun" <<'APPRUN'
#!/usr/bin/env bash
here="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH QT_PLUGIN_PATH QML2_IMPORT_PATH
exec "$here/usr/python/bin/python3" -m mako_assistant "$@"
APPRUN
chmod +x "$appdir/AppRun"

cat > "$appdir/mako-assistant.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=MAKO 助手
Name[en]=MAKO Assistant
Comment=為 Steam 遊戲安裝或移除 MAKO Renderer 補幀 (Mako FG)
Comment[en]=Install or remove MAKO Renderer frame generation for Steam games
Exec=mako-assistant
Icon=mako-assistant
Terminal=false
Categories=Game;
StartupWMClass=mako-assistant
DESKTOP
cp "$here/packaging/mako-assistant.png" "$appdir/mako-assistant.png"
ln -sf mako-assistant.png "$appdir/.DirIcon"
mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"
cp "$here/packaging/mako-assistant.png" "$appdir/usr/share/icons/hicolor/256x256/apps/"

echo "==> 自我檢查"
# No bytecode from this run: it would record the build machine's paths.
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen "$appdir/AppRun" --self-test

echo "==> 檢查是否含有建置機器的路徑"
for leak in "$HOME" "$here"; do
    if grep -r -a -l -F "$leak" "$appdir" >/dev/null 2>&1; then
        echo "錯誤：AppDir 內含建置機器的路徑 $leak，停止打包：" >&2
        grep -r -a -l -F "$leak" "$appdir" | head -5 >&2
        exit 1
    fi
done

tool="$build/appimagetool-x86_64.AppImage"
if [[ ! -x "$tool" ]]; then
    echo "==> 下載 appimagetool"
    curl -fL --progress-bar -o "$tool" "$appimagetool_url"
    chmod +x "$tool"
fi

echo "==> 打包 AppImage"
rm -f "$output"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream "$appdir" "$output"

echo "==> 附上更新說明"
{
    cat "$release_notes"
    printf '\n---\n\n`%s`  \nSHA-256: `%s`\n' "$(basename "$output")" "$(sha256sum "$output" | cut -d' ' -f1)"
} > "$notes_output"

echo
echo "完成：$output ($(du -h "$output" | cut -f1))"
echo "      $notes_output"
