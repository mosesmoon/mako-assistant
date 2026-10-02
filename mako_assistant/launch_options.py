"""Pure string transforms for Steam launch options.

The MAKO wrapper must sit directly in front of ``%command%`` so that any
environment assignments the user already has (``FOO=1 %command%``) are still
exported to the game through mako-launch.
"""

from __future__ import annotations

import re

MAKO_LAUNCH = "~/.local/bin/mako-launch"
MAKO_LAUNCH_COMMAND = f"{MAKO_LAUNCH} %command%"

# Any spelling of the wrapper: ~/..., $HOME/..., /home/x/..., or bare name,
# optionally followed by "--".
_WRAPPER = re.compile(r"(?:(?<=\s)|^)(?:\S*/)?mako-launch(?:\s+--)?\s+(?=%command%)")
_ANY_WRAPPER = re.compile(r"(?:(?<=\s)|^)(?:\S*/)?mako-launch(?=\s|$)")


def has_mako(options: str) -> bool:
    return bool(_ANY_WRAPPER.search(options or ""))


def add_mako(options: str) -> str:
    options = (options or "").strip()
    if has_mako(options):
        return options
    if not options:
        return MAKO_LAUNCH_COMMAND
    if "%command%" in options:
        return options.replace("%command%", MAKO_LAUNCH_COMMAND, 1)
    # Plain arguments (e.g. "-dx11") are appended to the game by Steam.
    return f"{MAKO_LAUNCH_COMMAND} {options}"


def remove_mako(options: str) -> str:
    options = (options or "").strip()
    stripped = _WRAPPER.sub("", options)
    # A wrapper that is not directly in front of %command% (hand-edited).
    stripped = _ANY_WRAPPER.sub("", stripped)
    stripped = re.sub(r"\s{2,}", " ", stripped).strip()
    return "" if stripped == "%command%" else stripped
