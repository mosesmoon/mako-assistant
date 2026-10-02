"""Talk to the running Steam client through its CEF remote-debugging port.

Steam only reads ``localconfig.vdf`` at start-up and rewrites it on exit, so
launch options edited on disk while Steam runs are silently lost. When the
debugging port is open (Decky Loader enables it), the assistant evaluates
``SteamClient.Apps.SetAppLaunchOptions`` inside Steam's SharedJSContext, the
same mechanism Decky plugins use. Only the standard library is required.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import urllib.parse
import urllib.request
from typing import Any, Optional

DEFAULT_PORTS = (8080,)
_TARGET_TITLE = "SharedJSContext"


class CefError(RuntimeError):
    pass


class _WebSocket:
    """Minimal RFC 6455 client: text frames, client masking, no extensions."""

    def __init__(self, url: str, timeout: float = 5.0) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "ws":
            raise CefError(f"unsupported websocket scheme: {parsed.scheme}")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        self._sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self._sock.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise CefError("websocket handshake closed")
            response += chunk
        header, self._buffer = response.split(b"\r\n\r\n", 1)
        if b" 101 " not in header.split(b"\r\n", 1)[0]:
            raise CefError("websocket handshake rejected")

    def send_text(self, text: str) -> None:
        payload = text.encode()
        frame = bytearray([0x81])
        length = len(payload)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 1 << 16:
            frame.append(0x80 | 126)
            frame += struct.pack("!H", length)
        else:
            frame.append(0x80 | 127)
            frame += struct.pack("!Q", length)
        mask = os.urandom(4)
        frame += mask
        frame += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(frame)

    def _read(self, count: int) -> bytes:
        while len(self._buffer) < count:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise CefError("websocket closed")
            self._buffer += chunk
        data, self._buffer = self._buffer[:count], self._buffer[count:]
        return data

    def recv_text(self) -> str:
        message = b""
        while True:
            first, second = self._read(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                (length,) = struct.unpack("!H", self._read(2))
            elif length == 127:
                (length,) = struct.unpack("!Q", self._read(8))
            if second & 0x80:
                mask = self._read(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(length)))
            else:
                payload = self._read(length)
            if opcode == 0x8:
                raise CefError("websocket closed by Steam")
            if opcode == 0x9:  # ping -> ignore, CEF does not require pong here
                continue
            if opcode in (0x0, 0x1, 0x2):
                message += payload
                if first & 0x80:
                    return message.decode("utf-8", errors="replace")

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class SteamCef:
    def __init__(self, ports: tuple[int, ...] = DEFAULT_PORTS, timeout: float = 3.0) -> None:
        self.ports = ports
        self.timeout = timeout

    def _debugger_url(self) -> Optional[str]:
        for port in self.ports:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json", timeout=self.timeout
                ) as response:
                    targets = json.load(response)
            except (OSError, ValueError):
                continue
            for target in targets:
                if target.get("title") == _TARGET_TITLE and target.get("webSocketDebuggerUrl"):
                    return target["webSocketDebuggerUrl"]
        return None

    def available(self) -> bool:
        return self._debugger_url() is not None

    def evaluate(self, expression: str) -> Any:
        url = self._debugger_url()
        if url is None:
            raise CefError("Steam CEF debugger is not reachable")
        ws = _WebSocket(url, timeout=self.timeout + 5)
        try:
            ws.send_text(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True,
                },
            }))
            while True:
                message = json.loads(ws.recv_text())
                if message.get("id") == 1:
                    break
        finally:
            ws.close()
        if "error" in message:
            raise CefError(str(message["error"]))
        result = message.get("result", {})
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            text = details.get("exception", {}).get("description") or details.get("text")
            raise CefError(f"Steam rejected the request: {text}")
        return result.get("result", {}).get("value")

    def set_launch_options(self, app_id: int, options: str) -> None:
        self.evaluate(
            f"SteamClient.Apps.SetAppLaunchOptions({int(app_id)}, {json.dumps(options)}); true"
        )
