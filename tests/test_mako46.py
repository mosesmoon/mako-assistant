"""MAKO Renderer 4.5/4.6: launcher location, AC/battery settings and new profile fields."""

import os
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import test_core  # noqa: E402
from mako_assistant import hostenv, mako_settings as ms  # noqa: E402
from mako_assistant import launch_options as lo  # noqa: E402
from mako_assistant.mako_config import dump_toml  # noqa: E402
from mako_assistant.service import AssistantService  # noqa: E402

POWER_CONF = '''version = 2
current_profile = "mako"

[global]
allow_fp16 = true

[[profile]]
name = "mako"
multiplier = 2
adaptive = true
target_fps = 90
flow_scale = 0.75

[profile.handheld]
target_fps = 60
gpu = ""

[profile.docked]
target_fps = 144
gpu_headroom_percent = 10
gpu = ""
'''


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.service = AssistantService(self.home / "steam", self.home / "mako",
                                        state_file=self.home / "state.json")

    def _executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n")
        path.chmod(0o755)
        return path

    def test_mako_installer_location_is_preferred(self):
        home_launcher = self._executable(self.home / ".local/bin/mako-launch")
        with mock.patch.object(hostenv, "which", return_value="/usr/bin/mako-launch"):
            self.assertEqual(self.service.mako_launch_path(), home_launcher)
        self.assertEqual(self.service.launch_option_wrapper(home_launcher), lo.MAKO_LAUNCH)

    def test_package_location_on_path(self):
        system = self._executable(self.home / "usr/bin/mako-launch")
        with mock.patch.object(hostenv, "which", return_value=str(system)):
            found = self.service.mako_launch_path()
        self.assertEqual(found, system)
        self.assertEqual(lo.add_mako("FOO=1 %command%", self.service.launch_option_wrapper(found)),
                         f"FOO=1 {system} %command%")
        self.assertTrue(lo.has_mako(f"{system} %command%"))
        self.assertEqual(lo.remove_mako(f"FOO=1 {system} %command% -dx11"), "FOO=1 %command% -dx11")

    def test_missing_everywhere_reports_the_usual_place(self):
        with mock.patch.object(hostenv, "which", return_value=None):
            self.assertEqual(self.service.mako_launch_path(), self.home / ".local/bin/mako-launch")

    def test_paths_with_spaces_are_quoted(self):
        self.assertEqual(self.service.launch_option_wrapper(Path("/opt/My Games/mako-launch")),
                         '"/opt/My Games/mako-launch"')


class PowerSetTest(unittest.TestCase):
    """Reuses the fake Steam/MAKO tree, with a default profile that has power sets."""

    def setUp(self):
        test_core.ServiceTest.setUp(self)
        self.addCleanup(test_core.ServiceTest.tearDown, self)
        (self.mako / "conf.toml").write_text(POWER_CONF)
        self.service.scan()
        self.service.install(292030)

    def conf(self):
        return tomllib.loads((self.mako / "conf.toml").read_text())

    def game(self):
        name = self.service.entries()[0].profile_name
        return next(p for p in self.conf()["profile"] if p["name"] == name)

    def test_new_game_profile_copies_power_sets(self):
        game = self.game()
        self.assertEqual(game["handheld"]["target_fps"], 60)
        self.assertEqual(game["docked"]["target_fps"], 144)
        self.assertEqual(self.conf()["current_profile"], "mako")
        self.assertIs(self.conf()["global"]["allow_fp16"], True)

    def test_each_set_shows_and_writes_its_own_values(self):
        with mock.patch.object(ms, "active_power_source", return_value="docked"):
            shown = self.service.game_settings(292030)
        self.assertEqual((shown.power_sets, shown.power_set, shown.active_power),
                         (True, "docked", "docked"))
        self.assertEqual(shown.values["target_fps"], 144)
        self.assertEqual(shown.values["gpu_headroom_percent"], 10)
        battery = self.service.game_settings(292030, "handheld")
        self.assertEqual((battery.values["target_fps"], battery.values["gpu_headroom_percent"]),
                         (60, 0))
        base = self.service.game_settings(292030, "base")
        self.assertEqual(base.values["target_fps"], 90)

        self.service.apply_game_settings(292030, {"target_fps": 50}, "handheld")
        self.service.apply_game_settings(292030, {"gpu_headroom_percent": 20}, "docked")
        game = self.game()
        self.assertEqual((game["handheld"]["target_fps"], game["docked"]["gpu_headroom_percent"]),
                         (50, 20))
        self.assertEqual(game["target_fps"], 90)              # base untouched
        self.assertNotIn("name", game["handheld"])

    def test_power_set_needs_the_tables(self):
        with self.assertRaises(ValueError):
            self.service.apply_game_settings(292030, {"target_fps": 50}, "attic")


class NewFieldsTest(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(ms.coerce("gpu_headroom_percent", 15), 15)
        for bad in (7, 25, -5, True, "10"):
            with self.assertRaises(ValueError):
                ms.coerce("gpu_headroom_percent", bad)
        self.assertEqual(ms.coerce("hdr_quality", "quality"), "quality")
        with self.assertRaises(ValueError):
            ms.coerce("hdr_quality", "ultra")
        self.assertIs(ms.coerce("adaptive_target_refresh_rate", True), True)

    def test_target_fps_is_locked_while_matching_refresh(self):
        spec = ms.FIELDS["target_fps"]
        self.assertFalse(spec.enabled({"adaptive_target_refresh_rate": True}))
        self.assertTrue(spec.enabled({"adaptive_target_refresh_rate": False}))

    def test_power_source_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def supply(name, **files):
                (root / name).mkdir()
                for key, value in files.items():
                    (root / name / key).write_text(value + "\n")

            self.assertEqual(ms.active_power_source(root), "base")         # desktop: nothing
            supply("BAT0", type="Battery", present="1")
            supply("AC", type="Mains", online="0")
            self.assertEqual(ms.active_power_source(root), "handheld")
            (root / "AC" / "online").write_text("1\n")
            self.assertEqual(ms.active_power_source(root), "docked")
            supply("hidpp_battery_0", type="Battery", scope="Device")       # a mouse
            self.assertEqual(ms.active_power_source(root), "docked")

    def test_writer_keeps_power_tables_round_trip(self):
        data = tomllib.loads(POWER_CONF)
        self.assertEqual(tomllib.loads(dump_toml(data)), data)


if __name__ == "__main__":
    unittest.main()
