"""Donusum isini arka plan is parcaciginda calistiran worker.

Kuyruk TEK worker ile sirayla islenir: modeller CPU ve RAM'i doldurdugundan
paralel calistirmak toplam sureyi kisaltmiyor, arayuzu ve makineyi bogiyor.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..core.converter import (
    ConversionCancelled,
    ConversionResult,
    OutputError,
    Pdf2MdConverter,
    PdfReadError,
)
from ..core.options import ConversionOptions

log = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """QRunnable kendisi sinyal yayamaz; sinyaller ayri bir QObject'te tutulur."""

    progress = Signal(int, int, str)          # (satir, yuzde, durum metni)
    finished = Signal(int, object)            # (satir, ConversionResult | None)
    failed = Signal(int, str)                 # (satir, hata metni)
    cancelled = Signal(int)                   # (satir,)
    queue_finished = Signal()


class ConversionWorker(QRunnable):
    """Kuyruktaki tum dosyalari sirayla ceviren tek is parcacigi."""

    def __init__(
        self,
        jobs: list[tuple[int, Path]],
        opts: ConversionOptions,
        engine: Pdf2MdConverter,
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._jobs = jobs
        self._opts = opts
        self._engine = engine
        self._cancelled = False

    def cancel(self) -> None:
        """Iptal bayragini kaldir. Calisan sayfa analizi bitene kadar surer."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        for row, pdf in self._jobs:
            if self._cancelled:
                self.signals.cancelled.emit(row)
                continue

            def progress(pct: int, msg: str, _row: int = row) -> None:
                self.signals.progress.emit(_row, pct, msg)

            try:
                result: ConversionResult | None = self._engine.convert(
                    pdf, self._opts, progress=progress, is_cancelled=lambda: self._cancelled
                )
                self.signals.finished.emit(row, result)
            except ConversionCancelled:
                self.signals.cancelled.emit(row)
            except (PdfReadError, OutputError) as exc:
                self.signals.failed.emit(row, str(exc))
            except Exception as exc:  # beklenmedik hata: kuyruk durmasin
                log.error("Beklenmeyen donusum hatasi: %s\n%s", exc, traceback.format_exc())
                self.signals.failed.emit(row, f"Beklenmeyen hata: {exc}")

        self.signals.queue_finished.emit()
