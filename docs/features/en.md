# MAKO Assistant — Feature Guide

**English** · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

**MAKO Assistant** is a graphical Linux desktop tool that turns **MAKO Renderer frame generation (Mako FG)** on or off for your Steam games with one click, without editing any config files by hand.

## Who it is for

On a Steam Deck in Gaming Mode, MAKO has a Decky plugin that you can use in-game. On a **regular Linux desktop or laptop** (for example Arch, Fedora or Ubuntu with KDE Plasma or GNOME), getting a game to use MAKO usually means doing all of this by hand:

1. Add `~/.local/bin/mako-launch %command%` to the game's Steam launch options (Properties → Launch Options) without breaking the options already there.
2. Find the name of the program the game **actually runs** (many games start a launcher first, and Unreal Engine games run a `*-Shipping.exe`).
3. Create a game profile in the MAKO settings and fill in the right matched processes (`active_in`).
4. Do it all again when a game update changes the executable's path or name.
5. Start the game and still not be sure whether frame generation is actually working.

MAKO Assistant turns these steps into one button, and while a game is running it shows which MAKO features are **actually** active.

## Before you start

> ⚠ **MAKO Assistant does not include MAKO Renderer and will not install it for you.** It only manages MAKO's settings.

Do these first:

1. **Install MAKO Renderer (standalone)** by following MAKO's own installation instructions. After installing, `~/.local/bin/mako-launch` should exist.
2. **Open MAKO UI once** to create the default settings. This creates `~/.config/mako-render/conf.toml` and the default profile `mako`. Every game profile MAKO Assistant creates is a copy of this default profile.
3. **Install Steam.** The native package (`~/.local/share/Steam`, `~/.steam`), Flatpak and Snap versions are supported.

Make sure all of the above is done and MAKO itself works before you install Mako FG for a game with MAKO Assistant.

Optional: **Decky Loader.** With it installed, launch options can be applied live while Steam is running, without closing Steam (see "How launch options are written" below).

## Features

### 1. Automatic Steam library scan

- On first start it scans **all** your Steam libraries (including libraries on other drives). After that you can click "⟳ Rescan Steam games".
- Tools such as Proton and the Steam Linux Runtime are filtered out, so only games are listed.
- Game names are shown in Steam's official localized name for your interface language (for example "巫師3：狂獵" in Traditional Chinese) and sorted the way that language expects.
- Each game shows its cover art, its current launch options, its MAKO profile and the detected game executable paths.

### 2. One-click "Install Mako FG"

When you click "Install Mako FG", the tool:

- **Adds the launch option** `~/.local/bin/mako-launch %command%` to the game's Steam launch options and **keeps what was already there**. For example, `FOO=1 %command% -dx11` becomes `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Detects the real game executable** from Steam's app information. It handles launchers (it looks for the actual game program in the install folder instead) and Unreal Engine `*-Shipping.exe` files, and skips common helper programs.
- **Creates a MAKO game profile**: it copies the default profile `mako` into a profile of the game's own in `conf.toml` and writes MAKO's profile metadata. **MAKO UI and the Decky plugin both see this profile and can edit it directly.**
- **Prevents duplicate matches**: if the default profile `mako` also matches this game's executable, the executable is removed from `mako`, so the game uses only its own profile. If another game's profile matches the same executable, you get a warning, but nothing is changed automatically.

### 3. How launch options are written

Steam reads launch options only when it starts, and overwrites its config file when it exits. So that Steam does not overwrite your change, MAKO Assistant picks the write method based on Steam's state, and shows that state in the window:

| Steam state | Write method |
|---|---|
| Not running | Edits Steam's `localconfig.vdf` directly (after making a backup) |
| Running, and the Steam client can be reached (needs Decky Loader) | Applies the change live through the Steam client, with no Steam restart |
| Running, but the client cannot be reached | Asks whether to close Steam → applies the change → restarts Steam |

### 4. Remove

- "Remove" only takes `mako-launch` out of the launch options and leaves your other options as they were.
- The game's MAKO settings are **kept by default**, so you can reuse them if you install again later. Tick "Also remove the game's MAKO Renderer settings" to delete them as well.

### 5. Import existing settings

If you added `mako-launch` to a game by hand before, that game shows an "Import settings" button. Clicking it creates the game's MAKO profile and includes the game in automatic path updates from then on.

### 6. Automatic path updates after game updates

- On every rescan, the tool detects the executables again for games **installed through this tool**. If a game update moved or renamed its executable, the MAKO matched processes are updated automatically, and the change is listed in the log area.
- Matched processes you **added by hand** in MAKO UI are kept.
- If you deleted a game's profile in MAKO UI, the tool respects that and does not recreate it.
- If a library is temporarily offline (for example an external drive that is not connected), those games' settings are left unchanged.

### 7. Launch games from the list

Every row has a "▶ Launch" button that starts the game through Steam. While the game is running, the button shows "Running".

### 8. Live view of the MAKO features actually in use

The "Live MAKO features" column refreshes every 3 seconds. It shows what MAKO has **actually applied** inside the game, not what the config file says:

- **Frame generation**: a fixed multiplier (for example ×2) or adaptive mode (target FPS and maximum multiplier), the Flow scale and performance mode.
- **Scaling**: the scaling method and resolution (for example 1280×720 → 2560×1440), and supersampling.
- **Other layers**: vkBasalt, Zink, ALSA audio.
- **Pending changes**, such as "game restart required" or "swapchain rebuild required", and any errors MAKO reports.

If a game has Mako FG installed but MAKO is not actually loaded, that is shown too, so you can track down the problem.

### 9. Overlay when a game starts

If MAKO Assistant is open when you start a game, as soon as it detects MAKO working in the game it shows the active MAKO features in the bottom-right corner for about 10 seconds, then fades out:

- It appears once per launch, never takes keyboard or mouse focus, and mouse clicks pass through it.
- It can appear on top of fullscreen Proton games.
- If a game with Mako FG installed still has not loaded MAKO 90 seconds after starting, a warning is shown instead.
- You can turn it off with the "Overlay on game start" checkbox in the toolbar.

### 10. Search and filters

- Search by game name (in any language) or by App ID.
- Filters: all games, Mako FG installed, Mako FG not installed, MAKO settings only, running.

### 11. Twelve interface languages

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

On first start the language follows your system language. You can change it at the top right at any time; the change takes effect immediately and is remembered.

### 12. Built to be safe

- `conf.toml` and Steam's `localconfig.vdf` are backed up (`*.mako-assistant.bak`) before every change.
- After writing `conf.toml`, the tool checks it with `mako-cli validate`. If MAKO rejects it, the original file is restored automatically.
- `localconfig.vdf` is never edited directly while Steam is running.
- When you click "Install Mako FG", the tool first checks that MAKO Renderer is installed (`~/.local/bin/mako-launch` exists) and that MAKO UI has created its settings. If either is missing, nothing is changed, and you are told to install MAKO first.

## Installing MAKO Assistant

**AppImage (recommended)**: Python and Qt are included, so nothing else needs to be installed.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**From source**: requires Python 3.11 or later and PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # run directly
./install.sh        # install to ~/.local/share/mako-assistant and add an application menu entry
```

## Known limitations

- **The overlay does not appear in Steam Deck Gaming Mode (gamescope).** On a Steam Deck, use MAKO's Decky plugin instead.
- Games running in native Wayland exclusive fullscreen may cover the overlay.
- Live launch-option changes only work through the Steam client port that Decky Loader opens (8080). Without Decky, close Steam before applying, or let the tool close and restart Steam for you.
- The "features actually in use" view and the MAKO profile metadata are read in the formats of the current MAKO version. After a major MAKO or Steam update they may temporarily not show (you see "—"), but installing and removing keep working.
- In Thai, Vietnamese, Malay and Hindi, right-click menus are in English (Qt has no official translations for these languages). Steam has no Malay or Hindi game names, so these two languages always show the original names.
- Only the most recent backup is kept.

## Where data is stored

| Location | Contents |
|---|---|
| `~/.config/mako-assistant/state.json` | MAKO Assistant's own state: game list cache, games installed through this tool, interface language, overlay setting |
| `~/.config/mako-render/conf.toml` | MAKO Renderer settings (game profiles) |
| `~/.config/mako-render/profile-metadata.json` | MAKO profile metadata (game names, Steam App IDs) |
| `<Steam>/userdata/<user ID>/config/localconfig.vdf` | Steam launch options |
