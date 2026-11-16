"""MAKO Renderer 5.0: model picker, MAKO FG mode, Mailbox presentation, new defaults."""

import sys
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import test_core  # noqa: E402
from mako_assistant import i18n, mako_settings as ms, runtime  # noqa: E402


class ModelPickerTest(unittest.TestCase):
    def test_picker_is_derived_from_two_keys(self):
        self.assertEqual(ms.fg_model({}), "mako-fg")      # 5.0 default for unsaved profiles
        self.assertEqual(ms.fg_model({"frame_generation_model": "lossless-scaling"}), "lsfg-quality")
        self.assertEqual(ms.fg_model({"frame_generation_model": "lossless-scaling",
                                      "performance_mode": True}), "lsfg-performance")
        self.assertEqual(ms.fg_model({"performance_mode": True}), "mako-fg")

    def test_picker_writes(self):
        self.assertEqual(ms.changes_for("fg_model", "mako-fg"), {"frame_generation_model": "mako-fg"})
        self.assertEqual(ms.changes_for("fg_model", "lsfg-performance"),
                         {"frame_generation_model": "lossless-scaling", "performance_mode": True})
        with self.assertRaises(ValueError):
            ms.changes_for("fg_model", "dlss")
        self.assertNotIn("fg_model", ms.WRITABLE)
        self.assertTrue({"frame_generation_model", "performance_mode"} <= ms.WRITABLE)

    def test_new_fields(self):
        self.assertEqual(ms.coerce("mako_fg_mode", "extra-performance"), "extra-performance")
        with self.assertRaises(ValueError):
            ms.coerce("mako_fg_mode", "ultra")
        self.assertIs(ms.coerce("mailbox_presentation_compatibility", True), True)
        self.assertTrue(ms.FIELDS["mailbox_presentation_compatibility"].restart)
        self.assertFalse(ms.FIELDS["mako_fg_mode"].visible({"frame_generation_model": "lossless-scaling"}))
        self.assertTrue(ms.FIELDS["mako_fg_mode"].visible({}))

    def test_defaults_follow_5_0(self):
        values = ms.effective_values({}, {})
        self.assertEqual((values["scaling_method"], values["frame_generation_model"],
                          values["mako_fg_mode"]), ("mako", "mako-fg", "balanced"))

    def test_wording_no_longer_calls_the_switch_mako_fg(self):
        for code in i18n.CODES:
            for key, text in i18n.STRINGS[code].items():
                if key.startswith(("set_fg", "set_ultra")):
                    continue
                self.assertNotIn("Mako FG", text, (code, key))


class ApplyTest(unittest.TestCase):
    def setUp(self):
        test_core.ServiceTest.setUp(self)
        self.addCleanup(test_core.ServiceTest.tearDown, self)
        self.service.scan()
        self.service.install(292030)

    def game(self):
        name = self.service.entries()[0].profile_name
        conf = tomllib.loads((self.mako / "conf.toml").read_text())
        return next(p for p in conf["profile"] if p["name"] == name)

    def test_apply_model_mode_and_mailbox(self):
        changes = {}
        changes.update(ms.changes_for("fg_model", "lsfg-performance"))
        changes.update(ms.changes_for("mailbox_presentation_compatibility", True))
        self.service.apply_game_settings(292030, changes)
        game = self.game()
        self.assertEqual((game["frame_generation_model"], game["performance_mode"],
                          game["mailbox_presentation_compatibility"]), ("lossless-scaling", True, True))
        self.service.apply_game_settings(292030, {**ms.changes_for("fg_model", "mako-fg"),
                                                  **ms.changes_for("mako_fg_mode", "quality")})
        game = self.game()
        self.assertEqual((game["frame_generation_model"], game["mako_fg_mode"]), ("mako-fg", "quality"))
        shown = self.service.game_settings(292030)
        self.assertEqual(ms.shown_value(shown.values, "fg_model"), "mako-fg")


class LiveViewTest(unittest.TestCase):
    def describe(self, applied):
        ctx = runtime.RuntimeContext(pid=1, role="frame-generation", phase="active", updated_ms=1,
                                     frame_generation_active=True, spatial={}, applied=applied,
                                     pending={}, error=None)
        game = runtime.RunningGame(app_id=1, pids=[1], mako_loaded=True, contexts=[ctx])
        _, features, _ = runtime.describe(game)
        return features[0].detail

    def test_model_is_shown(self):
        base = {"multiplier": 2, "frame_generation_enabled": True, "effective_performance_mode": True}
        self.assertTrue(self.describe({**base, "frame_generation_model": "mako-fg"}).startswith("MAKO FG"))
        self.assertNotIn(i18n.tr("fg_perf"), self.describe({**base, "frame_generation_model": "mako-fg"}))
        self.assertIn(i18n.tr("fg_perf"), self.describe({**base, "frame_generation_model": "lossless-scaling"}))
        self.assertIn(i18n.tr("fg_perf"), self.describe(base))            # 4.x: LSFG only


if __name__ == "__main__":
    unittest.main()
