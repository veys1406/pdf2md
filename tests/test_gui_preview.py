"""Onizleme panelinin tema ve icerik davranisi."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pdf2md.gui.preview import render_markdown, split_frontmatter  # noqa: E402

MD = """---
kaynak: "ders.pdf"
sayfa_sayisi: 2
---

# Başlık

| A | B |
|---|---|
| 1 | 2 |

`kod`
"""


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    from pdf2md.gui.preview import PreviewPanel

    p = PreviewPanel()
    p.set_dark(True)
    return p


def test_tema_degisince_onizleme_yeniden_render_edilir(panel):
    """QTextBrowser.toHtml() eski renkleri inline gomuyor; kaynaktan render sart.

    Aksi halde koyu temada uretilen tablo basliklari ve kod bloklari acik temada
    koyu zeminde koyu yaziyla, yani okunamaz halde kaliyordu.
    """
    panel.show_markdown(MD, None, "bilgi")
    koyu = panel.html_view.toHtml()

    panel.set_dark(False)
    acik = panel.html_view.toHtml()

    assert koyu != acik
    assert "#1a1a1c" not in acik  # koyu tema yuzey rengi
    assert "#f0f0f1" in acik      # acik tema yuzey rengi


def test_tema_degisimi_icerigi_kaybetmez(panel):
    panel.show_markdown(MD, None, "bilgi")
    panel.set_dark(False)

    assert panel.raw_view.toPlainText().startswith("---")
    assert panel.info.text() == "bilgi"


def test_bos_panelde_tema_degisimi_cokmez(panel):
    panel.clear()
    panel.set_dark(False)
    assert panel.html_view.toPlainText().strip() == ""


def test_temizleme_kaynagi_da_unutur(panel):
    panel.show_markdown(MD, None, "bilgi")
    panel.clear()
    panel.set_dark(True)
    assert panel.html_view.toPlainText().strip() == ""


# -- saf yardimcilar -------------------------------------------------------


def test_frontmatter_ayrilir():
    meta, body = split_frontmatter(MD)
    assert meta["kaynak"] == "ders.pdf"
    assert body.startswith("# Başlık")


def test_frontmatter_yoksa_govde_bozulmaz():
    meta, body = split_frontmatter("# Sadece başlık\n")
    assert meta == {}
    assert body == "# Sadece başlık\n"


def test_tablo_html_olarak_render_edilir():
    html = render_markdown("| A | B |\n|---|---|\n| 1 | 2 |")
    assert "<table>" in html
