"""Elle cizilen kontrollerin testleri.

Bu dosyanin varlik sebebi somut bir hata: `SoftButton.paintEvent` icinde
`QFont.setWeight(600)` cagriliyordu; PySide6 int kabul etmedigi icin paintEvent
TypeError ile kesiliyor ve butonlar arayuzde BOS kutular olarak ciziliyordu.
Qt boyle bir hatayi stderr'e yazip yutuyor, pencere modunda derlenen exe'de
stderr de yok. Bu yuzden her cizim yolu burada bir kez render edilerek
denetleniyor.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pdf2md.gui import theme  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _render(widget) -> bool:
    """Widget'i bir pixmap'e ciz; paintEvent istisna atarsa test cokmeli."""
    from PySide6.QtGui import QPixmap

    widget.resize(180, 40)
    pixmap = QPixmap(widget.size())
    widget.render(pixmap)
    return not pixmap.isNull()


# -- SoftButton ------------------------------------------------------------


@pytest.mark.parametrize("variant", ["primary", "ghost", "quiet"])
def test_buton_her_variantta_cizilebilir(app, variant):
    from pdf2md.gui.animations import SoftButton

    button = SoftButton("Dönüştür", variant)
    button.set_colors(theme.palette(True))
    assert _render(button)


def test_buton_devre_disi_da_cizilebilir(app):
    from pdf2md.gui.animations import SoftButton

    button = SoftButton("Kapalı")
    button.set_colors(theme.palette(False))
    button.setEnabled(False)
    assert _render(button)


def _enter_event():
    """Qt6 enterEvent'e QEnterEvent bekliyor, duz QEvent kabul etmiyor."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QEnterEvent

    point = QPointF(5, 5)
    return QEnterEvent(point, point, point)


def test_hover_animasyonu_degeri_tasir(app):
    from PySide6.QtCore import QEvent
    from pdf2md.gui.animations import SoftButton

    button = SoftButton("Test")
    button.set_colors(theme.palette(True))
    assert button._hover == 0.0

    button.enterEvent(_enter_event())
    button._hover_anim.setCurrentTime(button._hover_anim.duration())
    assert button._hover == pytest.approx(1.0, abs=0.01)

    button.leaveEvent(QEvent(QEvent.Type.Leave))
    button._hover_anim.setCurrentTime(button._hover_anim.duration())
    assert button._hover == pytest.approx(0.0, abs=0.01)


def test_devre_disi_buton_hoverda_canlanmaz(app):
    from pdf2md.gui.animations import SoftButton

    button = SoftButton("Test")
    button.setEnabled(False)
    button.enterEvent(_enter_event())
    assert button._hover == 0.0


# -- renk karistirma -------------------------------------------------------


def test_mix_uclarda_kaynak_renkleri_verir():
    from pdf2md.gui.animations import mix

    assert mix("#000000", "#ffffff", 0.0).name() == "#000000"
    assert mix("#000000", "#ffffff", 1.0).name() == "#ffffff"
    assert mix("#000000", "#ffffff", 0.5).red() == 128


def test_mix_araligin_disini_kirpar():
    from pdf2md.gui.animations import mix

    assert mix("#000000", "#ffffff", -2.0).name() == "#000000"
    assert mix("#000000", "#ffffff", 5.0).name() == "#ffffff"


# -- ilerleme cubugu -------------------------------------------------------


def test_ilerleme_ileri_giderken_animasyonlu(app):
    from pdf2md.gui.animations import AnimatedProgressBar

    bar = AnimatedProgressBar()
    bar.setRange(0, 100)
    bar.animate_to(80)
    bar._anim.setCurrentTime(bar._anim.duration())
    assert bar.value() == 80


def test_ilerleme_geri_giderken_aninda_sifirlanir(app):
    """Iptal/yeniden deneme sonrasi cubuk geriye dogru sunmemeli."""
    from pdf2md.gui.animations import AnimatedProgressBar

    bar = AnimatedProgressBar()
    bar.setRange(0, 100)
    bar.setValue(70)
    bar.animate_to(0)
    assert bar.value() == 0


# -- katlanabilir bolum ----------------------------------------------------


def test_katlanabilir_bolum_kapali_baslar(app):
    from PySide6.QtWidgets import QLabel
    from pdf2md.gui.animations import CollapsibleSection

    section = CollapsibleSection("SEÇENEKLER", QLabel("içerik"))
    assert not section.is_expanded()
    assert section._content.maximumHeight() == 0


def test_katlanabilir_bolum_acilip_kapanir(app):
    from PySide6.QtWidgets import QLabel
    from pdf2md.gui.animations import CollapsibleSection

    content = QLabel("içerik")
    section = CollapsibleSection("SEÇENEKLER", content)

    section.toggle()
    section._anim.setCurrentTime(section._anim.duration())
    assert section.is_expanded()
    assert content.maximumHeight() > 0

    section.toggle()
    section._anim.setCurrentTime(section._anim.duration())
    assert not section.is_expanded()
    assert content.maximumHeight() == 0


# -- birakma alani ---------------------------------------------------------


def test_birakma_alani_cizilebilir(app):
    from pdf2md.gui.drop_zone import DropZone

    zone = DropZone()
    zone.set_colors(theme.palette(True))
    assert _render(zone)


def test_birakma_alani_kompakt_moda_gecer(app):
    from pdf2md.gui.drop_zone import DropZone

    zone = DropZone()
    zone.set_colors(theme.palette(True))
    zone.set_compact(True)
    zone._height_anim.setCurrentTime(zone._height_anim.duration())
    assert zone.height() < 128

    zone.set_compact(False)
    zone._height_anim.setCurrentTime(zone._height_anim.duration())
    assert zone.height() == 128


# -- tema ------------------------------------------------------------------


@pytest.mark.parametrize("dark", [True, False])
def test_paletler_ayni_anahtarlari_tasir(dark):
    """Eksik anahtar, elle cizilen kontrollerde sessizce yanlis renk demek."""
    assert set(theme.DARK) == set(theme.LIGHT)
    assert theme.stylesheet(dark)  # format() eksik anahtarda patlar
