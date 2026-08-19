"""Surukle-birak alani. Dosya ve klasor kabul eder."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ..i18n import tr


def collect_pdfs(paths: list[Path]) -> list[Path]:
    """Verilen yollardan PDF listesi cikar; klasorler tek seviye taranir.

    Ayni dosya birden fazla kez birakildiginda tekrar eklenmez, sira korunur.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key not in seen:
            seen.add(key)
            found.append(p)

    for path in paths:
        if path.is_dir():
            for pdf in sorted(path.glob("*.pdf")):
                add(pdf)
        elif path.suffix.lower() == ".pdf":
            add(path)
    return found


class DropZone(QFrame):
    """PDF birakilabilen alan."""

    files_dropped = Signal(list)  # list[Path]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setProperty("hover", "false")
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 22, 20, 22)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(tr.DROP_TITLE)
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(tr.DROP_HINT)
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(hint)

    def _set_hover(self, hover: bool) -> None:
        self.setProperty("hover", "true" if hover else "false")
        # QSS property secicisi ancak stil yeniden uygulanirsa devreye girer
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_hover(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_hover(False)
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        pdfs = collect_pdfs(paths)
        if pdfs:
            self.files_dropped.emit(pdfs)
            event.acceptProposedAction()
