"""Work out which process names MAKO should match for an installed game.

Sources, in order of trust:
1. The launch entries in Steam's appinfo (what Steam actually starts).
2. Unreal Engine ``*-Shipping.exe`` binaries, which the launch stub spawns.
3. When the launch entry is only a launcher, the largest real executables in
   the install directory (e.g. Witcher 3: redprelauncher.exe -> witcher3.exe).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

# Mirrors the MAKO Decky plugin's helper list so we never match shared
# processes such as Wine services or Steam itself.
_HELPER_NAMES = {
    "bash", "bwrap", "conhost.exe", "explorer.exe", "flatpak", "gameoverlayui",
    "gamescope", "mako-run", "ntoskrnl.exe", "plugplay.exe", "pressure-vessel-wrap",
    "proton", "pv-adverb", "pv-bwrap", "reaper", "rpcss.exe", "services.exe", "sh",
    "srt-bwrap", "steam", "steam.exe", "steam-runtime-launch-client", "steamwebhelper",
    "svchost.exe", "tabtip.exe", "winedevice.exe", "wine", "wine64", "wineboot.exe",
    "winemenubuilder.exe", "wine-preloader", "wine64-preloader", "wineserver", "xalia.exe",
}
_NON_GAME_LAUNCH_TYPES = {"config", "editor", "server", "manual", "othervr", "vr"}
_SCRIPT_SUFFIXES = (".sh", ".bat", ".cmd", ".py", ".url", ".lnk", ".txt", ".html")
_LAUNCHER_HINT = re.compile(r"launch|prelaunch|bootstrap|starter|start_protected", re.I)
_JUNK_EXE = re.compile(
    r"unins|setup|install|redist|vcredist|vc_redist|dxsetup|directx|dotnet|"
    r"crash|report|uploader|helper|update|patch|config|settings|benchmark|"
    r"easyanticheat|eac_|battleye|be_service|launcher|cefprocess|webhelper|"
    r"unitycrashhandler|ue4prereq|prereq|touchup|cleanup|quicksfv|dump",
    re.I,
)
_SKIP_DIRS = re.compile(r"^(_commonredist|redist|redistributables?|directx|vcredist|"
                        r"support|installers?|easyanticheat|battleye|__installer|"
                        r"engine[/\\]extras)$", re.I)
_MIN_GAME_EXE_BYTES = 8 * 1024 * 1024
_SCAN_MAX_DEPTH = 5
_SCAN_MAX_FILES = 20000


def is_matchable(name: str) -> bool:
    lowered = name.lower()
    if not name or lowered in _HELPER_NAMES or name.startswith("."):
        return False
    if lowered.startswith(("pressure-vessel", "steam-runtime-")):
        return False
    if re.fullmatch(r"python(\d+(\.\d+)*)?", lowered):
        return False
    return not lowered.endswith((".so", ".dll") + _SCRIPT_SUFFIXES)


def _resolve_case_insensitive(root: Path, relative: str) -> Path | None:
    """Resolve a Windows-style relative path on a case-sensitive filesystem."""
    current = root
    for part in re.split(r"[\\/]+", relative.strip()):
        if part in ("", "."):
            continue
        candidate = current / part
        if candidate.exists():
            current = candidate
            continue
        try:
            match = next(
                (entry for entry in current.iterdir() if entry.name.lower() == part.lower()),
                None,
            )
        except OSError:
            return None
        if match is None:
            return None
        current = match
    return current if current.is_file() else None


def _launch_entries(appinfo: dict[str, Any]) -> list[dict[str, Any]]:
    launch = (appinfo.get("config") or {}).get("launch") or {}
    entries = [entry for _, entry in sorted(launch.items(), key=lambda kv: str(kv[0]))
               if isinstance(entry, dict)]
    return [
        entry for entry in entries
        if str(entry.get("type", "default")).lower() not in _NON_GAME_LAUNCH_TYPES
        and not str(entry.get("executable", "")).startswith("steam://")
        and not str((entry.get("config") or {}).get("betakey", ""))
    ]


def _walk_executables(root: Path, suffix_filter) -> Iterable[Path]:
    seen = 0
    base_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).parts) - base_depth
        dirnames[:] = [d for d in dirnames if not _SKIP_DIRS.match(d)] if depth < _SCAN_MAX_DEPTH else []
        for filename in filenames:
            seen += 1
            if seen > _SCAN_MAX_FILES:
                return
            if suffix_filter(filename):
                yield Path(dirpath) / filename


def _is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def _largest_game_binaries(install_dir: Path, windows: bool) -> list[Path]:
    if windows:
        found = _walk_executables(install_dir, lambda name: name.lower().endswith(".exe"))
    else:
        found = (path for path in _walk_executables(install_dir, lambda name: "." not in name)
                 if os.access(path, os.X_OK) and _is_elf(path))
    candidates = []
    for path in found:
        if _JUNK_EXE.search(path.name):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size >= _MIN_GAME_EXE_BYTES:
            candidates.append((size, path))
    candidates.sort(reverse=True)
    if not candidates:
        return []
    # Keep near-equal siblings (e.g. witcher3.exe in x64 and x64_dx12).
    top_size = candidates[0][0]
    return [path for size, path in candidates if size >= top_size * 0.6][:4]


def detect_executables(install_dir: Path, appinfo: dict[str, Any] | None) -> list[Path]:
    """Return absolute paths of the binaries that render the game."""
    install_dir = Path(install_dir)
    if not install_dir.is_dir():
        return []

    launch_paths: list[Path] = []
    for entry in _launch_entries(appinfo or {}):
        resolved = _resolve_case_insensitive(install_dir, str(entry.get("executable", "")))
        if resolved is not None and resolved not in launch_paths:
            launch_paths.append(resolved)

    windows = (not launch_paths and any(install_dir.glob("**/*.exe"))) or any(
        path.suffix.lower() == ".exe" for path in launch_paths
    )

    shipping = [
        path for path in _walk_executables(
            install_dir, lambda name: re.search(r"-Win(64|GDK)-Shipping\.exe$", name, re.I)
        )
    ]

    real_launch = [path for path in launch_paths
                   if is_matchable(path.name) and not _LAUNCHER_HINT.search(path.stem)]
    result: list[Path] = list(real_launch)
    for path in shipping:
        if path not in result:
            result.append(path)

    if not result:
        result = _largest_game_binaries(install_dir, windows)
        if not result:
            result = [path for path in launch_paths if is_matchable(path.name)]
    return result


def process_names(paths: Iterable[Path]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for path in paths:
        name = Path(path).name
        if is_matchable(name) and name.casefold() not in seen:
            names.append(name)
            seen.add(name.casefold())
    return names
