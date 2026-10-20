#!/bin/sh
# MAKO Assistant @VERSION@ — single-file installer for x86_64 Linux.
# MAKO 助手 @VERSION@ — x86_64 Linux 單一檔案安裝程式。
#
# Installs for the current user only (no root needed):
#   program   ~/.local/share/mako-assistant      (or --prefix DIR)
#   command   ~/.local/bin/mako-assistant
#   menu      ~/.local/share/applications/mako-assistant.desktop
#
#   sh MAKO_Assistant-@VERSION@-x86_64.bin               install or upgrade
#   sh MAKO_Assistant-@VERSION@-x86_64.bin --uninstall   remove the program
#   sh MAKO_Assistant-@VERSION@-x86_64.bin --help
#
# Python and Qt are included. MAKO Renderer itself is NOT included.
set -eu

VERSION="@VERSION@"
PAYLOAD_SHA256="@PAYLOAD_SHA256@"
MARKER=".mako-assistant-install"

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
prefix="$data_home/mako-assistant"
bin_dir="$HOME/.local/bin"
apps_dir="$data_home/applications"
icon_dir="$data_home/icons/hicolor/256x256/apps"
action=install
prefix_given=no

say() { printf '%s\n' "$@"; }
die() { printf '%s\n' "$@" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) action=uninstall ;;
        --prefix) [ $# -ge 2 ] || die "--prefix needs a directory"; prefix="$2"; prefix_given=yes; shift ;;
        --prefix=*) prefix="${1#--prefix=}"; prefix_given=yes ;;
        -h|--help)
            say "MAKO Assistant $VERSION installer / MAKO 助手 $VERSION 安裝程式" "" \
                "  sh $(basename "$0")               install or upgrade / 安裝或升級" \
                "  sh $(basename "$0") --uninstall   remove / 移除" \
                "  --prefix DIR   install the program into DIR (default: $prefix)"
            exit 0 ;;
        *) die "Unknown option / 不明的選項: $1 (see --help)" ;;
    esac
    shift
done

case "$prefix" in /*) ;; *) prefix="$(pwd)/$prefix" ;; esac
prefix="${prefix%/}"
launcher="$bin_dir/mako-assistant"
desktop="$apps_dir/mako-assistant.desktop"
icon="$icon_dir/mako-assistant.png"

# Only ever delete a directory that this installer created (or an older
# source install made by install.sh, which lives in the same place).
ours() {
    [ -f "$1/$MARKER" ] && return 0
    [ -d "$1/mako_assistant" ] && [ -f "$1/mako-assistant" ] && return 0
    return 1
}

refresh_menus() {
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$data_home/icons/hicolor" >/dev/null 2>&1 || true
}

if [ "$action" = uninstall ]; then
    removed=no
    # Without --prefix, remove whatever the launcher points at.
    if [ "$prefix_given" = no ] && [ -f "$launcher" ] && grep -q "mako-assistant-launcher" "$launcher" 2>/dev/null; then
        installed=$(sed -n 's|^exec "\(.*\)/AppRun".*|\1|p' "$launcher")
        [ -n "$installed" ] && prefix="$installed"
    fi
    if [ -d "$prefix" ]; then
        ours "$prefix" || die "$prefix was not created by this installer; nothing removed." \
                              "$prefix 不是這個安裝程式建立的，沒有移除任何檔案。"
        rm -rf "$prefix"; removed=yes
    fi
    if [ -f "$launcher" ] && grep -q "mako-assistant-launcher" "$launcher" 2>/dev/null; then rm -f "$launcher"; fi
    if [ -f "$desktop" ] && grep -q "X-MAKO-Assistant-Installer=true" "$desktop" 2>/dev/null; then rm -f "$desktop"; fi
    [ -f "$icon" ] && rm -f "$icon"
    refresh_menus
    if [ "$removed" = yes ]; then
        say "MAKO Assistant was removed. Your settings in ~/.config/mako-assistant and MAKO Renderer's settings were kept." \
            "已移除 MAKO 助手。~/.config/mako-assistant 中的設定與 MAKO Renderer 的設定都已保留。"
    else
        say "MAKO Assistant is not installed in $prefix." "MAKO 助手沒有安裝在 $prefix。"
    fi
    exit 0
fi

[ "$(uname -m)" = x86_64 ] || die "This installer is for x86_64 only. / 此安裝程式只支援 x86_64。"
[ "$(id -u)" -ne 0 ] || say "Note: you are running as root; MAKO Assistant will be installed for root only." \
                            "注意：目前以 root 執行，MAKO 助手只會安裝給 root 使用。請改用一般使用者執行。"
for tool in tar xz tail; do
    command -v "$tool" >/dev/null 2>&1 || die "Missing '$tool' / 缺少 $tool"
done

if [ -e "$prefix" ] && ! ours "$prefix"; then
    if [ -n "$(ls -A "$prefix" 2>/dev/null)" ]; then
        die "$prefix already exists and was not created by this installer. Use --prefix to pick another folder." \
            "$prefix 已存在且不是這個安裝程式建立的，請用 --prefix 指定其他資料夾。"
    fi
fi

payload_line=$(awk '/^__MAKO_ASSISTANT_PAYLOAD__$/ { print NR + 1; exit }' "$0")
[ -n "$payload_line" ] || die "The installer file is damaged. / 安裝檔已損毀。"

if command -v sha256sum >/dev/null 2>&1; then
    actual=$(tail -n +"$payload_line" "$0" | sha256sum | cut -d' ' -f1)
    [ "$actual" = "$PAYLOAD_SHA256" ] || die "The installer file is damaged or incomplete (checksum mismatch); download it again." \
                                             "安裝檔已損毀或下載不完整（檢查碼不符），請重新下載。"
fi

say "Installing MAKO Assistant $VERSION / 正在安裝 MAKO 助手 $VERSION …"
parent=$(dirname "$prefix")
mkdir -p "$parent" "$bin_dir" "$apps_dir" "$icon_dir"
staging="$prefix.new.$$"
rm -rf "$staging"
mkdir -p "$staging"
trap 'rm -rf "$staging"' EXIT INT TERM
tail -n +"$payload_line" "$0" | xz -dc | tar -x -C "$staging"
: > "$staging/$MARKER"

# Replace any previous version only after the new one is fully unpacked.
if [ -d "$prefix" ]; then
    old="$prefix.old.$$"
    mv "$prefix" "$old"
    mv "$staging" "$prefix"
    rm -rf "$old"
else
    mv "$staging" "$prefix"
fi
trap - EXIT INT TERM

[ -L "$launcher" ] && rm -f "$launcher"   # install.sh made a symlink here
cat > "$launcher" <<LAUNCHER
#!/bin/sh
# mako-assistant-launcher (created by the MAKO Assistant installer)
exec "$prefix/AppRun" "\$@"
LAUNCHER
chmod 755 "$launcher"

cp "$prefix/mako-assistant.png" "$icon"
cat > "$desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=MAKO 助手
Name[en]=MAKO Assistant
Comment=為 Steam 遊戲安裝或移除 MAKO Renderer 補幀 (Mako FG)
Comment[en]=Install or remove MAKO Renderer frame generation for Steam games
Exec="$launcher"
Icon=mako-assistant
Terminal=false
Categories=Game;
StartupWMClass=mako-assistant
X-MAKO-Assistant-Installer=true
DESKTOP
refresh_menus

if QT_QPA_PLATFORM=offscreen "$prefix/AppRun" --self-test >/dev/null 2>&1; then
    check="ok"
else
    check="failed"
fi

say "" "Installed MAKO Assistant $VERSION / 已安裝 MAKO 助手 $VERSION" \
    "  Open it from the application menu, or run: mako-assistant" \
    "  從應用程式選單開啟，或執行：mako-assistant" \
    "  Remove / 移除:  sh $(basename "$0") --uninstall"
case ":$PATH:" in *":$bin_dir:"*) ;; *)
    say "  Note: $bin_dir is not in your PATH; use the menu entry or $launcher." \
        "  注意：$bin_dir 不在 PATH 中，請用選單或 $launcher 開啟。" ;;
esac
if [ "$check" != ok ]; then
    say "  Warning: the self-test failed. Run '$launcher --self-test' to see why." \
        "  警告：自我檢查失敗，可執行「$launcher --self-test」查看原因。"
fi
say "  MAKO Renderer is not included: install it and open MAKO UI once before use." \
    "  不包含 MAKO Renderer：使用前請先安裝 MAKO Renderer 並開啟一次 MAKO UI。"
exit 0
__MAKO_ASSISTANT_PAYLOAD__
