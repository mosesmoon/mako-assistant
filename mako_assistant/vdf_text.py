"""Text KeyValues (VDF) reader/writer for Steam files such as localconfig.vdf.

Output follows Steam's own formatting (tab indentation, quoted keys and
values) so a rewritten file is indistinguishable from one Steam saved.
"""

from __future__ import annotations

from typing import Union

VdfValue = Union[str, "VdfDict"]
VdfDict = dict  # insertion-ordered str -> VdfValue

_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


class VdfError(ValueError):
    pass


def _tokenize(text: str):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n﻿":
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end < 0 else end + 1
        elif c in "{}":
            yield c
            i += 1
        elif c == "[":  # conditional such as [$WIN32]; ignored
            end = text.find("]", i)
            if end < 0:
                raise VdfError("unterminated conditional")
            i = end + 1
        elif c == '"':
            i += 1
            out = []
            while True:
                if i >= n:
                    raise VdfError("unterminated string")
                c = text[i]
                if c == "\\" and i + 1 < n and text[i + 1] in _ESCAPES:
                    out.append(_ESCAPES[text[i + 1]])
                    i += 2
                elif c == '"':
                    i += 1
                    break
                else:
                    out.append(c)
                    i += 1
            yield ("s", "".join(out))
        else:
            start = i
            while i < n and text[i] not in ' \t\r\n{}"':
                i += 1
            yield ("s", text[start:i])


def loads(text: str) -> VdfDict:
    root: VdfDict = {}
    stack = [root]
    pending_key = None
    for token in _tokenize(text):
        if token == "{":
            if pending_key is None:
                raise VdfError("'{' without key")
            child = stack[-1].get(pending_key)
            if not isinstance(child, dict):
                child = {}
                stack[-1][pending_key] = child
            stack.append(child)
            pending_key = None
        elif token == "}":
            if len(stack) == 1 or pending_key is not None:
                raise VdfError("unbalanced '}'")
            stack.pop()
        else:
            value = token[1]
            if pending_key is None:
                pending_key = value
            else:
                stack[-1][pending_key] = value
                pending_key = None
    if len(stack) != 1 or pending_key is not None:
        raise VdfError("unexpected end of file")
    return root


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dumps(data: VdfDict) -> str:
    lines: list[str] = []

    def walk(node: VdfDict, depth: int) -> None:
        indent = "\t" * depth
        for key, value in node.items():
            if isinstance(value, dict):
                lines.append(f"{indent}{_quote(key)}")
                lines.append(f"{indent}{{")
                walk(value, depth + 1)
                lines.append(f"{indent}}}")
            else:
                lines.append(f"{indent}{_quote(key)}\t\t{_quote(str(value))}")

    walk(data, 0)
    return "\n".join(lines) + "\n"


def get_ci(node: VdfDict, key: str):
    """Case-insensitive child lookup (Steam is inconsistent: apps/Apps)."""
    if key in node:
        return node[key]
    lowered = key.lower()
    for existing, value in node.items():
        if existing.lower() == lowered:
            return value
    return None


def child_ci(node: VdfDict, key: str) -> VdfDict:
    """Return the case-insensitively matching child map, creating it if absent."""
    found = get_ci(node, key)
    if isinstance(found, dict):
        return found
    node[key] = {}
    return node[key]
