"""Discover the local Steam installation, its libraries, games and launch options."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import vdf_text
from .appinfo import AppInfoError, read_appinfo

STEAM_ID64_BASE = 76561197960265728

_STEAM_ROOT_CANDIDATES = (
    "~/.local/share/Steam",
    "~/.steam/steam",
    "~/.steam/root",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",
    "~/snap/steam/common/.local/share/Steam",
)

# Shown in Steam's library but never real games.
_TOOL_NAME_PREFIXES = (
    "proton", "steam linux runtime", "steamworks common redistributables",
    "steamvr", "steam audio",
)


@dataclass
class SteamGame:
    app_id: int
    name: str
    install_dir: Path
    library: Path
    app_type: str = "game"
    appinfo: dict = field(default_factory=dict, repr=False)
    # Steam language key (tchinese, japanese, …) -> localized store name.
    names: dict = field(default_factory=dict)

    @property
    def installed(self) -> bool:
        return self.install_dir.is_dir()


class SteamInstallation:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else self.find_root()
        if self.root is None:
            raise FileNotFoundError("Steam installation not found")

    @staticmethod
    def find_root() -> Optional[Path]:
        for candidate in _STEAM_ROOT_CANDIDATES:
            path = Path(os.path.expanduser(candidate))
            if (path / "steamapps").is_dir():
                return path.resolve()
        return None

    # ---- libraries & games -------------------------------------------------

    def library_folders(self) -> list[Path]:
        folders = [self.root]
        config = self.root / "steamapps" / "libraryfolders.vdf"
        try:
            data = vdf_text.loads(config.read_text(encoding="utf-8", errors="replace"))
        except (OSError, vdf_text.VdfError):
            data = {}
        root_map = vdf_text.get_ci(data, "libraryfolders") or {}
        for value in root_map.values():
            path = value.get("path") if isinstance(value, dict) else value
            if isinstance(path, str) and path:
                folders.append(Path(path))
        unique: list[Path] = []
        seen = set()
        for folder in folders:
            try:
                key = folder.resolve()
            except OSError:
                key = folder
            if key not in seen and (folder / "steamapps").is_dir():
                seen.add(key)
                unique.append(folder)
        return unique

    def scan_games(self) -> list[SteamGame]:
        manifests: dict[int, SteamGame] = {}
        for library in self.library_folders():
            steamapps = library / "steamapps"
            for manifest in steamapps.glob("appmanifest_*.acf"):
                try:
                    data = vdf_text.loads(manifest.read_text(encoding="utf-8", errors="replace"))
                except (OSError, vdf_text.VdfError):
                    continue
                state = vdf_text.get_ci(data, "AppState") or {}
                try:
                    app_id = int(state.get("appid", ""))
                except ValueError:
                    continue
                installdir = state.get("installdir") or ""
                if not installdir:
                    continue
                manifests[app_id] = SteamGame(
                    app_id=app_id,
                    name=state.get("name") or str(app_id),
                    install_dir=steamapps / "common" / installdir,
                    library=library,
                )

        try:
            infos = read_appinfo(self.root / "appcache" / "appinfo.vdf", manifests)
        except (OSError, AppInfoError):
            infos = {}

        games = []
        for app_id, game in manifests.items():
            info = infos.get(app_id) or {}
            common = info.get("common") or {}
            game.appinfo = info
            game.app_type = str(common.get("type") or "").lower()
            if common.get("name"):
                game.name = str(common["name"])
            localized = common.get("name_localized")
            if isinstance(localized, dict):
                game.names = {str(k): str(v).strip() for k, v in localized.items()
                              if isinstance(v, str) and v.strip()}
            if game.app_type and game.app_type not in ("game", "demo", "mod"):
                continue
            if not game.app_type and game.name.lower().startswith(_TOOL_NAME_PREFIXES):
                continue
            if not game.installed:
                continue
            games.append(game)
        games.sort(key=lambda g: g.name.casefold())
        return games

    # ---- users & launch options -------------------------------------------

    def active_user_dirs(self) -> list[Path]:
        userdata = self.root / "userdata"
        try:
            users = [d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit() and d.name != "0"]
        except OSError:
            return []
        try:
            login = vdf_text.loads((self.root / "config" / "loginusers.vdf").read_text(
                encoding="utf-8", errors="replace"))
            entries = vdf_text.get_ci(login, "users") or {}
            best = None
            for steam_id, info in entries.items():
                if not isinstance(info, dict) or not steam_id.isdigit():
                    continue
                rank = (info.get("MostRecent") == "1", int(info.get("Timestamp") or 0))
                if best is None or rank > best[0]:
                    best = (rank, int(steam_id) - STEAM_ID64_BASE)
            if best is not None:
                preferred = userdata / str(best[1])
                if preferred.is_dir():
                    return [preferred]
        except (OSError, vdf_text.VdfError, ValueError):
            pass
        return users

    def localconfig_paths(self) -> list[Path]:
        return [d / "config" / "localconfig.vdf" for d in self.active_user_dirs()
                if (d / "config" / "localconfig.vdf").is_file()]

    @staticmethod
    def _apps_node(data: dict, create: bool) -> Optional[dict]:
        node = data
        for key in ("UserLocalConfigStore", "Software", "Valve", "Steam", "apps"):
            child = vdf_text.get_ci(node, key)
            if not isinstance(child, dict):
                if not create:
                    return None
                child = vdf_text.child_ci(node, key)
            node = child
        return node

    def read_launch_options(self) -> dict[int, str]:
        result: dict[int, str] = {}
        for path in self.localconfig_paths():
            try:
                data = vdf_text.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, vdf_text.VdfError):
                continue
            apps = self._apps_node(data, create=False) or {}
            for key, value in apps.items():
                if key.isdigit() and isinstance(value, dict):
                    options = vdf_text.get_ci(value, "LaunchOptions")
                    if isinstance(options, str):
                        result.setdefault(int(key), options)
        return result

    def write_launch_options_offline(self, changes: dict[int, str]) -> None:
        """Edit localconfig.vdf directly. Only valid while Steam is closed."""
        paths = self.localconfig_paths()
        if not paths:
            raise FileNotFoundError("localconfig.vdf not found for any Steam user")
        for path in paths:
            data = vdf_text.loads(path.read_text(encoding="utf-8", errors="replace"))
            apps = self._apps_node(data, create=True)
            for app_id, options in changes.items():
                app = vdf_text.child_ci(apps, str(app_id))
                existing_key = next((k for k in app if k.lower() == "launchoptions"), "LaunchOptions")
                app[existing_key] = options
            backup = path.with_name(path.name + ".mako-assistant.bak")
            shutil.copy2(path, backup)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(vdf_text.dumps(data), encoding="utf-8")
            os.replace(tmp, path)

    def header_image(self, app_id: int) -> Optional[Path]:
        cache = self.root / "appcache" / "librarycache"
        folder = cache / str(app_id)
        for pattern in ("**/library_header*.jpg", "header*.jpg", "**/library_capsule*.jpg"):
            match = next(iter(sorted(folder.glob(pattern))), None) if folder.is_dir() else None
            if match:
                return match
        legacy = cache / f"{app_id}_header.jpg"
        return legacy if legacy.is_file() else None

    # ---- process state ----------------------------------------------------

    def is_running(self) -> bool:
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if (proc / "comm").read_text().strip() != "steam":
                    continue
                exe = os.readlink(proc / "exe")
            except OSError:
                continue
            if exe.endswith("/steam") and "ubuntu12_32" in exe:
                return True
        return False

    def wait_until_closed(self, timeout: float = 60.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_running():
                return True
            time.sleep(0.5)
        return not self.is_running()
