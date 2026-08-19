"""Donusum kuyrugu tablosu."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
)

from ..core.converter import ConversionResult
from ..core.tokens import format_tokens
from ..i18n import tr
from . import theme


class JobState(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


_LABELS = {
    JobState.WAITING: tr.STATUS_WAITING,
    JobState.RUNNING: tr.STATUS_RUNNING,
    JobState.DONE: tr.STATUS_DONE,
    JobState.ERROR: tr.STATUS_ERROR,
    JobState.CANCELLED: tr.STATUS_CANCELLED,
    JobState.SKIPPED: tr.STATUS_SKIPPED,
}


@dataclass
class Job:
    path: Path
    state: JobState = JobState.WAITING
    status_text: str = ""
    result: ConversionResult | None = None
    error: str = ""
    markdown: str = ""  # onizleme icin okunan icerik
    warnings: list[str] = field(default_factory=list)


class QueueTable(QTableWidget):
    """Dosya, durum, ilerleme, sure ve token sutunlarini tasiyan kuyruk."""

    selection_changed = Signal(int)  # secili satir (-1: yok)
    retry_requested = Signal(int)

    COLUMNS = [tr.COL_FILE, tr.COL_PAGES, tr.COL_STATUS, tr.COL_PROGRESS, tr.COL_TIME, tr.COL_TOKENS]

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.COLUMNS), parent)
        self.jobs: list[Job] = []
        self._dark = True

        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemSelectionChanged.connect(
            lambda: self.selection_changed.emit(self.currentRow())
        )

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setDefaultSectionSize(38)

    # -- veri ---------------------------------------------------------

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        for row in range(self.rowCount()):
            self._paint_status(row)

    def add_files(self, paths: list[Path]) -> int:
        """Kuyrukta olmayan dosyalari ekle, eklenen sayiyi dondur."""
        existing = {j.path for j in self.jobs}
        added = 0
        for path in paths:
            if path in existing:
                continue
            self.jobs.append(Job(path=path))
            row = self.rowCount()
            self.insertRow(row)

            name = QTableWidgetItem(path.name)
            name.setToolTip(str(path))
            self.setItem(row, 0, name)
            self.setItem(row, 1, QTableWidgetItem("—"))
            self.setItem(row, 2, QTableWidgetItem(tr.STATUS_WAITING))

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            self.setCellWidget(row, 3, bar)

            self.setItem(row, 4, QTableWidgetItem("—"))
            self.setItem(row, 5, QTableWidgetItem("—"))
            self._paint_status(row)
            added += 1
        return added

    def clear_all(self) -> None:
        self.setRowCount(0)
        self.jobs.clear()

    def remove_row(self, row: int) -> None:
        if 0 <= row < len(self.jobs):
            self.removeRow(row)
            del self.jobs[row]

    def pending_jobs(self) -> list[tuple[int, Path]]:
        """Henuz basariyla islenmemis satirlar (yeniden denemeler dahil)."""
        return [
            (i, j.path)
            for i, j in enumerate(self.jobs)
            if j.state in (JobState.WAITING, JobState.ERROR, JobState.CANCELLED)
        ]

    def reset_pending(self) -> None:
        """Yeni bir calistirma oncesi bekleyen satirlari sifirla."""
        for i, job in enumerate(self.jobs):
            if job.state in (JobState.ERROR, JobState.CANCELLED):
                job.state = JobState.WAITING
                job.error = ""
                self._set_progress(i, 0)
            if job.state is JobState.WAITING:
                self._set_text(i, 2, tr.STATUS_WAITING)
                self._paint_status(i)

    # -- durum guncellemeleri -----------------------------------------

    def set_running(self, row: int, pct: int, message: str) -> None:
        job = self.jobs[row]
        job.state = JobState.RUNNING
        job.status_text = message
        self._set_text(row, 2, message)
        self._set_progress(row, pct)
        self._paint_status(row)

    def set_done(self, row: int, result: ConversionResult | None) -> None:
        job = self.jobs[row]
        if result is None:
            job.state = JobState.SKIPPED
            self._set_text(row, 2, tr.STATUS_SKIPPED)
            self._set_progress(row, 100)
            self._paint_status(row)
            return

        job.state = JobState.DONE
        job.result = result
        job.warnings = list(result.warnings)
        try:
            job.markdown = result.markdown_path.read_text(encoding="utf-8")
        except OSError:
            job.markdown = ""

        self._set_text(row, 1, f"{result.pages_converted_count}/{result.page_count}")
        self._set_text(row, 2, tr.STATUS_DONE + (" · OCR" if result.used_ocr else ""))
        self._set_progress(row, 100)
        self._set_text(row, 4, f"{result.duration:.0f} sn")
        self._set_text(row, 5, format_tokens(result.md_tokens))
        self._paint_status(row)

    def set_failed(self, row: int, message: str) -> None:
        job = self.jobs[row]
        job.state = JobState.ERROR
        job.error = message
        self._set_text(row, 2, tr.STATUS_ERROR)
        item = self.item(row, 2)
        if item:
            item.setToolTip(message)
        self._set_progress(row, 0)
        self._paint_status(row)

    def set_cancelled(self, row: int) -> None:
        self.jobs[row].state = JobState.CANCELLED
        self._set_text(row, 2, tr.STATUS_CANCELLED)
        self._set_progress(row, 0)
        self._paint_status(row)

    def totals(self) -> tuple[int, int, int]:
        """(tamamlanan, toplam, toplam token)"""
        done = sum(1 for j in self.jobs if j.state is JobState.DONE)
        total_tokens = sum(j.result.md_tokens for j in self.jobs if j.result)
        return done, len(self.jobs), total_tokens

    # -- ic yardimcilar -----------------------------------------------

    def _set_text(self, row: int, col: int, text: str) -> None:
        item = self.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self.setItem(row, col, item)
        item.setText(text)

    def _set_progress(self, row: int, pct: int) -> None:
        bar = self.cellWidget(row, 3)
        if isinstance(bar, QProgressBar):
            bar.setValue(pct)

    def _paint_status(self, row: int) -> None:
        colors = theme.palette(self._dark)
        state = self.jobs[row].state
        color = {
            JobState.DONE: colors["success"],
            JobState.ERROR: colors["danger"],
            JobState.CANCELLED: colors["warning"],
            JobState.SKIPPED: colors["muted"],
            JobState.RUNNING: colors["accent"],
        }.get(state, colors["muted"])
        item = self.item(row, 2)
        if item:
            item.setForeground(QColor(color))

    # -- baglam menusu -------------------------------------------------

    def _show_context_menu(self, pos) -> None:
        row = self.rowAt(pos.y())
        if row < 0:
            return
        job = self.jobs[row]

        menu = QMenu(self)
        if job.result:
            open_md = QAction(tr.CTX_OPEN_MD, menu)
            open_md.triggered.connect(lambda: reveal(job.result.markdown_path, open_file=True))
            menu.addAction(open_md)

            show = QAction(tr.CTX_OPEN_FOLDER, menu)
            show.triggered.connect(lambda: reveal(job.result.markdown_path))
            menu.addAction(show)
            menu.addSeparator()

        if job.state in (JobState.ERROR, JobState.CANCELLED, JobState.DONE):
            retry = QAction(tr.CTX_RETRY, menu)
            retry.triggered.connect(lambda: self.retry_requested.emit(row))
            menu.addAction(retry)

        remove = QAction(tr.CTX_REMOVE, menu)
        remove.triggered.connect(lambda: self.remove_row(row))
        menu.addAction(remove)

        menu.exec(self.viewport().mapToGlobal(pos))


def reveal(path: Path, open_file: bool = False) -> None:
    """Dosyayi ac veya Gezgin'de secili gelecek sekilde goster."""
    try:
        if open_file:
            import os

            os.startfile(path)  # noqa: S606 - Windows'a ozgu, kullanici tetikler
        else:
            subprocess.run(["explorer", "/select,", str(path)], check=False)
    except OSError:
        pass
