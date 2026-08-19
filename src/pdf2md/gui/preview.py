"""Markdown onizleme paneli.

QWebEngineView bilerek kullanilmiyor: paketlenmis exe'ye ~150 MB ekliyor.
markdown-it-py ile uretilen HTML, QTextBrowser'in destekledigi alt kumede
(baslik, tablo, liste, gorsel, kod) yeterince iyi goruntuleniyor.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from ..core.paths import logo_path
from ..i18n import tr
from . import theme
from .animations import SoftButton, fade_in
from .queue_view import reveal


def split_frontmatter(md: str) -> tuple[dict[str, str], str]:
    """YAML frontmatter'i govdeden ayir.

    Onizlemede ham `---` blogu dev bir baslik gibi gorunuyordu; meta veriyi
    ayirip ustte kucuk bir seritte gosteriyoruz. Ham Markdown sekmesi dosyanin
    aynisini gosterdiginden orada dokunulmaz.
    """
    if not md.startswith("---\n"):
        return {}, md

    end = md.find("\n---", 4)
    if end == -1:
        return {}, md

    meta: dict[str, str] = {}
    for line in md[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip().strip('"')

    body = md[end + 4:].lstrip("\n")
    return meta, body


def render_markdown(md: str) -> str:
    """Markdown -> HTML. markdown-it yoksa duz metne duser."""
    try:
        from markdown_it import MarkdownIt

        return MarkdownIt("commonmark").enable("table").enable("strikethrough").render(md)
    except Exception:
        return "<pre>" + md.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"


class PreviewPanel(QFrame):
    """Sekmeli onizleme: render edilmis HTML ve ham markdown.

    Panelin tamami tek bir yuvarlak kart; icindeki metin gorunumleri kendi
    cercevelerini cizmez (bkz. theme.QFrame#previewCard kurallari).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCard")
        self._dark = True
        self._md_path: Path | None = None
        self._md = ""
        self._info = ""

        self.tabs = QTabWidget()

        self.html_view = QTextBrowser()
        self.html_view.setOpenExternalLinks(False)
        self.html_view.setOpenLinks(False)

        self.raw_view = QPlainTextEdit()
        self.raw_view.setReadOnly(True)
        self.raw_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.tabs.addTab(self.html_view, tr.TAB_PREVIEW)
        self.tabs.addTab(self.raw_view, tr.TAB_RAW)

        self.info = QLabel(tr.PREVIEW_EMPTY)
        self.info.setObjectName("statTokens")

        self.copy_btn = SoftButton(tr.BTN_COPY)
        self.copy_btn.clicked.connect(self._copy)
        self.folder_btn = SoftButton(tr.BTN_SHOW_IN_FOLDER)
        self.folder_btn.clicked.connect(self._reveal)

        # Panel dar oldugunda tek satirda bilgi + iki buton sigmiyordu;
        # bilgi ustte, butonlar altta sagda duruyor.
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch(1)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.folder_btn)

        bar = QVBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)
        bar.addWidget(self.info)
        bar.addLayout(buttons)

        hairline = QLabel()
        hairline.setObjectName("hairline")
        hairline.setFixedHeight(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(hairline)
        layout.addLayout(bar)

        # Metin gorunumleri ve sekme cubugu kendi genisliklerini dayatinca panel
        # 730 px minimum istiyordu ve dar ekranda pencerenin disina tasiyordu.
        for widget in (self.tabs, self.html_view, self.raw_view):
            widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            widget.setMinimumWidth(0)
        self.info.setWordWrap(True)
        self.info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(260)

        self.clear()

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self.html_view.document().setDefaultStyleSheet(theme.preview_css(dark))
        # toHtml() ile yeniden yazmak ise yaramiyor: QTextBrowser o cikti icine
        # eski renkleri inline gomuyor, tema degisince tablo basliklari ve kod
        # bloklari koyu zeminde koyu yaziyla kaliyordu. Kaynak markdown'dan
        # bastan render ediliyor.
        if self._md:
            self.show_markdown(self._md, self._md_path, self._info, animate=False)
        else:
            self.html_view.setHtml(self._empty_html())

    def _empty_html(self) -> str:
        """Bos durum: ortada logo ve tek satirlik aciklama."""
        logo = logo_path()
        if not logo.exists():
            return f'<p class="meta" align="center">{tr.PREVIEW_EMPTY}</p>'
        src = QUrl.fromLocalFile(str(logo)).toString()
        return (
            f'<div align="center" style="margin-top:48px">'
            f'<img src="{src}" width="56" height="56"/>'
            f'<p class="meta">{tr.PREVIEW_EMPTY}</p>'
            f"</div>"
        )

    def clear(self) -> None:
        self._md_path = None
        self._md = ""
        self._info = ""
        self.html_view.document().setDefaultStyleSheet(theme.preview_css(self._dark))
        self.html_view.setHtml(self._empty_html())
        self.raw_view.setPlainText("")
        self.info.setText("")
        self.copy_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)

    def show_markdown(
        self, md: str, md_path: Path | None, info: str = "", animate: bool = True
    ) -> None:
        self._md_path = md_path
        self._md = md
        self._info = info
        self.raw_view.setPlainText(md)

        # Gorsel linkleri relatif; taban yolu vermezsek onizlemede gorunmezler
        if md_path is not None:
            self.html_view.setSearchPaths([str(md_path.parent)])
            self.html_view.document().setBaseUrl(QUrl.fromLocalFile(str(md_path.parent) + "/"))

        meta, body = split_frontmatter(md)
        header = ""
        if meta:
            parts = [f"{k}: {v}" for k, v in meta.items() if v]
            header = f'<p class="meta">{" · ".join(parts)}</p><hr/>'

        self.html_view.document().setDefaultStyleSheet(theme.preview_css(self._dark))
        self.html_view.setHtml(header + render_markdown(body))
        # Icerik degisimi sicramasin: yeni belge kisa bir fade ile gelsin.
        # Tema degisiminde animasyon yok: pencere zaten kendi gecisini yapiyor.
        if animate:
            fade_in(self.tabs, start=0.3)
        self.info.setText(info)
        self.copy_btn.setEnabled(bool(md))
        self.folder_btn.setEnabled(md_path is not None)

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.raw_view.toPlainText())
        self.copy_btn.setText(tr.BTN_COPIED)
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(tr.BTN_COPY))

    def _reveal(self) -> None:
        if self._md_path:
            reveal(self._md_path)
