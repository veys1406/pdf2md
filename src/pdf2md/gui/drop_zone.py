"""Surukle-birak alani. Dosya ve klasor kabul eder."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from ..i18n import tr
from .animations import mix


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
    """PDF birakilabilen alan.

    Kesikli cerceve QSS ile degil elle ciziliyor: dosya suruklenirken cercevenin
    ve zeminin yumusak gecisle canlanmasi QSS `transition` olmadan baska turlu
    yapilamiyor.
    """

    files_dropped = Signal(list)  # list[Path]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setFixedHeight(128)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self._colors: dict[str, str] = {}
        self._glow = 0.0  # 0 = bos duruyor, 1 = uzerine dosya suruklendi

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_glow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(tr.DROP_TITLE)
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(tr.DROP_HINT)
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Sarma kapali: panel Ignored genislik politikasi kullandigi icin
        # QLabel'lar en dar olcuye gore sariliyor ve tek satirlik metin ikiye
        # bolunuyordu.
        hint.setWordWrap(False)
        title.setWordWrap(False)

        layout.addWidget(title)
        layout.addWidget(hint)
        self._title = title
        self._hint = hint

        self._height_anim = QVariantAnimation(self)
        self._height_anim.setDuration(220)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_anim.valueChanged.connect(self._on_height)
        self._compact = False

    def _on_height(self, value) -> None:
        self.setFixedHeight(int(value))

    def set_compact(self, compact: bool) -> None:
        """Kuyrukta dosya varken alani daraltir: kucuk ekranlarda yer acar."""
        if compact == self._compact:
            return
        self._compact = compact
        self._hint.setVisible(not compact)
        self._title.setText(tr.DROP_TITLE_COMPACT if compact else tr.DROP_TITLE)
        # Dar yukseklikte iki satira sarilan metnin alti kesiliyordu.

        layout = self.layout()
        if compact:
            layout.setContentsMargins(24, 12, 24, 12)
        else:
            layout.setContentsMargins(24, 24, 24, 24)

        self._height_anim.stop()
        self._height_anim.setStartValue(self.height())
        self._height_anim.setEndValue(62 if compact else 128)
        self._height_anim.start()

    def set_colors(self, colors: dict[str, str]) -> None:
        self._colors = colors
        self.update()

    def _on_glow(self, value) -> None:
        self._glow = float(value)
        self.update()

    def _set_hover(self, hover: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0 if hover else 0.0)
        self._anim.start()

    def paintEvent(self, event) -> None:
        c = self._colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 18.0, 18.0)

        bg = mix(c.get("drop_bg", "#101011"), c.get("surface2", "#1a1a1c"), self._glow)
        painter.fillPath(path, bg)

        border = mix(c.get("border", "#242427"), c.get("accent", "#f4f4f5"), self._glow)
        pen = QPen(QColor(border), 1.0 + self._glow * 0.6)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 5])
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_hover(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_hover(False)
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        pdfs = collect_pdfs(paths)
        if pdfs:
            self.files_dropped.emit(pdfs)
            event.acceptProposedAction()
