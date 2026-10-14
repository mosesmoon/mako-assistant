"""End-to-end check of the settings panel against a real service and a fake Steam/MAKO tree."""

import os
import time
import tomllib
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:  # PyQt6 is only needed for the interface
    QApplication = None

import test_core


@unittest.skipIf(QApplication is None, "PyQt6 not installed")
class SettingsPanelTest(unittest.TestCase):
    def setUp(self):
        test_core.ServiceTest.setUp(self)   # the same fake Steam library and MAKO config
        from mako_assistant import ui
        self.ui = ui
        self.app = QApplication.instance() or QApplication([])
        ui.prepare_app(self.app, self.service)
        self.service.scan()
        self.service.install(292030)
        self.window = ui.MainWindow(self.service, self.service.entries(), autostart=False)
        self.window.resize(1400, 900)
        self.window.show()

    def tearDown(self):
        self.window.pool.waitForDone(5000)
        self.window.close()
        test_core.ServiceTest.tearDown(self)

    def wait(self, condition, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def test_expand_edit_and_apply(self):
        card = self.window._cards[292030]
        card.chevron.click()
        panel = card.panel
        self.assertTrue(self.wait(lambda: panel.base is not None), "settings never loaded")
        self.assertFalse(panel.apply_btn.isEnabled())

        panel._on_change("adaptive", True)
        panel._on_change("adaptive_max_multiplier", 0)        # 0x = live pause
        panel._on_change("target_fps", 144)
        panel._on_change("gamescope_vrr_mode", "off")
        adaptive = next(s for s in panel.sections if s.section.key == "set_sec_adaptive")
        self.assertTrue(adaptive.isVisibleTo(panel))
        self.assertTrue(panel.apply_btn.isEnabled())

        panel.apply_btn.click()
        self.assertTrue(self.wait(lambda: not panel.pending and not self.window.busy),
                        "apply never finished")
        conf = tomllib.loads((self.mako / "conf.toml").read_text())
        game = next(p for p in conf["profile"] if p["name"] == panel.profile)
        self.assertEqual((game["adaptive"], game["target_fps"], game["gamescope_vrr_mode"]),
                         (True, 144, "off"))
        self.assertIs(game["frame_generation_enabled"], False)
        self.assertNotIn("adaptive_max_multiplier", game)       # 0x only pauses
        self.assertFalse(panel.apply_btn.isEnabled())

    def test_unsaved_edits_survive_a_refresh(self):
        card = self.window._cards[292030]
        card.chevron.click()
        self.assertTrue(self.wait(lambda: card.panel.base is not None))
        card.panel._on_change("flow_scale", 0.5)
        self.window.populate()                                   # e.g. after a rescan
        panel = self.window._cards[292030].panel
        self.assertIsNotNone(panel)
        self.assertTrue(self.wait(lambda: panel.base is not None))
        self.assertEqual(panel.pending, {"flow_scale": 0.5})

    def test_language_switch_keeps_open_panels_and_edits(self):
        card = self.window._cards[292030]
        card.chevron.click()
        self.assertTrue(self.wait(lambda: card.panel.base is not None))
        card.panel._on_change("target_fps", 75)
        index = self.ui.i18n.CODES.index("ja")
        try:
            self.window.language_box.setCurrentIndex(index)
            replacement = self.app.main_window
            self.assertIsNot(replacement, self.window)
            panel = replacement._cards[292030].panel
            self.assertIsNotNone(panel)
            self.assertTrue(self.wait(lambda: panel.base is not None))
            self.assertEqual(panel.pending, {"target_fps": 75})
            self.assertEqual(panel.apply_btn.text(), "適用")
        finally:
            self.ui.i18n.set_language("en")
            replacement = getattr(self.app, "main_window", None)
            if replacement is not None and replacement is not self.window:
                replacement.pool.waitForDone(5000)
                replacement.poll_timer.stop()
                replacement.close()

    def test_game_without_profile_explains_why(self):
        self.service.uninstall(292030, remove_config=True)
        self.window.entries = self.service.entries()
        self.window._settings.clear()
        self.window.populate()
        card = self.window._cards[292030]
        card.chevron.click()
        self.assertTrue(self.wait(lambda: card.panel.message.isVisibleTo(card.panel)
                                  and card.panel.base is None
                                  and card.panel.message.text() != self.ui.tr("set_loading")))
        self.assertEqual(card.panel.message.text(), self.ui.tr("set_no_profile"))


if __name__ == "__main__":
    unittest.main()
