"""Donusum secenekleri ve varsayilanlari."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OcrMode(str, Enum):
    AUTO = "auto"    # metin katmani yoksa OCR calistir
    OFF = "off"      # hicbir zaman OCR calistirma
    FORCE = "force"  # metin katmani olsa bile OCR calistir


class ImageMode(str, Enum):
    REFERENCED = "referenced"  # ayri klasore kaydet, md'den link ver
    SKIP = "skip"              # gorselleri tamamen atla


class ExistingFile(str, Enum):
    OVERWRITE = "overwrite"
    RENAME = "rename"  # dosya-1.md, dosya-2.md
    SKIP = "skip"


@dataclass
class ConversionOptions:
    """Tek bir donusumu tanimlayan secenekler."""

    # Cikti
    output_dir: Path | None = None  # None -> PDF ile ayni klasor
    existing_file: ExistingFile = ExistingFile.RENAME
    frontmatter: bool = True

    # Sayfa araligi (1 tabanli, ikisi de dahil). None -> tum belge
    page_range: tuple[int, int] | None = None

    # OCR
    ocr_mode: OcrMode = OcrMode.AUTO
    ocr_langs: list[str] = field(default_factory=lambda: ["tr", "en"])

    # Gorseller
    image_mode: ImageMode = ImageMode.REFERENCED
    min_image_px: int = 32           # bu boyutun altindaki gorseller atilir
    min_image_area_ratio: float = 0.005  # sayfa alaninin %0.5'inden kucukler atilir
    max_image_width: int = 1600      # bunu asan gorseller olceklenir
    drop_repeated_images: bool = True  # her sayfada tekrarlayan logo/filigran atilir
    repeated_image_threshold: float = 0.5  # sayfalarin yarisindan fazlasinda varsa logo say
    repeated_image_min_pages: int = 3      # en az bu kadar farkli sayfada gorunmeli

    # Zenginlestirme (ek model indirir, yavaslatir)
    do_formula: bool = True   # formul goruntulerini LaTeX'e cevir
    do_code: bool = False     # kod bloklarini dil etiketiyle isaretle
    do_tables: bool = True    # TableFormer ile tablo yapisi cikar

    # Post-process
    strip_repeated_headers: bool = True  # ust/alt bilgi tekrarlarini sil
    repeated_line_threshold: float = 0.6  # satir bu oranda sayfada gecerse ust/alt bilgi say
    fix_hyphenation: bool = True         # satir sonu tirelemesini birlestir
    normalize_headings: bool = True      # baslik seviyelerini normalize et

    def cache_key(self) -> tuple:
        """Ayni DocumentConverter ornegini yeniden kullanabilmek icin anahtar.

        Yalnizca pipeline'i etkileyen (model yukleyen) alanlar yer alir; cikti
        bicimini etkileyen alanlar burada olmamali.
        """
        return (
            self.ocr_mode is not OcrMode.OFF,
            tuple(self.ocr_langs),
            self.do_formula,
            self.do_code,
            self.do_tables,
            self.image_mode is ImageMode.REFERENCED,
        )
