#!/usr/bin/env bash
# Install MAKO 助手 for the current user: ~/.local/share/mako-assistant,
# a `mako-assistant` command in ~/.local/bin and an application menu entry.
set -euo pipefail
src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${XDG_DATA_HOME:-$HOME/.local/share}/mako-assistant"
bin="$HOME/.local/bin"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

python3 -c 'import PyQt6.QtWidgets' 2>/dev/null || {
    echo "需要 PyQt6：sudo pacman -S python-pyqt6" >&2; exit 1; }

mkdir -p "$dest" "$bin" "$apps"
rm -rf "$dest/mako_assistant"
cp -r "$src/mako_assistant" "$dest/"
find "$dest/mako_assistant" -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$src/mako-assistant" "$dest/mako-assistant"
ln -sf "$dest/mako-assistant" "$bin/mako-assistant"

cat > "$apps/mako-assistant.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=MAKO 助手
Name[en]=MAKO Assistant
Comment=為 Steam 遊戲安裝或移除 MAKO Renderer 補幀 (Mako FG)
Comment[en]=Install or remove MAKO Renderer frame generation for Steam games
Exec=$bin/mako-assistant
Icon=applications-games
Terminal=false
Categories=Game;
StartupWMClass=mako-assistant
DESKTOP
update-desktop-database "$apps" >/dev/null 2>&1 || true
echo "已安裝 MAKO 助手：執行 mako-assistant 或從應用程式選單開啟。"
