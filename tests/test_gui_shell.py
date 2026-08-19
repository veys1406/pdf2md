"""Ana pencerenin kabugu: ikon, kisayollar ve varlik dosyalari."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pdf2md.core.paths import icon_path, logo_path  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def window(app):
    from pdf2md.gui.main_window import MainWindow

    w = MainWindow()
    w._models_checked = True  # sihirbaz acilmasin
    return w


def test_varlik_dosyalari_yerinde():
    """Logo ve ikon depoya dahil; eksikse exe ikonsuz derlenir."""
    assert icon_path().exists(), "assets/icon.ico yok — packaging/make_icon.py calistirin"
    assert logo_path().exists(), "assets/logo.png yok — packaging/make_icon.py calistirin"


def test_pencere_ikonu_ayarli(window):
    assert not window.windowIcon().isNull()


def test_kisayollar_kayitli(window):
    from PySide6.QtGui import QKeySequence, QShortcut

    kayitli = {s.key().toString() for s in window.findChildren(QShortcut)}
    for beklenen in ("Ctrl+O", "Ctrl+Shift+O", "Esc", "Ctrl+L", "Ctrl+M", "F1"):
        assert QKeySequence(beklenen).toString() in kayitli, beklenen


def test_donustur_kisayolu_var(window):
    from PySide6.QtGui import QShortcut

    kayitli = {s.key().toString() for s in window.findChildren(QShortcut)}
    assert any("Return" in k or "Enter" in k for k in kayitli)


def test_bos_kuyrukta_donustur_kapali(window):
    assert not window.convert_btn.isEnabled()


def test_secenek_bolumu_kapali_baslar(window):
    assert not window.options_section.is_expanded()
