"""Secenek paneli <-> ConversionOptions <-> QSettings gidis donusu.

Buradaki asil hedef bir regresyon: Qt, `str` tabanli enum'lari combo verisine
koyup geri verirken duz `str`'e indirgiyordu. Panelden donen secenekler dogrudan
kaydedilince `save_options` "'str' object has no attribute 'value'" ile
cokuyor, kullanici bir secenegi degistirir degistirmez arayuz patlıyordu.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pdf2md.core import settings as app_settings  # noqa: E402
from pdf2md.core.options import ConversionOptions, ExistingFile, ImageMode, OcrMode  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    from pdf2md.gui.options_panel import OptionsPanel

    return OptionsPanel(ConversionOptions())


def test_panelden_donen_secenekler_enum(panel):
    opts = panel.options(ConversionOptions())
    assert isinstance(opts.ocr_mode, OcrMode)
    assert isinstance(opts.image_mode, ImageMode)
    assert isinstance(opts.existing_file, ExistingFile)


def test_panel_secim_degisince_dogru_enum_doner(panel):
    panel.existing_combo.setCurrentIndex(
        panel.existing_combo.findData(ExistingFile.SKIP.value)
    )
    panel.ocr_combo.setCurrentIndex(panel.ocr_combo.findData(OcrMode.FORCE.value))

    opts = panel.options(ConversionOptions())
    assert opts.existing_file is ExistingFile.SKIP
    assert opts.ocr_mode is OcrMode.FORCE


def test_set_options_paneli_verilen_degerlere_getirir(panel):
    panel.set_options(
        ConversionOptions(
            ocr_mode=OcrMode.OFF,
            image_mode=ImageMode.SKIP,
            existing_file=ExistingFile.OVERWRITE,
            page_range=(3, 9),
        )
    )
    opts = panel.options(ConversionOptions())
    assert (opts.ocr_mode, opts.image_mode, opts.existing_file) == (
        OcrMode.OFF,
        ImageMode.SKIP,
        ExistingFile.OVERWRITE,
    )
    assert opts.page_range == (3, 9)


def test_panelden_donen_secenekler_kaydedilebilir(panel, monkeypatch):
    """save_options panelden geleni oldugu gibi kabul etmeli."""
    yazilan: dict[str, object] = {}

    class SahteSettings:
        def setValue(self, key, value):
            yazilan[key] = value

    monkeypatch.setattr(app_settings, "_settings", lambda: SahteSettings())
    app_settings.save_options(panel.options(ConversionOptions()))

    assert yazilan["ocr_mode"] == OcrMode.AUTO.value
    assert yazilan["existing_file"] == ExistingFile.RENAME.value


def test_save_options_duz_str_ile_de_cokmez(monkeypatch):
    """Eski bir ayar dosyasindan duz str gelirse kaydetme yine calismali."""
    yazilan: dict[str, object] = {}

    class SahteSettings:
        def setValue(self, key, value):
            yazilan[key] = value

    monkeypatch.setattr(app_settings, "_settings", lambda: SahteSettings())
    opts = ConversionOptions()
    opts.ocr_mode = "force"  # type: ignore[assignment]

    app_settings.save_options(opts)
    assert yazilan["ocr_mode"] == "force"
