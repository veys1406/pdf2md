"""Kullanici ayarlarinin kalici saklanmasi (QSettings -> kayit defteri).

ConversionOptions ile QSettings arasinda cevrim yapar. Bozuk/eski bir deger
okundugunda varsayilana duser, kullanici hata gormez.
"""

from __future__ import annotations

from pathlib import Path

from enum import Enum

from PySide6.QtCore import QSettings

from .options import ConversionOptions, ExistingFile, ImageMode, OcrMode

ORG = "pdf2md"
APP = "pdf2md"


def _settings() -> QSettings:
    return QSettings(ORG, APP)


def _enum(cls, value, default):
    try:
        return cls(value)
    except (ValueError, TypeError):
        return default


def _raw(value) -> str:
    """Enum ya da duz str olabilen bir ayari QSettings'e yazilacak metne cevir."""
    return value.value if isinstance(value, Enum) else str(value)


def _bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return default


def load_options() -> ConversionOptions:
    s = _settings()
    d = ConversionOptions()

    out = s.value("output_dir", "")
    return ConversionOptions(
        output_dir=Path(out) if out else None,
        existing_file=_enum(ExistingFile, s.value("existing_file"), d.existing_file),
        frontmatter=_bool(s.value("frontmatter"), d.frontmatter),
        ocr_mode=_enum(OcrMode, s.value("ocr_mode"), d.ocr_mode),
        image_mode=_enum(ImageMode, s.value("image_mode"), d.image_mode),
        do_formula=_bool(s.value("do_formula"), d.do_formula),
    )


def save_options(opts: ConversionOptions) -> None:
    s = _settings()
    s.setValue("output_dir", str(opts.output_dir) if opts.output_dir else "")
    s.setValue("existing_file", _raw(opts.existing_file))
    s.setValue("frontmatter", opts.frontmatter)
    s.setValue("ocr_mode", _raw(opts.ocr_mode))
    s.setValue("image_mode", _raw(opts.image_mode))
    s.setValue("do_formula", opts.do_formula)


def load_dark_theme() -> bool:
    return _bool(_settings().value("dark_theme"), True)


def save_dark_theme(dark: bool) -> None:
    _settings().setValue("dark_theme", dark)


def load_window_geometry() -> bytes | None:
    value = _settings().value("geometry")
    return value if isinstance(value, (bytes, bytearray)) else None


def save_window_geometry(data: bytes) -> None:
    _settings().setValue("geometry", data)


def load_last_dir() -> str:
    return str(_settings().value("last_dir", "") or "")


def save_last_dir(path: str) -> None:
    _settings().setValue("last_dir", path)
