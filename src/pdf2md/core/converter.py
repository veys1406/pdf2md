r"""PDF -> Markdown donusum motoru.

Docling pipeline'ini sarmalar. Pahali olan kisim DocumentConverter'in kurulmasi
(model yukleme, 10-30 sn); bu yuzden ornekler `cache_key()` bazinda onbelleklenip
kuyruk boyunca yeniden kullanilir.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .options import ConversionOptions, ExistingFile, ImageMode, OcrMode
from .paths import ensure_env

log = logging.getLogger(__name__)

# Sayfa basina bu kadar karakterden azsa metin katmani yok sayilir (taranmis PDF)
_TEXT_LAYER_MIN_CHARS = 40
_TEXT_PROBE_PAGES = 12


class ConversionCancelled(Exception):
    """Kullanici donusumu iptal etti."""


class PdfReadError(Exception):
    """PDF acilamadi: bozuk, sifreli veya desteklenmeyen dosya."""


@dataclass
class ConversionResult:
    source: Path
    markdown_path: Path
    images_dir: Path | None
    page_count: int
    pages_converted: str        # "tumu" veya "5-20" (kullaniciya gosterilecek etiket)
    pages_converted_count: int  # gercekten islenen sayfa sayisi
    used_ocr: bool
    duration: float
    md_tokens: int = 0
    pdf_tokens: int = 0
    image_stats: object | None = None
    warnings: list[str] = field(default_factory=list)


# Ilerleme geri cagrisi: (yuzde 0-100, durum metni)
ProgressFn = Callable[[int, str], None]
# Iptal kontrolu: True dondururse donusum durur
CancelFn = Callable[[], bool]


def _noop_progress(pct: int, msg: str) -> None:
    pass


def _never_cancel() -> bool:
    return False


def probe_pdf(path: Path) -> tuple[int, bool, str]:
    """PDF'i ac ve (sayfa sayisi, metin katmani var mi, uyari) dondur."""
    import pymupdf

    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise PdfReadError(f"PDF acilamadi: {exc}") from exc

    try:
        if doc.needs_pass:
            raise PdfReadError("PDF parola korumali, acilamiyor.")

        page_count = len(doc)
        if page_count == 0:
            raise PdfReadError("PDF bos gorunuyor (0 sayfa).")

        probe = min(page_count, _TEXT_PROBE_PAGES)
        total_chars = 0
        for i in range(probe):
            try:
                total_chars += len(doc[i].get_text("text").strip())
            except Exception:
                continue

        has_text = (total_chars / probe) >= _TEXT_LAYER_MIN_CHARS
        warning = "" if has_text else "Metin katmani bulunamadi, taranmis belge olarak islenecek."
        return page_count, has_text, warning
    finally:
        doc.close()


def extract_raw_text(path: Path, page_range: tuple[int, int] | None = None) -> str:
    """Karsilastirma icin PDF'in ham metnini cek (token tasarrufu hesabinda kullanilir)."""
    import pymupdf

    try:
        doc = pymupdf.open(path)
    except Exception:
        return ""
    try:
        start, end = page_range if page_range else (1, len(doc))
        chunks = []
        for i in range(max(0, start - 1), min(len(doc), end)):
            try:
                chunks.append(doc[i].get_text("text"))
            except Exception:
                continue
        return "\n".join(chunks)
    finally:
        doc.close()


def resolve_output_path(source: Path, opts: ConversionOptions) -> Path | None:
    """Cikti .md yolunu belirle. `SKIP` politikasinda dosya varsa None doner."""
    out_dir = opts.output_dir or source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{source.stem}.md"

    if not target.exists():
        return target
    if opts.existing_file is ExistingFile.OVERWRITE:
        return target
    if opts.existing_file is ExistingFile.SKIP:
        return None

    for i in range(1, 1000):
        candidate = out_dir / f"{source.stem}-{i}.md"
        if not candidate.exists():
            return candidate
    raise PdfReadError("Cikti dosyasi icin bos isim bulunamadi.")


class Pdf2MdConverter:
    """Docling converter ornegini onbellekleyen donusum motoru."""

    def __init__(self) -> None:
        ensure_env()
        self._cache: dict[tuple, object] = {}

    # -- pipeline kurulumu -------------------------------------------------

    def _build_converter(self, opts: ConversionOptions, use_ocr: bool):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline = PdfPipelineOptions()
        pipeline.do_ocr = use_ocr
        pipeline.do_table_structure = opts.do_tables
        pipeline.do_formula_enrichment = opts.do_formula
        pipeline.do_code_enrichment = opts.do_code
        pipeline.generate_picture_images = opts.image_mode is ImageMode.REFERENCED
        pipeline.generate_page_images = False
        pipeline.images_scale = 2.0  # 144 DPI: okunabilir ama sisirmeyen cozunurluk

        if use_ocr:
            pipeline.ocr_options = self._ocr_options(opts)

        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
        )

    def _ocr_options(self, opts: ConversionOptions):
        """OCR motorunu sec. EasyOCR kuruluysa Turkce icin onu, degilse RapidOCR'i kullan."""
        from docling.datamodel.pipeline_options import EasyOcrOptions, RapidOcrOptions

        try:
            import easyocr  # noqa: F401

            return EasyOcrOptions(lang=list(opts.ocr_langs), force_full_page_ocr=True)
        except ImportError:
            # RapidOCR'da ayri 'tr' modeli yok; Turkce karakterleri kapsayan
            # 'latin' script modeli kullanilir.
            langs = list(opts.ocr_langs)
            lang = "en" if langs == ["en"] else "latin"
            return RapidOcrOptions(lang=[lang], force_full_page_ocr=True)

    def _get_converter(self, opts: ConversionOptions, use_ocr: bool):
        key = (*opts.cache_key(), use_ocr)
        conv = self._cache.get(key)
        if conv is None:
            conv = self._build_converter(opts, use_ocr)
            self._cache[key] = conv
        return conv

    def clear_cache(self) -> None:
        """Yuklu modelleri bellekten bosalt."""
        self._cache.clear()

    # -- donusum -----------------------------------------------------------

    def convert(
        self,
        source: Path,
        opts: ConversionOptions,
        progress: ProgressFn = _noop_progress,
        is_cancelled: CancelFn = _never_cancel,
    ) -> ConversionResult | None:
        """Tek bir PDF'i markdown'a cevir.

        `ExistingFile.SKIP` politikasinda dosya zaten varsa None doner. Iptal
        yalnizca asama sinirlarinda etkili olur: docling'in kendi donusumu
        bolunemez, bu yuzden calisan bir sayfa analizi bitene kadar beklenir.
        """
        source = Path(source)
        started = time.perf_counter()
        warnings: list[str] = []

        def check_cancel() -> None:
            if is_cancelled():
                raise ConversionCancelled()

        progress(2, "PDF okunuyor")
        page_count, has_text, warn = probe_pdf(source)
        if warn:
            warnings.append(warn)
        check_cancel()

        target = resolve_output_path(source, opts)
        if target is None:
            return None

        use_ocr = {
            OcrMode.OFF: False,
            OcrMode.FORCE: True,
            OcrMode.AUTO: not has_text,
        }[opts.ocr_mode]

        if use_ocr and opts.ocr_mode is OcrMode.AUTO:
            warnings.append("Taranmis belge: OCR calistirildi, sonuc daha yavas ve hatali olabilir.")

        progress(8, "Motor hazirlaniyor" + (" (OCR)" if use_ocr else ""))
        converter = self._get_converter(opts, use_ocr)
        check_cancel()

        page_range = opts.page_range or (1, page_count)
        start, end = max(1, page_range[0]), min(page_count, page_range[1])
        if start > end:
            raise PdfReadError(
                f"Gecersiz sayfa araligi: belge {page_count} sayfa, "
                f"{page_range[0]}-{page_range[1]} istendi."
            )
        pages_label = f"{start}-{end}" if (start, end) != (1, page_count) else "tumu"

        progress(15, "Sayfalar analiz ediliyor" + (" (OCR yavas olabilir)" if use_ocr else ""))
        try:
            result = converter.convert(source, page_range=(start, end))
        except ConversionCancelled:
            raise
        except Exception as exc:
            raise PdfReadError(f"Donusum basarisiz: {exc}") from exc
        check_cancel()

        doc = result.document

        progress(80, "Gorseller isleniyor")
        from . import images as images_mod

        images_dir = target.parent / f"{target.stem}_images"
        image_stats = images_mod.process_images(doc, images_dir, images_dir.name, opts)

        captions: dict[str, str] = {}
        if opts.image_mode is ImageMode.REFERENCED:
            for pic in doc.pictures:
                if pic.image is not None and pic.image.uri is not None:
                    try:
                        caption = pic.caption_text(doc)
                    except Exception:
                        caption = ""
                    if caption:
                        captions[str(pic.image.uri).replace("\\", "/")] = caption
        check_cancel()

        progress(88, "Markdown olusturuluyor")
        from docling_core.types.doc import ImageRefMode

        # escape_underscores kapali: LLM'e giden metinde "sqlite_master" gibi kacislar
        # hem gurultu hem gereksiz token.
        # compact_tables: docling varsayilan olarak tablo hucrelerini bosluklarla
        # hizaliyor; 200 karakterlik dolgu satirlari token sayisini iki katina
        # cikarabiliyor. Okunabilirlik kaybi yok, kazanc buyuk.
        md = doc.export_to_markdown(
            image_mode=ImageRefMode.REFERENCED,
            escape_underscores=False,
            compact_tables=True,
        )

        from . import postprocess

        md = postprocess.clean(md, opts, end - start + 1, captions)
        if opts.frontmatter:
            md = postprocess.build_frontmatter(source, page_count, pages_label) + md
        check_cancel()

        progress(95, "Dosya yaziliyor")
        target.write_text(md, encoding="utf-8")

        from . import tokens

        md_tokens = tokens.count_tokens(md)
        pdf_tokens = tokens.count_tokens(extract_raw_text(source, (start, end)))

        progress(100, "Tamamlandi")
        return ConversionResult(
            source=source,
            markdown_path=target,
            images_dir=images_dir if image_stats.saved else None,
            page_count=page_count,
            pages_converted=pages_label,
            pages_converted_count=end - start + 1,
            used_ocr=use_ocr,
            duration=time.perf_counter() - started,
            md_tokens=md_tokens,
            pdf_tokens=pdf_tokens,
            image_stats=image_stats,
            warnings=warnings,
        )
