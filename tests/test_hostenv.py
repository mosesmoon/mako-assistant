"""Host access used by the Flatpak build: the host /proc report and command wrapping."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mako_assistant import hostenv, runtime  # noqa: E402


class HostEnvTest(unittest.TestCase):
    def setUp(self):
        env = dict(os.environ, SteamAppId="424242", SDL_AUDIODRIVER="alsa")
        self.child = subprocess.Popen(["sleep", "30"], env=env)
        self.addCleanup(self.child.wait)
        self.addCleanup(self.child.kill)

    def test_shell_report_matches_reading_proc_directly(self):
        # Outside Flatpak hostenv.run() runs the same script locally, so the
        # report the Flatpak build relies on can be checked against /proc.
        reported = {p.pid: p for p in hostenv.host_processes()}
        local = {p.pid: p for p in runtime._local_processes(Path("/proc"))}
        self.assertIn(self.child.pid, reported)
        mine = reported[self.child.pid]
        self.assertEqual(mine.env, {"SteamAppId": "424242", "SDL_AUDIODRIVER": "alsa"})
        self.assertEqual(mine.start_ticks, local[self.child.pid].start_ticks)
        self.assertEqual(mine.libraries, local[self.child.pid].libraries)
        self.assertIsNotNone(mine.start_ticks)

    def test_detect_running_from_a_host_report(self):
        report = hostenv.host_processes()
        games = runtime.detect_running(processes=report, state_dir=Path("/nonexistent"))
        self.assertIn(424242, games)
        self.assertIn(self.child.pid, games[424242].pids)
        self.assertFalse(games[424242].mako_loaded)

    def test_parse_report(self):
        text = ("@12\nSteamAppId=70\nSDL_AUDIODRIVER=alsa\nOTHER=x\n+libmako-render.so\n"
                "=12 (my game) S 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 777 19\n@oops\n+vkbasalt\n")
        [info] = hostenv.parse_process_report(text)
        self.assertEqual((info.pid, info.env, info.libraries, info.start_ticks),
                         (12, {"SteamAppId": "70", "SDL_AUDIODRIVER": "alsa"},
                          {"libmako-render.so"}, 777))

    def test_commands_go_through_flatpak_spawn_inside_flatpak(self):
        with mock.patch.object(hostenv, "IN_FLATPAK", True):
            self.assertEqual(hostenv.host_argv(["mako-cli", "validate"]),
                             ["flatpak-spawn", "--host", "mako-cli", "validate"])
            with mock.patch.dict(os.environ, {"HOST_XDG_CONFIG_HOME": "/home/u/.cfg",
                                              "XDG_CONFIG_HOME": "/home/u/.var/app/x/config"}):
                self.assertEqual(hostenv.xdg_config_home(), Path("/home/u/.cfg"))
        self.assertEqual(hostenv.host_argv(["steam"]), ["steam"])
        self.assertEqual(hostenv.which("sh"), subprocess.run(
            ["sh", "-c", "command -v sh"], capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    unittest.main()
