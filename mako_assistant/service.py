"""Application logic for MAKO Assistant, independent of the UI toolkit."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import launch_options as lo
from .executables import detect_executables, process_names
from .i18n import localized_name, tr
from .mako_config import MakoConfig
from .steam import SteamGame, SteamInstallation
from .steam_cef import CefError, SteamCef


def state_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "mako-assistant" / "state.json"


class SteamMustCloseError(RuntimeError):
    """Steam runs without a reachable CEF port; localconfig.vdf can't be edited live."""


@dataclass
class GameEntry:
    app_id: int
    name: str
    install_dir: str
    launch_options: str = ""
    has_mako: bool = False
    profile_name: Optional[str] = None
    profile_processes: list[str] = field(default_factory=list)
    managed: bool = False
    executables: list[str] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return localized_name(self.name, self.names)

    def matches(self, query: str) -> bool:
        query = query.casefold()
        return (query in str(self.app_id)
                or any(query in n.casefold() for n in (self.name, *self.names.values())))


@dataclass
class SyncChange:
    app_id: int
    name: str
    before: list[str]
    after: list[str]
    old_paths: list[str] = field(default_factory=list)
    new_paths: list[str] = field(default_factory=list)


class AssistantService:
    def __init__(self, steam_root: Optional[Path] = None,
                 mako_dir: Optional[Path] = None,
                 cef: Optional[SteamCef] = None,
                 state_file: Optional[Path] = None) -> None:
        self._steam_root = steam_root
        self._mako_dir = mako_dir
        self.cef = cef or SteamCef()
        self.state_file = state_file or state_path()
        self.state = self._load_state()

    # ---- state --------------------------------------------------------------

    def _load_state(self) -> dict:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                state.setdefault("managed", {})
                state.setdefault("games", [])
                return state
        except (OSError, ValueError):
            pass
        return {"managed": {}, "games": [], "scanned": False}

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_file)

    @property
    def has_scanned(self) -> bool:
        return bool(self.state.get("scanned"))

    def steam(self) -> SteamInstallation:
        return SteamInstallation(self._steam_root)

    def mako(self) -> MakoConfig:
        config = MakoConfig(self._mako_dir)
        if not config.exists():
            raise FileNotFoundError(tr("svc_no_conf", path=config.conf_path))
        config.load()
        return config

    # ---- launch options -------------------------------------------------------

    def _live_launch_options(self, app_ids: list[int]) -> Optional[dict[int, str]]:
        if not app_ids:
            return {}
        script = """(async () => {
  const ids = %s; const out = {};
  await Promise.all(ids.map(id => new Promise(resolve => {
    const d = appDetailsStore.GetAppDetails(id);
    if (d && d.strLaunchOptions !== undefined) { out[id] = d.strLaunchOptions; return resolve(); }
    let done = false, handle;
    const finish = v => { if (done) return; done = true;
      try { handle && handle.unregister(); } catch (e) {}
      if (v !== undefined) out[id] = v; resolve(); };
    handle = SteamClient.Apps.RegisterForAppDetails(id, dd => finish(dd && dd.strLaunchOptions));
    setTimeout(() => finish(undefined), 4000);
  })));
  return JSON.stringify(out);
})()""" % json.dumps(app_ids)
        try:
            raw = self.cef.evaluate(script)
            return {int(k): v for k, v in json.loads(raw).items()}
        except (CefError, OSError, ValueError, TypeError):
            return None

    def read_launch_options(self, steam: SteamInstallation, app_ids: list[int]) -> dict[int, str]:
        on_disk = steam.read_launch_options()
        if steam.is_running():
            live = self._live_launch_options(app_ids)
            if live is not None:
                on_disk.update(live)
        return on_disk

    def apply_launch_options(self, changes: dict[int, str]) -> str:
        """Persist launch options. Returns 'live' or 'file' describing the route."""
        steam = self.steam()
        if steam.is_running():
            try:
                for app_id, options in changes.items():
                    self.cef.set_launch_options(app_id, options)
                live = self._live_launch_options(list(changes))
                if live is not None:
                    failed = [a for a, o in changes.items() if a in live and live[a] != o]
                    if failed:
                        raise CefError(tr("svc_steam_rejected", ids=failed))
                return "live"
            except (CefError, OSError) as error:
                raise SteamMustCloseError(str(error)) from error
        steam.write_launch_options_offline(changes)
        return "file"

    # ---- scanning -------------------------------------------------------------

    def scan(self, rescan_library: bool = True) -> tuple[list[GameEntry], list[SyncChange]]:
        steam = self.steam()
        cached = self.state.get("games")
        # Caches written before localized names existed are refreshed once.
        if rescan_library or not cached or any("names" not in g for g in cached):
            games = steam.scan_games()
            self.state["games"] = [
                {"app_id": g.app_id, "name": g.name, "names": g.names,
                 "install_dir": str(g.install_dir)}
                for g in games
            ]
            self.state["scanned"] = True
            self._save_state()
            changes = self.sync_paths(steam, games)
        else:
            changes = []
        return self.entries(steam), changes

    def entries(self, steam: Optional[SteamInstallation] = None) -> list[GameEntry]:
        steam = steam or self.steam()
        cached = self.state.get("games", [])
        options = self.read_launch_options(steam, [g["app_id"] for g in cached])
        try:
            config: Optional[MakoConfig] = self.mako()
        except (OSError, ValueError):
            config = None
        result = []
        for game in cached:
            app_id = int(game["app_id"])
            opts = options.get(app_id, "")
            profile = config.profile_for_app(app_id) if config else None
            managed = self.state["managed"].get(str(app_id), {})
            result.append(GameEntry(
                app_id=app_id,
                name=game["name"],
                install_dir=game["install_dir"],
                launch_options=opts,
                has_mako=lo.has_mako(opts),
                profile_name=profile.name if profile else None,
                profile_processes=profile.processes if profile else [],
                managed=bool(managed),
                executables=list(managed.get("executables", [])),
                names=dict(game.get("names") or {}),
            ))
        return result

    def sync_paths(self, steam: SteamInstallation,
                   games: Optional[list[SteamGame]] = None) -> list[SyncChange]:
        """Refresh detected executables for games installed through the assistant."""
        managed = self.state.get("managed", {})
        if not managed:
            return []
        games = games if games is not None else steam.scan_games()
        by_id = {g.app_id: g for g in games}
        try:
            config = self.mako()
        except (OSError, ValueError):
            return []

        changes: list[SyncChange] = []
        dirty = False
        for key, record in managed.items():
            game = by_id.get(int(key))
            if game is None:
                continue  # uninstalled or library offline: keep the old match
            paths = [str(p) for p in detect_executables(game.install_dir, game.appinfo)]
            names = process_names(Path(p) for p in paths)
            if not names:
                continue
            profile = config.profile_for_app(game.app_id)
            if profile is None and record.get("profile"):
                continue  # the user deleted the profile in MAKO UI; respect that
            before = profile.processes if profile else []
            captured = [n.casefold() for n in profile.captured] if profile else None
            if captured != [n.casefold() for n in names]:
                name, _ = config.upsert_game(game.app_id, game.name, names)
                record["profile"] = name
                dirty = True
            after = config.profile_for_app(game.app_id).processes
            if before != after or record.get("executables") != paths:
                changes.append(SyncChange(
                    game.app_id, localized_name(game.name, game.names), before, after,
                    list(record.get("executables") or []), paths))
            record["executables"] = paths
            record["install_dir"] = str(game.install_dir)
        if dirty:
            config.save()
        self._save_state()
        return changes

    def _game(self, steam: SteamInstallation, app_id: int) -> SteamGame:
        game = next((g for g in steam.scan_games() if g.app_id == app_id), None)
        if game is None:
            raise LookupError(tr("svc_app_missing", app_id=app_id))
        return game

    # ---- actions ----------------------------------------------------------------

    def install(self, app_id: int) -> str:
        steam = self.steam()
        game = self._game(steam, app_id)
        paths = detect_executables(game.install_dir, game.appinfo)
        names = process_names(paths)

        current = self.read_launch_options(steam, [app_id]).get(app_id, "")
        route = self.apply_launch_options({app_id: lo.add_mako(current)})

        message = tr("svc_injected", name=localized_name(game.name, game.names))
        profile_name = None
        if names:
            config = self.mako()
            profile_name, created = config.upsert_game(app_id, game.name, names)
            config.save()
            key = "svc_profile_created" if created else "svc_profile_updated"
            processes = ", ".join(config.profile_for_app(app_id).processes)
            message += "\n" + tr(key, profile=profile_name, processes=processes)
        else:
            message += "\n" + tr("svc_no_exe")

        self.state["managed"][str(app_id)] = {
            "name": game.name,
            "install_dir": str(game.install_dir),
            "executables": [str(p) for p in paths],
            "profile": profile_name,
        }
        self._save_state()
        if route == "file":
            message += "\n" + tr("svc_file_written")
        return message

    def uninstall(self, app_id: int, remove_config: bool) -> str:
        steam = self.steam()
        current = self.read_launch_options(steam, [app_id]).get(app_id, "")
        cached = next((g for g in self.state.get("games", [])
                       if int(g["app_id"]) == app_id), None)
        name = (localized_name(cached["name"], cached.get("names") or {})
                if cached else str(app_id))
        message = ""
        if lo.has_mako(current):
            self.apply_launch_options({app_id: lo.remove_mako(current)})
            message = tr("svc_option_removed", name=name)
        else:
            message = tr("svc_option_absent", name=name)
        if remove_config:
            config = self.mako()
            removed = config.remove_game(app_id)
            if removed:
                config.save()
                message += "\n" + tr("svc_profile_removed", profile=removed)
            self.state["managed"].pop(str(app_id), None)
        else:
            message += "\n" + tr("svc_profile_kept")
        self._save_state()
        return message

    # ---- Steam process control (fallback when CEF is unavailable) -------------

    def shutdown_steam(self, progress: Callable[[str], None] = lambda _: None) -> bool:
        steam_bin = shutil.which("steam") or str(self.steam().root / "steam.sh")
        progress(tr("svc_closing_steam"))
        subprocess.Popen([steam_bin, "-shutdown"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return self.steam().wait_until_closed(90)

    def launch_game(self, app_id: int) -> None:
        """Ask Steam to start the game (it forwards to a running client)."""
        url = f"steam://rungameid/{int(app_id)}"
        steam_bin = shutil.which("steam")
        command = [steam_bin, url] if steam_bin else ["xdg-open", url]
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError as error:
            raise RuntimeError(tr("svc_launch_failed", error=error)) from error

    @property
    def language(self) -> Optional[str]:
        return self.state.get("language")

    @language.setter
    def language(self, code: str) -> None:
        self.state["language"] = code
        self._save_state()

    @property
    def overlay_enabled(self) -> bool:
        return bool(self.state.get("overlay", True))

    @overlay_enabled.setter
    def overlay_enabled(self, enabled: bool) -> None:
        self.state["overlay"] = bool(enabled)
        self._save_state()

    def start_steam(self) -> None:
        steam_bin = shutil.which("steam") or str(self.steam().root / "steam.sh")
        subprocess.Popen([steam_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
