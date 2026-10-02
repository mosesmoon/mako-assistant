"""Read and write MAKO Renderer's conf.toml and its profile-metadata.json.

Conventions follow the MAKO Decky plugin so MAKO UI and Decky recognise the
profiles the assistant creates:

* ``conf.toml``: one ``[[profile]]`` per game, matched by ``active_in``.
* ``profile-metadata.json``: ``kind = "game"``, ``steam_app_id`` (string),
  ``display_name`` and ``captured_processes`` (the automatically detected
  names; anything else in ``active_in`` is a user alias and is preserved).
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .i18n import tr

DEFAULT_PROFILE_NAME = "mako"
METADATA_VERSION = 1
_INVALID_NAME_CHARS = set('\t\n\r\'"\\/$|&;()<>{}[]`*?')


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "mako-render"


def mako_cli() -> Optional[Path]:
    for candidate in (
        Path("~/.local/bin/mako-cli").expanduser(),
        Path("~/.local/share/mako-render/bin/mako-cli").expanduser(),
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which("mako-cli")
    return Path(found) if found else None


# ---- TOML serialisation ---------------------------------------------------

def _toml_string(value: str) -> str:
    out = ['"']
    for char in value:
        if char == '"':
            out.append('\\"')
        elif char == "\\":
            out.append("\\\\")
        elif char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _toml_key(key: str) -> str:
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else _toml_string(key)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return repr(value)
    if isinstance(value, str):
        return _toml_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_toml_key(k)} = {_toml_value(v)}" for k, v in value.items()) + " }"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"cannot serialise {type(value).__name__} to TOML")


def _is_table_array(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, dict) for v in value)


def dump_toml(data: dict[str, Any], header_comments: list[str] = ()) -> str:
    lines: list[str] = []

    def emit_table(prefix: str, table: dict[str, Any], array: bool) -> None:
        if lines:
            lines.append("")
        lines.append(f"[[{prefix}]]" if array else f"[{prefix}]")
        emit_body(prefix, table)

    def emit_body(prefix: str, table: dict[str, Any]) -> None:
        nested = []
        for key, value in table.items():
            if isinstance(value, dict) or _is_table_array(value):
                nested.append((key, value))
            else:
                lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
        for key, value in nested:
            path = f"{prefix}.{_toml_key(key)}" if prefix else _toml_key(key)
            if isinstance(value, dict):
                emit_table(path, value, array=False)
            else:
                for item in value:
                    emit_table(path, item, array=True)

    scalars = {k: v for k, v in data.items() if not (isinstance(v, dict) or _is_table_array(v))}
    for key, value in scalars.items():
        lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
        if key == "version":
            lines.extend(header_comments)
    emit_body("", {k: v for k, v in data.items() if k not in scalars})
    return "\n".join(lines) + "\n"


# ---- helpers ----------------------------------------------------------------

def processes_of(profile: dict[str, Any]) -> list[str]:
    active_in = profile.get("active_in", "")
    values = active_in if isinstance(active_in, (list, tuple)) else str(active_in).split(",")
    return [str(v).strip() for v in values if str(v).strip()]


def _active_in_value(processes: list[str]) -> Any:
    return processes[0] if len(processes) == 1 else list(processes)


def safe_profile_name(display_name: str, app_id: int) -> str:
    name = "".join(c for c in display_name if c not in _INVALID_NAME_CHARS)
    name = re.sub(r"\s+", "-", name.strip()).strip("-")
    if not name or name.lower() in {"global", "profile", DEFAULT_PROFILE_NAME}:
        name = f"game-{app_id}"
    return name


@dataclass
class GameProfile:
    name: str
    display_name: str
    processes: list[str]
    captured: list[str]


class MakoConfig:
    def __init__(self, directory: Optional[Path] = None) -> None:
        self.dir = Path(directory) if directory else config_dir()
        self.conf_path = self.dir / "conf.toml"
        self.meta_path = self.dir / "profile-metadata.json"
        self.data: dict[str, Any] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self._header_comments: list[str] = []

    # ---- io ----

    def exists(self) -> bool:
        return self.conf_path.is_file()

    def load(self) -> None:
        text = self.conf_path.read_text(encoding="utf-8")
        self.data = tomllib.loads(text)
        self._header_comments = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                break
            if stripped.startswith("#"):
                self._header_comments.append(stripped)
        self.metadata = {}
        if self.meta_path.is_file():
            payload = json.loads(self.meta_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("profiles"), dict):
                self.metadata = {k: dict(v) for k, v in payload["profiles"].items()
                                 if isinstance(v, dict)}

    def save(self) -> None:
        """Write both files atomically; roll back if mako-cli rejects the result."""
        self.dir.mkdir(parents=True, exist_ok=True)
        text = dump_toml(self.data, self._header_comments)
        tomllib.loads(text)  # never write something we cannot read back

        backup = self.conf_path.with_name("conf.toml.mako-assistant.bak")
        had_conf = self.conf_path.is_file()
        if had_conf:
            shutil.copy2(self.conf_path, backup)
        tmp = self.conf_path.with_name("conf.toml.mako-assistant.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.conf_path)

        cli = mako_cli()
        if cli is not None:
            result = subprocess.run(
                [str(cli), "validate", "-c", str(self.conf_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                if had_conf:
                    shutil.copy2(backup, self.conf_path)
                raise ValueError(tr("cfg_rejected",
                                    details=(result.stderr or result.stdout).strip()))

        # Keep metadata in step with the profiles that exist (like Decky does).
        profiles = self.profiles()
        payload_profiles = {}
        for profile in profiles:
            name = str(profile.get("name", ""))
            entry = self.metadata.get(name) or {}
            payload_profiles[name] = {
                "captured_processes": list(entry.get("captured_processes") or []),
                "display_name": entry.get("display_name")
                or ("Default" if name == DEFAULT_PROFILE_NAME else name),
                "kind": entry.get("kind")
                or ("default" if name == DEFAULT_PROFILE_NAME
                    else "process" if processes_of(profile) else "manual"),
                "steam_app_id": entry.get("steam_app_id"),
            }
        self.metadata = payload_profiles
        meta_tmp = self.meta_path.with_name("profile-metadata.json.tmp")
        meta_tmp.write_text(
            json.dumps({"profiles": payload_profiles, "version": METADATA_VERSION},
                       indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(meta_tmp, self.meta_path)

    # ---- queries ----

    def profiles(self) -> list[dict[str, Any]]:
        profiles = self.data.setdefault("profile", [])
        if not isinstance(profiles, list):
            raise ValueError("conf.toml: 'profile' is not an array of tables")
        return profiles

    def _profile(self, name: str) -> Optional[dict[str, Any]]:
        return next((p for p in self.profiles() if p.get("name") == name), None)

    def profile_for_app(self, app_id: int) -> Optional[GameProfile]:
        target = str(app_id)
        for name, entry in self.metadata.items():
            if str(entry.get("steam_app_id") or "") == target:
                profile = self._profile(name)
                if profile is not None:
                    return GameProfile(
                        name=name,
                        display_name=str(entry.get("display_name") or name),
                        processes=processes_of(profile),
                        captured=list(entry.get("captured_processes") or []),
                    )
        return None

    def _profile_matching_processes(self, processes: list[str]) -> Optional[str]:
        wanted = {p.casefold() for p in processes}
        for profile in self.profiles():
            name = str(profile.get("name", ""))
            if name == DEFAULT_PROFILE_NAME:
                continue
            if self.metadata.get(name, {}).get("steam_app_id"):
                continue
            if wanted & {p.casefold() for p in processes_of(profile)}:
                return name
        return None

    # ---- mutations (call save() afterwards) ----

    def upsert_game(self, app_id: int, display_name: str, processes: list[str]) -> tuple[str, bool]:
        """Create or refresh the game's profile. Returns (profile name, created)."""
        if not self.profiles():
            raise ValueError(tr("cfg_no_profiles"))
        existing = self.profile_for_app(app_id)
        name = existing.name if existing else self._profile_matching_processes(processes)
        created = name is None
        if created:
            source = self._profile(DEFAULT_PROFILE_NAME) or self.profiles()[0]
            base = safe_profile_name(display_name, app_id)
            name, suffix = base, 2
            while self._profile(name) is not None:
                name, suffix = f"{base}-{suffix}", suffix + 1
            profile = {"name": name}
            profile.update({k: v for k, v in source.items() if k not in ("name", "active_in")})
            self.profiles().append(profile)
        profile = self._profile(name)
        assert profile is not None

        previous_captured = {
            p.casefold() for p in (self.metadata.get(name, {}).get("captured_processes") or [])
        }
        merged = [p for p in processes_of(profile) if p.casefold() not in previous_captured]
        known = {p.casefold() for p in merged}
        for process in processes:
            if process.casefold() not in known:
                merged.append(process)
                known.add(process.casefold())

        # Keep "name" first and active_in right after it, like MAKO UI writes.
        rest = {k: v for k, v in profile.items() if k not in ("name", "active_in")}
        profile.clear()
        profile["name"] = name
        if merged:
            profile["active_in"] = _active_in_value(merged)
        profile.update(rest)

        entry = self.metadata.get(name, {})
        self.metadata[name] = {
            "captured_processes": list(processes),
            "display_name": display_name if created or not entry.get("display_name")
            else entry["display_name"],
            "kind": "game",
            "steam_app_id": str(app_id),
        }
        return name, created

    def remove_game(self, app_id: int) -> Optional[str]:
        existing = self.profile_for_app(app_id)
        if existing is None or existing.name == DEFAULT_PROFILE_NAME:
            return None
        self.data["profile"] = [p for p in self.profiles() if p.get("name") != existing.name]
        self.metadata.pop(existing.name, None)
        return existing.name
