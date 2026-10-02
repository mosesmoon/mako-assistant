"""Reader for Steam's binary ``appcache/appinfo.vdf`` (versions 27, 28 and 29).

Only the entries that are actually requested are decoded; every other app
section is skipped by its length prefix, which keeps a scan fast even with a
large (100+ MB) cache.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any, Iterable, Optional

_MAGIC_V27 = 0x07564427
_MAGIC_V28 = 0x07564428
_MAGIC_V29 = 0x07564429

_TYPE_MAP = 0x00
_TYPE_STRING = 0x01
_TYPE_INT32 = 0x02
_TYPE_FLOAT = 0x03
_TYPE_POINTER = 0x04
_TYPE_WSTRING = 0x05
_TYPE_COLOR = 0x06
_TYPE_UINT64 = 0x07
_TYPE_END = 0x08
_TYPE_INT64 = 0x0A
_TYPE_END_ALT = 0x0B


class AppInfoError(ValueError):
    pass


class _BinaryKV:
    def __init__(self, data: bytes, string_table: Optional[list[str]]) -> None:
        self.data = data
        self.pos = 0
        self.strings = string_table

    def _cstring(self) -> str:
        end = self.data.index(b"\x00", self.pos)
        value = self.data[self.pos:end].decode("utf-8", errors="replace")
        self.pos = end + 1
        return value

    def _key(self) -> str:
        if self.strings is None:
            return self._cstring()
        (index,) = struct.unpack_from("<I", self.data, self.pos)
        self.pos += 4
        try:
            return self.strings[index]
        except IndexError as error:
            raise AppInfoError(f"string table index {index} out of range") from error

    def parse_map(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while True:
            kind = self.data[self.pos]
            self.pos += 1
            if kind in (_TYPE_END, _TYPE_END_ALT):
                return result
            key = self._key()
            if kind == _TYPE_MAP:
                result[key] = self.parse_map()
            elif kind == _TYPE_STRING:
                result[key] = self._cstring()
            elif kind in (_TYPE_INT32, _TYPE_POINTER, _TYPE_COLOR):
                (result[key],) = struct.unpack_from("<i", self.data, self.pos)
                self.pos += 4
            elif kind == _TYPE_FLOAT:
                (result[key],) = struct.unpack_from("<f", self.data, self.pos)
                self.pos += 4
            elif kind == _TYPE_UINT64:
                (result[key],) = struct.unpack_from("<Q", self.data, self.pos)
                self.pos += 8
            elif kind == _TYPE_INT64:
                (result[key],) = struct.unpack_from("<q", self.data, self.pos)
                self.pos += 8
            elif kind == _TYPE_WSTRING:
                end = self.pos
                while self.data[end:end + 2] != b"\x00\x00":
                    end += 2
                result[key] = self.data[self.pos:end].decode("utf-16-le", errors="replace")
                self.pos = end + 2
            else:
                raise AppInfoError(f"unknown binary VDF type 0x{kind:02x}")


def read_appinfo(path: Path, app_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Return the decoded ``appinfo`` sections for the requested app ids."""
    wanted = {int(app_id) for app_id in app_ids}
    data = Path(path).read_bytes()
    if len(data) < 8:
        raise AppInfoError("appinfo.vdf is truncated")
    magic, _universe = struct.unpack_from("<II", data, 0)
    pos = 8
    string_table: Optional[list[str]] = None
    if magic == _MAGIC_V29:
        (table_offset,) = struct.unpack_from("<q", data, pos)
        pos += 8
        (count,) = struct.unpack_from("<I", data, table_offset)
        raw = data[table_offset + 4:].split(b"\x00", count)
        string_table = [item.decode("utf-8", errors="replace") for item in raw[:count]]
    elif magic not in (_MAGIC_V27, _MAGIC_V28):
        raise AppInfoError(f"unsupported appinfo.vdf magic 0x{magic:08x}")

    # v27 headers lack the binary-data SHA1 that v28+ append.
    header_size = 40 if magic == _MAGIC_V27 else 60
    result: dict[int, dict[str, Any]] = {}
    while pos + 8 <= len(data) and wanted - result.keys():
        (app_id,) = struct.unpack_from("<I", data, pos)
        if app_id == 0:
            break
        (size,) = struct.unpack_from("<I", data, pos + 4)
        body_start = pos + 8
        next_pos = body_start + size
        if app_id in wanted:
            kv = _BinaryKV(data[body_start + header_size:next_pos], string_table)
            try:
                parsed = kv.parse_map()
            except (AppInfoError, IndexError, struct.error):
                parsed = {}
            result[app_id] = parsed.get("appinfo", parsed)
        pos = next_pos
    return result
