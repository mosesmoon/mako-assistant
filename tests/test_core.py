import json
import struct
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from mako_assistant import launch_options as lo
from mako_assistant import vdf_text
from mako_assistant.appinfo import read_appinfo
from mako_assistant.executables import detect_executables, process_names
from mako_assistant.mako_config import MakoConfig, dump_toml
from mako_assistant.service import AssistantService
from mako_assistant.steam_cef import CefError

M = "~/.local/bin/mako-launch %command%"


class LaunchOptionsTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(lo.add_mako(""), M)
        self.assertEqual(lo.add_mako("%command%"), M)
        self.assertEqual(lo.add_mako("FOO=1 %command% -dx11"), f"FOO=1 {M} -dx11")
        self.assertEqual(lo.add_mako("-dx11"), f"{M} -dx11")
        self.assertEqual(lo.add_mako(M), M)

    def test_remove(self):
        self.assertEqual(lo.remove_mako(M), "")
        self.assertEqual(lo.remove_mako(f"FOO=1 {M} -dx11"), "FOO=1 %command% -dx11")
        self.assertEqual(lo.remove_mako(f"{M} -dx11"), "%command% -dx11")
        self.assertEqual(lo.remove_mako("/home/a/.local/bin/mako-launch -- %command%"), "")
        self.assertEqual(lo.remove_mako("gamemoderun %command%"), "gamemoderun %command%")

    def test_roundtrip_preserves_user_options(self):
        for original in ("", "FOO=1 %command%", "gamemoderun %command% -novid"):
            back = lo.remove_mako(lo.add_mako(original))
            self.assertEqual(back or "", original if original != "%command%" else "")

    def test_has_mako(self):
        self.assertTrue(lo.has_mako(M))
        self.assertFalse(lo.has_mako("not-mako-launcher %command%"))


class VdfTest(unittest.TestCase):
    def test_roundtrip(self):
        text = '"Root"\n{\n\t"apps"\n\t{\n\t\t"10"\n\t\t{\n\t\t\t"LaunchOptions"\t\t"A=\\"b\\" %command%"\n\t\t}\n\t}\n}\n'
        data = vdf_text.loads(text)
        self.assertEqual(data["Root"]["apps"]["10"]["LaunchOptions"], 'A="b" %command%')
        self.assertEqual(vdf_text.loads(vdf_text.dumps(data)), data)


class TomlTest(unittest.TestCase):
    def test_dump_roundtrip(self):
        data = {"version": 2, "global": {"allow_fp16": True, "dll": 'C:\\x "y"'},
                "profile": [{"name": "a", "active_in": ["x.exe", "y"], "flow_scale": 0.75,
                             "multiplier": 2}]}
        self.assertEqual(tomllib.loads(dump_toml(data, ["# keep"])), data)
        self.assertIn("# keep", dump_toml(data, ["# keep"]))


def _write_appinfo_v29(path: Path, apps: dict):
    strings: list[str] = []

    def key(k):
        if k not in strings:
            strings.append(k)
        return struct.pack("<I", strings.index(k))

    def kv(node):
        out = b""
        for k, v in node.items():
            if isinstance(v, dict):
                out += b"\x00" + key(k) + kv(v)
            else:
                out += b"\x01" + key(k) + str(v).encode() + b"\x00"
        return out + b"\x08"

    body = b""
    for app_id, info in apps.items():
        payload = b"\x00" * 60 + b"\x00" + key("appinfo") + kv(info) + b"\x08"
        body += struct.pack("<II", app_id, len(payload)) + payload
    body += struct.pack("<I", 0)
    table_offset = 16 + len(body)
    table = struct.pack("<I", len(strings)) + b"".join(s.encode() + b"\x00" for s in strings)
    path.write_bytes(struct.pack("<IIq", 0x07564429, 1, table_offset) + body + table)


class FakeCef:
    def evaluate(self, _):
        raise CefError("offline")

    def set_launch_options(self, *_):
        raise CefError("offline")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.steam = root / "Steam"
        common = self.steam / "steamapps" / "common"
        (common / "Witcher" / "bin" / "x64_dx12").mkdir(parents=True)
        (common / "Witcher" / "redprelauncher.exe").write_bytes(b"MZ")
        (common / "Witcher" / "bin" / "x64_dx12" / "witcher3.exe").write_bytes(b"MZ" * 5_000_000)
        (common / "Proton").mkdir()
        (self.steam / "steamapps" / "appmanifest_292030.acf").write_text(
            '"AppState"\n{\n"appid" "292030"\n"name" "Witcher"\n"installdir" "Witcher"\n}\n')
        (self.steam / "steamapps" / "appmanifest_1.acf").write_text(
            '"AppState"\n{\n"appid" "1"\n"name" "Proton 9"\n"installdir" "Proton"\n}\n')
        (self.steam / "appcache").mkdir()
        _write_appinfo_v29(self.steam / "appcache" / "appinfo.vdf", {
            1: {"common": {"name": "Proton 9", "type": "Tool"}},
            292030: {"common": {"name": "The Witcher 3", "type": "Game",
                                "name_localized": {"tchinese": "巫師3：狂獵",
                                                   "japanese": "ウィッチャー３"}},
                     "config": {"installdir": "Witcher",
                                "launch": {"0": {"executable": "redprelauncher.exe",
                                                 "config": {"oslist": "windows"}}}}},
        })
        cfg = self.steam / "userdata" / "42" / "config"
        cfg.mkdir(parents=True)
        cfg.joinpath("localconfig.vdf").write_text(
            '"UserLocalConfigStore"\n{\n"Software"\n{\n"Valve"\n{\n"Steam"\n{\n"apps"\n{\n'
            '"292030"\n{\n"LaunchOptions" "FOO=1 %command%"\n}\n}\n}\n}\n}\n}\n')
        self.mako = root / "mako-render"
        self.mako.mkdir()
        (self.mako / "conf.toml").write_text(
            'version = 2\n\n[global]\nallow_fp16 = true\n\n[[profile]]\nname = "mako"\n'
            'multiplier = 2\nflow_scale = 0.75\n')
        patcher = mock.patch("mako_assistant.mako_config.mako_cli", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        running = mock.patch("mako_assistant.steam.SteamInstallation.is_running", return_value=False)
        running.start()
        self.addCleanup(running.stop)
        self.service = AssistantService(self.steam, self.mako, FakeCef(), root / "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_appinfo_and_detection(self):
        info = read_appinfo(self.steam / "appcache" / "appinfo.vdf", [292030])[292030]
        paths = detect_executables(self.steam / "steamapps/common/Witcher", info)
        self.assertEqual(process_names(paths), ["witcher3.exe"])

    def test_localized_names(self):
        from mako_assistant import i18n
        entry = self.service.scan()[0][0]
        try:
            for code, expected in (("zh_TW", "巫師3：狂獵"), ("ja", "ウィッチャー３"),
                                   ("de", "The Witcher 3"), ("hi", "The Witcher 3")):
                i18n.set_language(code)
                self.assertEqual(entry.display_name, expected)
            self.assertTrue(entry.matches("狂獵") and entry.matches("witcher"))
        finally:
            i18n.set_language("en")

    def test_install_and_uninstall(self):
        entries, _ = self.service.scan()
        self.assertEqual([e.app_id for e in entries], [292030])
        self.assertFalse(entries[0].has_mako)

        self.service.install(292030)
        entry = self.service.entries()[0]
        self.assertTrue(entry.has_mako)
        self.assertEqual(entry.launch_options, f"FOO=1 {M}")
        self.assertEqual(entry.profile_processes, ["witcher3.exe"])
        meta = json.loads((self.mako / "profile-metadata.json").read_text())["profiles"]
        self.assertEqual(meta[entry.profile_name]["steam_app_id"], "292030")
        self.assertEqual(meta[entry.profile_name]["kind"], "game")
        conf = tomllib.loads((self.mako / "conf.toml").read_text())
        self.assertEqual(conf["profile"][1]["multiplier"], 2)

        self.service.uninstall(292030, remove_config=False)
        entry = self.service.entries()[0]
        self.assertFalse(entry.has_mako)
        self.assertEqual(entry.launch_options, "FOO=1 %command%")
        self.assertIsNotNone(entry.profile_name)

        self.service.uninstall(292030, remove_config=True)
        self.assertIsNone(self.service.entries()[0].profile_name)
        conf = tomllib.loads((self.mako / "conf.toml").read_text())
        self.assertEqual([p["name"] for p in conf["profile"]], ["mako"])

    def test_sync_updates_only_managed_and_keeps_aliases(self):
        self.service.scan()
        self.service.install(292030)
        config = MakoConfig(self.mako)
        config.load()
        name = config.profile_for_app(292030).name
        # User adds a manual alias in MAKO UI.
        for profile in config.profiles():
            if profile["name"] == name:
                profile["active_in"] = ["witcher3.exe", "alias.exe"]
        config.save()
        # Game update moves the binary.
        common = self.steam / "steamapps/common/Witcher/bin"
        (common / "x64_dx12" / "witcher3.exe").unlink()
        (common / "x64_new").mkdir()
        (common / "x64_new" / "witcher3_v2.exe").write_bytes(b"MZ" * 5_000_000)

        _, changes = self.service.scan()
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].after, ["alias.exe", "witcher3_v2.exe"])
        self.assertTrue(changes[0].new_paths[0].endswith("x64_new/witcher3_v2.exe"))


if __name__ == "__main__":
    unittest.main()
