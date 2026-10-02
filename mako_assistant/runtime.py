"""Detect what MAKO is *actually* doing inside running Steam games.

Nothing here reads conf.toml. The sources are the live processes:

* ``/proc/<pid>/environ``: ``SteamAppId`` & co. tie a process to a Steam app
  (the same gate the MAKO Decky plugin uses), plus launcher toggles that
  mako-launch exports (Zink, ALSA).
* ``/proc/<pid>/maps``: proves the MAKO layer (``libmako-render.so``) and
  vkBasalt were really loaded into the process.
* ``~/.config/mako-render/runtime-state/*.json``: written by the MAKO layer per
  swapchain context with the *applied* settings and whether frame generation
  and spatial scaling are active. The layer leaves these files behind when a
  game exits, so a file only counts when its pid is alive *and* the pid's
  start time matches ``process_start_ticks``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .i18n import tr
from .mako_config import config_dir

_APP_ID_ENV_KEYS = ("SteamAppId", "SteamGameId", "STEAM_COMPAT_APP_ID")
_MAKO_LIBRARY = b"libmako-render.so"
_VKBASALT_LIBRARY = b"vkbasalt"


@dataclass
class RuntimeContext:
    pid: int
    role: str
    phase: str
    updated_ms: int
    frame_generation_active: bool
    spatial: dict[str, Any]
    applied: dict[str, Any]
    pending: dict[str, Any]
    error: Optional[str]


@dataclass
class RunningGame:
    app_id: int
    pids: list[int] = field(default_factory=list)
    mako_loaded: bool = False
    vkbasalt_loaded: bool = False
    zink: bool = False
    alsa: bool = False
    contexts: list[RuntimeContext] = field(default_factory=list)

    @property
    def frame_generation(self) -> Optional[RuntimeContext]:
        live = [c for c in self.contexts if c.role == "frame-generation"]
        return max(live, key=lambda c: c.updated_ms) if live else None

    @property
    def latest(self) -> Optional[RuntimeContext]:
        return max(self.contexts, key=lambda c: c.updated_ms) if self.contexts else None


def _read_environ(pid_dir: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in (pid_dir / "environ").read_bytes().split(b"\0"):
        key, sep, value = item.partition(b"=")
        if sep:
            values[key.decode(errors="ignore")] = value.decode(errors="ignore")
    return values


def _start_ticks(pid: int, proc: Path) -> Optional[int]:
    try:
        stat = (proc / str(pid) / "stat").read_text()
    except OSError:
        return None
    # comm (field 2) may contain spaces/parentheses: split after the last ')'.
    fields = stat.rsplit(")", 1)[-1].split()
    try:
        return int(fields[19])  # field 22 overall: starttime
    except (IndexError, ValueError):
        return None


def _maps_contains(pid_dir: Path, needles: tuple[bytes, ...]) -> set[bytes]:
    found: set[bytes] = set()
    try:
        with (pid_dir / "maps").open("rb") as handle:
            for line in handle:
                for needle in needles:
                    if needle not in found and needle in line:
                        found.add(needle)
                if len(found) == len(needles):
                    break
    except OSError:
        pass
    return found


def runtime_state_dir() -> Path:
    return config_dir() / "runtime-state"


def detect_running(proc: Path = Path("/proc"),
                   state_dir: Optional[Path] = None) -> dict[int, RunningGame]:
    """Return running Steam games keyed by app id, with their live MAKO state."""
    uid = os.getuid()
    games: dict[int, RunningGame] = {}
    pid_owner: dict[int, int] = {}
    try:
        entries = list(proc.iterdir())
    except OSError:
        return {}
    for pid_dir in entries:
        if not pid_dir.name.isdigit():
            continue
        try:
            if pid_dir.stat().st_uid != uid:
                continue
            env = _read_environ(pid_dir)
        except OSError:
            continue
        app_id = next((env[k].strip() for k in _APP_ID_ENV_KEYS
                       if env.get(k, "").strip().isdigit() and env[k].strip() != "0"), None)
        if app_id is None:
            continue
        pid = int(pid_dir.name)
        game = games.setdefault(int(app_id), RunningGame(int(app_id)))
        game.pids.append(pid)
        pid_owner[pid] = game.app_id
        found = _maps_contains(pid_dir, (_MAKO_LIBRARY, _VKBASALT_LIBRARY))
        game.mako_loaded |= _MAKO_LIBRARY in found
        game.vkbasalt_loaded |= _VKBASALT_LIBRARY in found
        if _MAKO_LIBRARY in found:
            game.zink |= env.get("MESA_LOADER_DRIVER_OVERRIDE") == "zink"
            game.alsa |= env.get("SDL_AUDIODRIVER") == "alsa"

    directory = state_dir or runtime_state_dir()
    try:
        files = list(directory.glob("*.json"))
    except OSError:
        files = []
    for path in files:
        try:
            pid = int(path.name.split("-", 1)[0])
        except ValueError:
            continue
        owner = pid_owner.get(pid)
        if owner is None:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("process_start_ticks") != _start_ticks(pid, proc):
            continue  # stale file from an earlier process that reused this pid
        games[owner].contexts.append(RuntimeContext(
            pid=pid,
            role=str(data.get("role") or ""),
            phase=str(data.get("phase") or ""),
            updated_ms=int(data.get("updated_unix_ms") or 0),
            frame_generation_active=bool(data.get("frame_generation_active")),
            spatial=dict(data.get("spatial_scaling") or {}),
            applied=dict(data.get("applied") or {}),
            pending=dict(data.get("pending") or {}),
            error=data.get("error"),
        ))
    return games


# ---- human readable summary --------------------------------------------------

_PHASES = {"active": "phase_active", "preparing": "phase_preparing",
           "debouncing": "phase_debouncing"}
_PENDING = {
    "frame_generation_private": "pending_fg",
    "spatial_private": "pending_spatial",
    "swapchain_recreation": "pending_swapchain",
    "process_restart": "pending_restart",
}
_METHODS = {"ls1": None, "ls1-performance": "method_ls1_perf", "native": "method_native"}


@dataclass
class Feature:
    label: str
    active: bool
    detail: str = ""


def _method(name: Any) -> str:
    key = _METHODS.get(str(name))
    return tr(key) if key else str(name).upper()


def describe(game: RunningGame) -> tuple[str, list[Feature], list[str]]:
    """Return (headline, feature list, notes) in the current UI language."""
    if not game.mako_loaded:
        return tr("rt_no_mako"), [], []
    context = game.frame_generation or game.latest
    if context is None:
        return tr("rt_waiting"), [], []

    applied = context.applied
    features: list[Feature] = []

    if context.frame_generation_active:
        if applied.get("adaptive"):
            parts = [tr("fg_adaptive", fps=applied.get("target_fps"),
                        max=applied.get("adaptive_max_multiplier"))]
        else:
            parts = [f"×{applied.get('multiplier')}"]
        flow = applied.get("effective_flow_scale", applied.get("flow_scale"))
        if isinstance(flow, (int, float)):
            parts.append(f"Flow {flow:.2f}")
        if applied.get("effective_performance_mode"):
            parts.append(tr("fg_perf"))
        if applied.get("ultra_performance"):
            parts.append(tr("fg_ultra"))
        features.append(Feature(tr("feat_fg"), True, " · ".join(parts)))
    else:
        reason = "fg_disabled" if not applied.get("frame_generation_enabled") else "fg_inactive"
        features.append(Feature(tr("feat_fg"), False, tr(reason)))

    spatial = context.spatial
    if spatial.get("active"):
        detail = f"{_method(spatial.get('active_method'))} ×{spatial.get('effective_factor')}"
        src = (spatial.get("source_width"), spatial.get("source_height"))
        dst = (spatial.get("presentation_width"), spatial.get("presentation_height"))
        if all(src) and all(dst):
            detail += f" ({src[0]}×{src[1]} → {dst[0]}×{dst[1]})"
        if spatial.get("supersampling_active"):
            detail += " · " + tr("sc_supersampling")
        features.append(Feature(tr("feat_scaling"), True, detail))
    elif applied.get("scaling_enabled"):
        reason = (spatial.get("inactive_reason") or spatial.get("fallback_reason")
                  or spatial.get("constraint_reason"))
        features.append(Feature(tr("feat_scaling"), False, str(reason) if reason
                                else tr("fg_inactive")))

    if game.vkbasalt_loaded:
        features.append(Feature("vkBasalt", True))
    if game.zink:
        features.append(Feature("Zink", True))
    if game.alsa:
        features.append(Feature(tr("feat_alsa"), True))

    notes = [tr(_PENDING[k]) for k, v in context.pending.items() if v and k in _PENDING]
    if context.error:
        notes.append(tr("log_error", error=context.error))
    phase_key = _PHASES.get(context.phase)
    phase = tr(phase_key) if phase_key else context.phase
    headline = tr("rt_headline", phase=phase, profile=applied.get("name", "?"))
    return headline, features, notes
