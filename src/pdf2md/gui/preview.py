"""Markdown onizleme paneli.

QWebEngineView bilerek kullanilmiyor: paketlenmis exe'ye ~150 MB ekliyor.
markdown-it-py ile uretilen HTML, QTextBrowser'in destekledigi alt kumede
(baslik, tablo, liste, gorsel, kod) yeterince iyi goruntuleniyor.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from . import theme
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


class PreviewPanel(QWidget):
    """Sekmeli onizleme: render edilmis HTML ve ham markdown."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dark = True
        self._md_path: Path | None = None

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

        self.copy_btn = QPushButton(tr.BTN_COPY)
        self.copy_btn.clicked.connect(self._copy)
        self.folder_btn = QPushButton(tr.BTN_SHOW_IN_FOLDER)
        self.folder_btn.clicked.connect(self._reveal)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.info, 1)
        bar.addWidget(self.copy_btn)
        bar.addWidget(self.folder_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(bar)

        self.clear()

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self.html_view.document().setDefaultStyleSheet(theme.preview_css(dark))
        # Stil degisikliginin uygulanmasi icin icerigi yeniden yaz
        self.html_view.setHtml(self.html_view.toHtml())

    def clear(self) -> None:
        self._md_path = None
        self.html_view.setHtml("")
        self.raw_view.setPlainText("")
        self.info.setText(tr.PREVIEW_EMPTY)
        self.copy_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)

    def show_markdown(self, md: str, md_path: Path | None, info: str = "") -> None:
        self._md_path = md_path
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
