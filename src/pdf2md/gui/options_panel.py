"""Alt secenekler seridi: cikti klasoru, sayfa araligi, OCR, gorsel, formul."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.options import ConversionOptions, ExistingFile, ImageMode, OcrMode
from ..i18n import tr

_PAGE_RANGE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+)\s*)?$")


def parse_pages(text: str) -> tuple[int, int] | None:
    """'5-20' / '7' -> (5,20) / (7,7). Bos veya gecersizse None."""
    m = _PAGE_RANGE.match(text or "")
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    if start < 1 or end < start:
        return None
    return start, end


def _labeled(label: str, widget: QWidget) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    caption = QLabel(label)
    caption.setObjectName("sectionLabel")
    layout.addWidget(caption)
    layout.addWidget(widget)
    return box


class OptionsPanel(QFrame):
    """Donusum secenekleri. Degisiklikler `changed` ile bildirilir."""

    changed = Signal()

    def __init__(self, opts: ConversionOptions, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText(tr.OPT_OUTPUT_SAME)
        self.browse_btn = QPushButton(tr.OPT_BROWSE)
        self.browse_btn.clicked.connect(self._pick_output)
        self.clear_output_btn = QPushButton("✕")
        self.clear_output_btn.setObjectName("iconButton")
        self.clear_output_btn.setToolTip(tr.OPT_OUTPUT_SAME)
        self.clear_output_btn.clicked.connect(self._clear_output)

        output_row = QWidget()
        row = QHBoxLayout(output_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.output_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(self.clear_output_btn)

        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText(tr.OPT_PAGES_PLACEHOLDER)
        self.pages_edit.setFixedWidth(130)
        self.pages_edit.textChanged.connect(self._on_pages_changed)

        self.ocr_combo = QComboBox()
        for label, mode in (
            (tr.OPT_OCR_AUTO, OcrMode.AUTO),
            (tr.OPT_OCR_OFF, OcrMode.OFF),
            (tr.OPT_OCR_FORCE, OcrMode.FORCE),
        ):
            self.ocr_combo.addItem(label, mode.value)
        self.ocr_combo.currentIndexChanged.connect(self.changed)

        self.image_combo = QComboBox()
        for label, mode in (
            (tr.OPT_IMAGES_SAVE, ImageMode.REFERENCED),
            (tr.OPT_IMAGES_SKIP, ImageMode.SKIP),
        ):
            self.image_combo.addItem(label, mode.value)
        self.image_combo.currentIndexChanged.connect(self.changed)

        self.existing_combo = QComboBox()
        for label, mode in (
            (tr.OPT_EXISTING_RENAME, ExistingFile.RENAME),
            (tr.OPT_EXISTING_OVERWRITE, ExistingFile.OVERWRITE),
            (tr.OPT_EXISTING_SKIP, ExistingFile.SKIP),
        ):
            self.existing_combo.addItem(label, mode.value)
        self.existing_combo.currentIndexChanged.connect(self.changed)

        self.formula_check = QCheckBox(tr.OPT_FORMULA)
        self.formula_check.stateChanged.connect(self.changed)
        self.frontmatter_check = QCheckBox(tr.OPT_FRONTMATTER)
        self.frontmatter_check.stateChanged.connect(self.changed)

        grid = QGridLayout(self)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.addWidget(_labeled(tr.OPT_OUTPUT, output_row), 0, 0, 1, 3)
        grid.addWidget(_labeled(tr.OPT_PAGES, self.pages_edit), 0, 3)
        grid.addWidget(_labeled(tr.OPT_OCR, self.ocr_combo), 1, 0)
        grid.addWidget(_labeled(tr.OPT_IMAGES, self.image_combo), 1, 1)
        grid.addWidget(_labeled(tr.OPT_EXISTING, self.existing_combo), 1, 2)

        checks = QWidget()
        check_layout = QVBoxLayout(checks)
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setSpacing(6)
        check_layout.addWidget(self.formula_check)
        check_layout.addWidget(self.frontmatter_check)
        grid.addWidget(checks, 1, 3)
        grid.setColumnStretch(0, 1)

        self.set_options(opts)

    # -- degerler -----------------------------------------------------

    def set_options(self, opts: ConversionOptions) -> None:
        self.output_edit.setText(str(opts.output_dir) if opts.output_dir else "")
        self.ocr_combo.setCurrentIndex(max(0, self.ocr_combo.findData(opts.ocr_mode.value)))
        self.image_combo.setCurrentIndex(
            max(0, self.image_combo.findData(opts.image_mode.value))
        )
        self.existing_combo.setCurrentIndex(
            max(0, self.existing_combo.findData(opts.existing_file.value))
        )
        self.formula_check.setChecked(opts.do_formula)
        self.frontmatter_check.setChecked(opts.frontmatter)
        if opts.page_range:
            self.pages_edit.setText(f"{opts.page_range[0]}-{opts.page_range[1]}")

    def options(self, base: ConversionOptions | None = None) -> ConversionOptions:
        """Paneldeki degerlerle yeni bir ConversionOptions uret."""
        opts = base or ConversionOptions()
        out = self.output_edit.text().strip()
        opts.output_dir = Path(out) if out else None
        opts.page_range = parse_pages(self.pages_edit.text())
        # Qt, str tabanli enum'lari QVariant'a koyup geri verirken duz str'e
        # indirgiyor; enum'a burada geri cevrilmezse save_options patliyor.
        opts.ocr_mode = OcrMode(self.ocr_combo.currentData())
        opts.image_mode = ImageMode(self.image_combo.currentData())
        opts.existing_file = ExistingFile(self.existing_combo.currentData())
        opts.do_formula = self.formula_check.isChecked()
        opts.frontmatter = self.frontmatter_check.isChecked()
        return opts

    def pages_valid(self) -> bool:
        text = self.pages_edit.text().strip()
        return not text or parse_pages(text) is not None

    # -- olaylar -------------------------------------------------------

    def _on_pages_changed(self) -> None:
        ok = self.pages_valid()
        self.pages_edit.setStyleSheet("" if ok else "border-color: #f87171;")
        self.changed.emit()

    def _pick_output(self) -> None:
        current = self.output_edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, tr.OPT_OUTPUT, current)
        if chosen:
            self.output_edit.setText(chosen)
            self.changed.emit()

    def _clear_output(self) -> None:
        self.output_edit.clear()
        self.changed.emit()
