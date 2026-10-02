import string
import unittest

from mako_assistant import i18n


def _fields(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class TranslationTest(unittest.TestCase):
    def test_every_language_is_complete(self):
        english = i18n.STRINGS["en"]
        for code in i18n.CODES:
            table = i18n.STRINGS[code]
            with self.subTest(language=code):
                self.assertEqual(set(table) - set(english), set(), "unknown keys")
                self.assertEqual(set(english) - set(table), set(), "missing keys")
                for key, text in table.items():
                    self.assertEqual(_fields(text), _fields(english[key]), key)

    def test_match_language(self):
        cases = {"zh_TW.UTF-8": "zh_TW", "zh_HK": "zh_TW", "zh_CN.UTF-8": "zh_CN",
                 "ja_JP.UTF-8": "ja", "pt_BR": "en", "hi_IN": "hi", "ms_MY": "ms", "C": "en"}
        for raw, expected in cases.items():
            self.assertEqual(i18n.match_language(raw), expected, raw)

    def test_fallback(self):
        i18n.set_language("ja")
        self.assertEqual(i18n.tr("btn_remove"), "削除")
        i18n.set_language("en")
