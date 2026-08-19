"""Model indirme sihirbazi.

Iki durumda acilir:
  - ilk acilista zorunlu modeller eksikse (first_run=True)
  - menuden "Modeller" secildiginde (tum modeller, istege bagli olanlar dahil)

Indirme ayri bir is parcaciginda calisir. Ilerleme, huggingface_hub'in tqdm
ciktisina baglanmak yerine onbellek klasorunun buyumesi olculerek gosterilir:
HF surumune ve hf_xet'in kullanilip kullanilmadigina bagimli olmayan tek yontem.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import models
from ..core.paths import models_dir
from ..i18n import tr
from . import theme
from .animations import AnimatedProgressBar, SoftButton, fade_in

log = logging.getLogger(__name__)

_POLL_MS = 700


class _DownloadWorker(QObject):
    """Modelleri sirayla indiren arka plan isi."""

    status = Signal(str)     # su an indirilen modelin basligi
    finished = Signal()
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, specs: list[models.ModelSpec]) -> None:
        super().__init__()
        self._specs = specs
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            models.download_all(
                self._specs,
                on_status=lambda s: self.status.emit(s.title),
                is_cancelled=lambda: self._cancelled,
            )
        except models.DownloadCancelled:
            self.cancelled.emit()
        except models.ModelDownloadError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmedik hata: sihirbaz kilitlenmesin
            log.exception("Model indirme hatasi")
            self.failed.emit(str(exc))
        else:
            self.finished.emit()


class _ModelRow(QFrame):
    """Tek bir model satiri: baslik, aciklama, boyut ve durum/secim kutusu."""

    def __init__(self, spec: models.ModelSpec, installed: bool) -> None:
        super().__init__()
        self.spec = spec
        self.installed = installed
        self.setObjectName("card")

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = QLabel(spec.title)
        title.setStyleSheet("font-weight: 600;")
        detail = QLabel(spec.detail)
        detail.setObjectName("appSubtitle")
        detail.setWordWrap(True)
        texts.addWidget(title)
        texts.addWidget(detail)

        size = QLabel(models.format_size(spec.approx_bytes))
        size.setObjectName("statTokens")

        row.addLayout(texts, 1)
        row.addWidget(size)

        self.check: QCheckBox | None = None
        if installed:
            state = QLabel(tr.MODELS_INSTALLED + " ✓")
            state.setObjectName("statTokens")
            row.addWidget(state)
        else:
            self.check = QCheckBox()
            # Zorunlular hep secili ve kapatilamaz; istege bagli olanlar kapali
            # baslar: kimse istemeden 640 MB indirmesin.
            self.check.setChecked(spec.required)
            self.check.setEnabled(not spec.required)
            self.check.setToolTip(
                tr.MODELS_REQUIRED if spec.required else tr.MODELS_OPTIONAL
            )
            row.addWidget(self.check)

    def selected(self) -> bool:
        return self.check is not None and self.check.isChecked()


class ModelsDialog(QDialog):
    """Model durumunu gosteren ve eksikleri indiren diyalog."""

    def __init__(self, parent: QWidget | None = None, first_run: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr.MODELS_FIRST_RUN_TITLE if first_run else tr.MODELS_TITLE)
        self.setMinimumWidth(580)
        self._first_run = first_run
        self._thread: QThread | None = None
        self._worker: _DownloadWorker | None = None
        self._running_specs: list[models.ModelSpec] = []
        self._base_bytes = 0
        self._downloaded_ok = False

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_MS)
        self._timer.timeout.connect(self._tick)

        self._build_ui()
        self._apply_colors()
        fade_in(self, duration=180, start=0.2)

    # -- kurulum -------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        intro = QLabel(tr.MODELS_INTRO if models.missing() else tr.MODELS_INTRO_DONE)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._rows: list[_ModelRow] = []
        self._rows_start = layout.count()
        for spec in models.SPECS:
            self._rows.append(self._make_row(spec, layout.count()))

        self.location_label = QLabel(tr.models_location(str(models_dir())))
        self.location_label.setObjectName("statTokens")
        self.location_label.setWordWrap(True)
        layout.addWidget(self.location_label)

        self.progress = AnimatedProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statTokens")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.total_label = QLabel("")
        self.total_label.setObjectName("statTokens")

        self.download_btn = SoftButton(tr.BTN_DOWNLOAD, "primary")
        self.download_btn.clicked.connect(self._start)

        self.close_btn = SoftButton(tr.BTN_LATER if self._first_run else tr.BTN_CLOSE)
        self.close_btn.clicked.connect(self.reject)

        self.cancel_btn = SoftButton(tr.BTN_CANCEL)
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setVisible(False)

        buttons.addWidget(self.total_label, 1)
        buttons.addWidget(self.close_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.download_btn)
        layout.addLayout(buttons)

        self._update_total()

    def _apply_colors(self) -> None:
        """Elle cizilen butonlara paleti dagit (QSS okumuyorlar)."""
        parent = self.parent()
        dark = getattr(parent, "_dark", True)
        colors = theme.palette(bool(dark))
        for button in self.findChildren(SoftButton):
            button.set_colors(colors)

    def _make_row(self, spec: models.ModelSpec, index: int) -> _ModelRow:
        row = _ModelRow(spec, models.is_installed(spec))
        if row.check is not None:
            row.check.toggled.connect(self._update_total)
        self.layout().insertWidget(index, row)
        return row

    def _selected_specs(self) -> list[models.ModelSpec]:
        return [row.spec for row in self._rows if row.selected()]

    def _update_total(self) -> None:
        specs = self._selected_specs()
        self.download_btn.setEnabled(bool(specs))
        self.total_label.setText(
            tr.models_total(len(specs), models.format_size(models.total_bytes(specs)))
            if specs
            else tr.MODELS_ALL_READY
        )

    # -- indirme -------------------------------------------------------

    def _start(self) -> None:
        specs = self._selected_specs()
        if not specs:
            return

        self._running_specs = specs
        self._base_bytes = sum(models.installed_bytes(s) for s in specs)
        self._set_running(True)
        self.status_label.setText(tr.MODELS_STARTING)

        worker = _DownloadWorker(specs)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        self._worker, self._thread = worker, thread

        self.progress.setValue(0)
        self._timer.start()
        thread.start()

    def _set_running(self, running: bool) -> None:
        self.progress.setVisible(running)
        self.download_btn.setVisible(not running)
        self.close_btn.setVisible(not running)
        self.cancel_btn.setVisible(running)
        self.cancel_btn.setEnabled(running)
        for row in self._rows:
            if row.check is not None:
                row.check.setEnabled(not running and not row.spec.required)

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.status_label.setText(tr.MODELS_CANCEL_HINT)

    def _tick(self) -> None:
        """Onbellek klasorunun buyumesine bakarak ilerlemeyi guncelle."""
        if not self._running_specs:
            return
        target = models.total_bytes(self._running_specs)
        if target <= 0:
            return
        current = sum(models.installed_bytes(s) for s in self._running_specs)
        done = max(0, current - self._base_bytes)
        # Tahmini boyut gercekte inenden kucuk kalabilir; %99'da tut, bitisi
        # worker'in finished sinyali belirlesin.
        self.progress.animate_to(min(99, int(done * 100 / target)))

    @Slot(str)
    def _on_status(self, title: str) -> None:
        self.status_label.setText(tr.models_downloading(title))

    def _teardown(self) -> None:
        self._timer.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
        self._thread = None
        self._worker = None
        self._running_specs = []
        self._set_running(False)
        self._refresh_rows()

    def _refresh_rows(self) -> None:
        """Satirlari yeniden kur: yeni inen modeller artik ✓ gostermeli."""
        layout = self.layout()
        for row in self._rows:
            layout.removeWidget(row)
            row.deleteLater()
        self._rows = [
            self._make_row(spec, self._rows_start + i)
            for i, spec in enumerate(models.SPECS)
        ]
        self._apply_colors()
        self._update_total()

    @Slot()
    def _on_finished(self) -> None:
        self._downloaded_ok = True
        self.progress.animate_to(100)
        self._teardown()
        self.status_label.setText(tr.MODELS_DONE)
        self.close_btn.setText(tr.BTN_CLOSE)
        if self._first_run:
            self.accept()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._teardown()
        self.status_label.setText(tr.models_error(message))

    @Slot()
    def _on_cancelled(self) -> None:
        self._teardown()
        self.status_label.setText(tr.MODELS_CANCELLED)

    # -- kapanis -------------------------------------------------------

    def reject(self) -> None:
        # Indirme surerken kapatma istegi once iptal anlamina gelir.
        if self._worker is not None:
            self._cancel()
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._cancel()
            event.ignore()
            return
        super().closeEvent(event)

    @property
    def succeeded(self) -> bool:
        return self._downloaded_ok
