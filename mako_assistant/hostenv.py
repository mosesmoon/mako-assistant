"""Reach the host system when MAKO Assistant runs inside a Flatpak sandbox.

Outside Flatpak everything here is a thin pass-through. Inside Flatpak:

* the sandbox has its own PID namespace, so host processes (Steam, games) are
  invisible in ``/proc``: a small POSIX shell script runs on the host through
  ``flatpak-spawn --host`` and reports just the fields we need;
* host programs (``mako-cli``, ``steam``) cannot run inside the sandbox, so
  they are started through ``flatpak-spawn --host`` as well;
* ``XDG_CONFIG_HOME`` points into ``~/.var/app/<id>``, so the host's own
  directory comes from ``HOST_XDG_CONFIG_HOME`` (Flatpak 1.13+) or ``~/.config``.

This needs the Flatpak permissions ``--talk-name=org.freedesktop.Flatpak`` and
``--filesystem=host``; see ``packaging/flatpak``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

IN_FLATPAK = Path("/.flatpak-info").exists()

# Environment keys read from game processes (see runtime.py).
PROCESS_ENV_KEYS = ("SteamAppId", "SteamGameId", "STEAM_COMPAT_APP_ID",
                    "MESA_LOADER_DRIVER_OVERRIDE", "SDL_AUDIODRIVER")
PROCESS_LIBRARIES = ("libmako-render.so", "vkbasalt")

# One grep over every environ file picks the few Steam processes, so a poll
# costs a handful of forks on the host, not one per process.
_PROCESS_SCRIPT = r"""
for f in $(grep -l -a -E 'SteamAppId=|SteamGameId=|STEAM_COMPAT_APP_ID=' /proc/[0-9]*/environ 2>/dev/null); do
    d=${f%/environ}
    [ -O "$d" ] || continue
    printf '@%s\n' "${d#/proc/}"
    tr '\0' '\n' < "$f" 2>/dev/null | grep -E '^(SteamAppId|SteamGameId|STEAM_COMPAT_APP_ID|MESA_LOADER_DRIVER_OVERRIDE|SDL_AUDIODRIVER)='
    grep -q -F libmako-render.so "$d/maps" 2>/dev/null && echo '+libmako-render.so'
    grep -q -F vkbasalt "$d/maps" 2>/dev/null && echo '+vkbasalt'
    s=$(cat "$d/stat" 2>/dev/null) && printf '=%s\n' "$s"
done
exit 0
"""

_STEAM_SCRIPT = r"""
for f in $(grep -l -x -F steam /proc/[0-9]*/comm 2>/dev/null); do
    d=${f%/comm}
    [ -O "$d" ] || continue
    readlink "$d/exe" 2>/dev/null
done
exit 0
"""


@dataclass
class ProcessInfo:
    """What runtime.py needs to know about one process."""
    pid: int
    env: dict[str, str] = field(default_factory=dict)
    libraries: set[str] = field(default_factory=set)
    start_ticks: Optional[int] = None


def start_ticks_from_stat(stat: str) -> Optional[int]:
    # comm (field 2) may contain spaces/parentheses: split after the last ')'.
    fields = stat.rsplit(")", 1)[-1].split()
    try:
        return int(fields[19])  # field 22 overall: starttime
    except (IndexError, ValueError):
        return None


def host_argv(argv: Sequence[str]) -> list[str]:
    """The command line that runs ``argv`` on the host."""
    argv = [str(a) for a in argv]
    return ["flatpak-spawn", "--host", *argv] if IN_FLATPAK else argv


def run(argv: Sequence[str], timeout: float = 30) -> subprocess.CompletedProcess:
    """Run a host program and capture its output."""
    return subprocess.run(host_argv(argv), capture_output=True, text=True, timeout=timeout)


def spawn(argv: Sequence[str]) -> None:
    """Start a host program in the background (Steam, a steam:// URL)."""
    subprocess.Popen(host_argv(argv), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def which(name: str) -> Optional[str]:
    """Like shutil.which, but looks at the host's PATH inside Flatpak."""
    if not IN_FLATPAK:
        return shutil.which(name)
    try:
        result = run(["sh", "-c", 'command -v "$1"', "sh", name], timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    found = result.stdout.strip().splitlines()
    return found[0] if result.returncode == 0 and found and found[0].startswith("/") else None


def xdg_config_home() -> Path:
    """The user's real config directory (the host's, also inside Flatpak)."""
    if IN_FLATPAK:
        base = os.environ.get("HOST_XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base)


def parse_process_report(text: str) -> list[ProcessInfo]:
    processes: list[ProcessInfo] = []
    current: Optional[ProcessInfo] = None
    for line in text.splitlines():
        if line.startswith("@"):
            try:
                current = ProcessInfo(int(line[1:]))
            except ValueError:
                current = None
                continue
            processes.append(current)
        elif current is None:
            continue
        elif line.startswith("+"):
            current.libraries.add(line[1:])
        elif line.startswith("="):
            current.start_ticks = start_ticks_from_stat(line[1:])
        else:
            key, sep, value = line.partition("=")
            if sep and key in PROCESS_ENV_KEYS:
                current.env[key] = value
    return processes


def host_processes() -> Optional[list[ProcessInfo]]:
    """Steam game processes on the host (Flatpak only); None if the host is unreachable."""
    try:
        result = run(["sh", "-c", _PROCESS_SCRIPT], timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return parse_process_report(result.stdout)


def host_steam_executables() -> Optional[list[str]]:
    """Executables of the host's processes named ``steam`` (Flatpak only)."""
    try:
        result = run(["sh", "-c", _STEAM_SCRIPT], timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]
