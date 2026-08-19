"""Ana pencere: birakma alani, kuyruk, onizleme ve secenekler."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core import models
from ..core import settings as app_settings
from ..core.converter import Pdf2MdConverter
from ..core.tokens import format_tokens, page_image_tokens, savings_percent
from ..i18n import tr
from . import theme
from .animations import (
    CollapsibleSection,
    SoftButton,
    fade_in,
    fade_window_in,
    pulse_opacity,
)
from .drop_zone import DropZone, collect_pdfs
from .options_panel import OptionsPanel
from .preview import PreviewPanel
from .queue_view import JobState, QueueTable
from .setup_wizard import ModelsDialog
from .worker import ConversionWorker

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr.APP_TITLE)
        self.setMinimumSize(760, 520)
        self._size_to_screen()

        self._dark = app_settings.load_dark_theme()
        self._opts = app_settings.load_options()
        self._engine = Pdf2MdConverter()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)  # kuyruk sirayla islenir
        self._worker: ConversionWorker | None = None
        self._models_checked = False
        self._shown_once = False

        self._build_ui()
        self._apply_theme()
        self._restore_geometry()
        self._update_actions()

    def _size_to_screen(self) -> None:
        """Pencereyi ekrana sigacak sekilde ac.

        Sabit 1180x760, %125 olcekli 1536x960 bir ekranda calisma alanindan
        (mantiksal ~1229x730) buyuk kaliyordu: alt eylem cubugu ve sag panel
        pencerenin disinda kaliyordu.
        """
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1180, 760)
            return
        area = screen.availableGeometry()
        self.resize(min(1180, int(area.width() * 0.94)), min(770, int(area.height() * 0.94)))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._shown_once:
            self._shown_once = True
            fade_window_in(self)
        if not self._models_checked:
            self._models_checked = True
            # Pencere cizildikten sonra ac: sihirbaz bos bir ekranin ustunde
            # acilmasin.
            QTimer.singleShot(120, self._check_models_on_start)

    def _check_models_on_start(self) -> None:
        """Ilk acilista zorunlu modeller eksikse sihirbazi goster."""
        if not models.missing():
            return
        ModelsDialog(self, first_run=True).exec()
        self._update_actions()

    def _open_models_dialog(self, first_run: bool = False) -> None:
        ModelsDialog(self, first_run=first_run).exec()
        self._update_actions()

    def _ensure_models(self) -> bool:
        """Donusum icin gereken modeller yoksa kullaniciya indirmeyi teklif et.

        Formul modeli yalnizca secenek aciksa gerekli; kapaliyken eksik olmasi
        donusumu engellemez.
        """
        needed = models.missing()
        if self.options_panel.options(self._opts).do_formula:
            formula = models.spec("formula")
            if not models.is_installed(formula):
                needed.append(formula)
        if not needed:
            return True

        answer = QMessageBox.question(
            self, tr.MODELS_MISSING_TITLE, tr.MODELS_MISSING_ASK,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer is not QMessageBox.StandardButton.Yes:
            return False

        self._open_models_dialog()
        return all(models.is_installed(s) for s in needed)

    # -- kurulum -------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(14)

        layout.addWidget(self._build_header())

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self._build_left())
        self.splitter.addWidget(self._build_right())
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setChildrenCollapsible(False)
        # Sabit [680, 480] dar ekranda sag paneli 260 px'e sikistiriyordu;
        # oran pencere genisliginden hesaplaniyor.
        width = max(self.width(), 900)
        self.splitter.setSizes([int(width * 0.58), int(width * 0.42)])
        layout.addWidget(self.splitter, 1)

        self.options_panel = OptionsPanel(self._opts)
        self.options_panel.changed.connect(self._on_options_changed)
        self.options_section = CollapsibleSection(
            tr.OPT_SECTION, self.options_panel, app_settings.load_options_expanded()
        )
        self.options_section.toggled_open.connect(app_settings.save_options_expanded)
        layout.addWidget(self.options_section)

        layout.addLayout(self._build_action_bar())

        self.setCentralWidget(root)
        self.statusBar().showMessage(tr.READY)

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(8)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(tr.APP_TITLE)
        title.setObjectName("appTitle")
        subtitle = QLabel(tr.APP_SUBTITLE)
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)

        self.theme_btn = SoftButton("", "quiet")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.clicked.connect(self._toggle_theme)

        self.menu_btn = SoftButton("⋯", "quiet")
        self.menu_btn.setFixedWidth(40)
        self.menu_btn.clicked.connect(self._show_menu)

        row.addLayout(titles)
        row.addStretch(1)
        row.addWidget(self.theme_btn)
        row.addWidget(self.menu_btn)
        return header

    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        pick_files = SoftButton(tr.BTN_PICK_FILES)
        pick_files.clicked.connect(self._pick_files)
        pick_folder = SoftButton(tr.BTN_PICK_FOLDER)
        pick_folder.clicked.connect(self._pick_folder)
        self.clear_btn = SoftButton(tr.BTN_CLEAR)
        self.clear_btn.clicked.connect(self._clear_queue)
        buttons.addWidget(pick_files)
        buttons.addWidget(pick_folder)
        buttons.addStretch(1)
        buttons.addWidget(self.clear_btn)
        layout.addLayout(buttons)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(1, 1, 1, 1)

        self.queue = QueueTable()
        self.queue.selection_changed.connect(self._on_row_selected)
        self.queue.retry_requested.connect(self._retry_row)
        card_layout.addWidget(self.queue)
        layout.addWidget(card, 1)
        return panel

    def _build_right(self) -> QWidget:
        self.preview = PreviewPanel()
        return self.preview

    def _build_action_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("statTokens")

        self.convert_btn = SoftButton(tr.BTN_CONVERT, "primary")
        self.convert_btn.clicked.connect(self._start_conversion)

        self.cancel_btn = SoftButton(tr.BTN_CANCEL)
        self.cancel_btn.clicked.connect(self._cancel_conversion)
        self.cancel_btn.setVisible(False)

        bar.addWidget(self.summary_label, 1)
        bar.addWidget(self.cancel_btn)
        bar.addWidget(self.convert_btn)
        return bar

    # -- tema / ayarlar -------------------------------------------------

    def _apply_theme(self) -> None:
        colors = theme.palette(self._dark)
        self.setStyleSheet(theme.stylesheet(self._dark))
        self.theme_btn.setText("☾" if self._dark else "☀")
        self.theme_btn.setToolTip(tr.MENU_THEME_LIGHT if self._dark else tr.MENU_THEME_DARK)
        self.queue.set_dark(self._dark)
        self.preview.set_dark(self._dark)

        # Elle cizilen kontroller QSS okumaz; palet onlara ayrica verilir.
        self.drop_zone.set_colors(colors)
        for button in self.findChildren(SoftButton):
            button.set_colors(colors)

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        app_settings.save_dark_theme(self._dark)
        self._apply_theme()
        pulse_opacity(self)

    def _show_menu(self) -> None:
        menu = QMenu(self)
        models_action = QAction(tr.MENU_MODELS, menu)
        models_action.triggered.connect(lambda: self._open_models_dialog())
        models_action.setEnabled(self._worker is None)
        menu.addAction(models_action)
        menu.addSeparator()

        about = QAction(tr.MENU_ABOUT, menu)
        about.triggered.connect(
            lambda: QMessageBox.information(self, tr.MENU_ABOUT, tr.ABOUT_TEXT)
        )
        menu.addAction(about)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def _on_options_changed(self) -> None:
        self._opts = self.options_panel.options(self._opts)
        app_settings.save_options(self._opts)
        self._update_actions()

    def _restore_geometry(self) -> None:
        data = app_settings.load_window_geometry()
        if not data:
            return
        self.restoreGeometry(data)

        # Kaydedilen boyut baska/buyuk bir ekrandan kalmis olabilir; ekrana
        # sigmiyorsa geri kucult, yoksa alt eylem cubugu goruntunun disinda kalir.
        from PySide6.QtWidgets import QApplication

        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        if self.width() > area.width() or self.height() > area.height():
            self.resize(
                min(self.width(), int(area.width() * 0.94)),
                min(self.height(), int(area.height() * 0.94)),
            )
            self.move(area.topLeft())

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.cancel()
        app_settings.save_window_geometry(bytes(self.saveGeometry()))
        super().closeEvent(event)

    # -- dosya ekleme ---------------------------------------------------

    def _pick_files(self) -> None:
        start = app_settings.load_last_dir() or str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(self, tr.BTN_PICK_FILES, start, "PDF (*.pdf)")
        if files:
            app_settings.save_last_dir(str(Path(files[0]).parent))
            self._add_files([Path(f) for f in files])

    def _pick_folder(self) -> None:
        start = app_settings.load_last_dir() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, tr.BTN_PICK_FOLDER, start)
        if folder:
            app_settings.save_last_dir(folder)
            self._add_files(collect_pdfs([Path(folder)]))

    @Slot(list)
    def _add_files(self, paths: list[Path]) -> None:
        added = self.queue.add_files(paths)
        if added:
            fade_in(self.queue, start=0.3)
            self.statusBar().showMessage(f"{added} dosya eklendi", 3000)
        self._update_actions()

    def _clear_queue(self) -> None:
        self.queue.clear_all()
        self.preview.clear()
        self._update_actions()

    # -- donusum --------------------------------------------------------

    def _start_conversion(self) -> None:
        if not self.options_panel.pages_valid():
            QMessageBox.warning(self, tr.OPT_PAGES, tr.OPT_PAGES_PLACEHOLDER)
            return

        if not self._ensure_models():
            return

        self._opts = self.options_panel.options(self._opts)
        app_settings.save_options(self._opts)

        self.queue.reset_pending()
        jobs = self.queue.pending_jobs()
        if not jobs:
            return

        worker = ConversionWorker(jobs, self._opts, self._engine)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.failed.connect(self._on_failed)
        worker.signals.cancelled.connect(self._on_cancelled)
        worker.signals.queue_finished.connect(self._on_queue_finished)
        self._worker = worker

        self._set_running(True)
        self.statusBar().showMessage(tr.ENGINE_LOADING)
        self._pool.start(worker)

    def _retry_row(self, row: int) -> None:
        if self._worker is not None:
            return
        job = self.queue.jobs[row]
        job.state = JobState.WAITING
        self.queue.set_running(row, 0, tr.STATUS_WAITING)
        self._start_conversion()

    def _cancel_conversion(self) -> None:
        if self._worker is None:
            return
        answer = QMessageBox.question(
            self, tr.CONFIRM_CANCEL_TITLE, tr.CONFIRM_CANCEL,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer is QMessageBox.StandardButton.Yes:
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.statusBar().showMessage("İptal ediliyor…")

    def _set_running(self, running: bool) -> None:
        self.convert_btn.setVisible(not running)
        self.cancel_btn.setVisible(running)
        self.cancel_btn.setEnabled(running)
        self.options_section.setEnabled(not running)
        self.clear_btn.setEnabled(not running)

    # -- worker sinyalleri ----------------------------------------------

    @Slot(int, int, str)
    def _on_progress(self, row: int, pct: int, message: str) -> None:
        self.queue.set_running(row, pct, message)
        self.statusBar().showMessage(f"{self.queue.jobs[row].path.name} · {message}")

    @Slot(int, object)
    def _on_finished(self, row: int, result) -> None:
        self.queue.set_done(row, result)
        self._update_summary()
        if self.queue.currentRow() in (row, -1):
            self.queue.selectRow(row)
            self._on_row_selected(row)

    @Slot(int, str)
    def _on_failed(self, row: int, message: str) -> None:
        self.queue.set_failed(row, message)
        log.warning("%s: %s", self.queue.jobs[row].path.name, message)
        self._update_summary()

    @Slot(int)
    def _on_cancelled(self, row: int) -> None:
        self.queue.set_cancelled(row)

    @Slot()
    def _on_queue_finished(self) -> None:
        self._worker = None
        self._set_running(False)
        self._update_actions()
        self.statusBar().showMessage(tr.READY, 5000)

        errors = [j for j in self.queue.jobs if j.state is JobState.ERROR]
        if errors:
            detail = "\n".join(f"• {j.path.name}: {j.error}" for j in errors[:8])
            QMessageBox.warning(self, tr.ERR_TITLE, detail)

    # -- onizleme -------------------------------------------------------

    @Slot(int)
    def _on_row_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.queue.jobs):
            self.preview.clear()
            return

        job = self.queue.jobs[row]
        if job.result is None or not job.markdown:
            self.preview.clear()
            return

        vision = page_image_tokens(job.result.pages_converted_count)
        percent = savings_percent(vision, job.result.md_tokens)
        info = tr.savings_label(
            format_tokens(job.result.md_tokens), format_tokens(vision), percent
        )
        if job.result.used_ocr:
            info += " · OCR"
        self.preview.show_markdown(job.markdown, job.result.markdown_path, info)

    def _update_summary(self) -> None:
        done, total, tokens = self.queue.totals()
        self.summary_label.setText(tr.queue_summary(done, total, format_tokens(tokens)))

    def _update_actions(self) -> None:
        self.drop_zone.set_compact(bool(self.queue.jobs))
        has_pending = bool(self.queue.pending_jobs())
        self.convert_btn.setEnabled(has_pending and self._worker is None)
        self.clear_btn.setEnabled(bool(self.queue.jobs) and self._worker is None)
        self._update_summary()
