"""Uygulama girisi.

ensure_env() HER SEYDEN once cagrilir: huggingface_hub bir kez import edildikten
sonra HF_HOME degisikligi dikkate alinmiyor, modeller kullanicinin ev dizinine
inmeye baslıyor.
"""

from __future__ import annotations

import logging
import sys

from .core.paths import ensure_env, logs_dir

ensure_env()


def _setup_logging() -> None:
    handlers: list[logging.Handler] = []
    try:
        handlers.append(logging.FileHandler(logs_dir() / "pdf2md.log", encoding="utf-8"))
    except OSError:
        pass
    if sys.stderr is not None:  # pencere modunda derlenen exe'de stderr yok
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> int:
    _setup_logging()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("pdf2md")
    app.setOrganizationName("pdf2md")

    from .gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
