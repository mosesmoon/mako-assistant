import sys


def _self_test() -> int:
    """Used by the AppImage build: prove the bundled Python, Qt and translations work."""
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication

    from . import __version__, i18n, ui
    from .service import AssistantService  # noqa: F401

    app = QApplication(sys.argv[:1])
    app.setStyleSheet(ui.STYLE)
    qt_ok = []
    for code in i18n.CODES:
        i18n.set_language(code)
        ui.install_translations(app)
        if QCoreApplication.translate("QLineEdit", "&Copy") != "&Copy":
            qt_ok.append(code)
    print(f"MAKO Assistant {__version__} self-test OK (Qt platform: {app.platformName()}, "
          f"UI languages: {len(i18n.CODES)}, Qt translations: {', '.join(qt_ok) or 'none'})")
    return 0


if "--self-test" in sys.argv:
    sys.exit(_self_test())

from .ui import main  # noqa: E402

sys.exit(main())
