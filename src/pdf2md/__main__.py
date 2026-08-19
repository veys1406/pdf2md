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


def _set_taskbar_identity() -> None:
    """Gorev cubugunda kendi ikonumuzla, python.exe'den ayri gorunelim.

    Windows uygulamalari AppUserModelID'ye gore grupluyor; ayarlanmazsa
    gelistirme ortaminda pencere Python'un genel ikonuyla listeleniyor.
    """
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("veys1406.pdf2md")
    except Exception:
        pass


def main() -> int:
    _setup_logging()

    # EASYOCR_MODULE_PATH eklenmeden onceki surumler modelleri ~/.EasyOCR'a
    # indirmisti; 98 MB'i yeniden indirtmemek icin bir kez tasinir.
    from .core.models import migrate_legacy_easyocr

    try:
        if migrate_legacy_easyocr():
            logging.getLogger(__name__).info("EasyOCR modelleri uygulama klasörüne taşındı.")
    except Exception:
        logging.getLogger(__name__).warning("EasyOCR modelleri taşınamadı.", exc_info=True)

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("pdf2md")
    app.setOrganizationName("pdf2md")

    from .core.paths import icon_path

    icon_file = icon_path()
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))
    _set_taskbar_identity()

    from .gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
