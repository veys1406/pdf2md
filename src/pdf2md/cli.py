"""Arayuzsuz komut satiri girisi.

Motoru GUI olmadan denemek/otomasyonda kullanmak icin:
    uv run python -m pdf2md.cli dosya.pdf --cikti C:\\ciktilar --sayfa 1-10
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .core.converter import ConversionCancelled, Pdf2MdConverter, PdfReadError
from .core.options import ConversionOptions, ExistingFile, ImageMode, OcrMode
from .core.tokens import format_tokens, page_image_tokens, savings_percent


def parse_page_range(value: str | None) -> tuple[int, int] | None:
    """'5-20' veya '7' bicimini (baslangic, bitis) olarak coz."""
    if not value:
        return None
    value = value.strip()
    if "-" in value:
        a, _, b = value.partition("-")
        return int(a), int(b)
    n = int(value)
    return n, n


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pdf2md",
        description="PDF dosyalarini LLM dostu Markdown'a cevirir.",
    )
    p.add_argument("pdf", nargs="*", type=Path, help="Cevrilecek PDF dosyalari")
    p.add_argument(
        "--modelleri-indir",
        action="store_true",
        help="Gerekli modelleri indirip cik (ilk kurulum / paketleme testi)",
    )
    p.add_argument("--cikti", type=Path, default=None, help="Cikti klasoru (varsayilan: PDF'in yani)")
    p.add_argument("--sayfa", default=None, help="Sayfa araligi, orn. 5-20")
    p.add_argument(
        "--ocr",
        choices=[m.value for m in OcrMode],
        default=OcrMode.AUTO.value,
        help="OCR modu (varsayilan: auto)",
    )
    p.add_argument("--gorsel-yok", action="store_true", help="Gorselleri tamamen atla")
    # Varsayilan KAPALI: CodeFormulaV2 CPU'da bir belgeyi saatlerce isleyebiliyor.
    p.add_argument("--formul", action="store_true", help="Formulleri LaTeX'e cevir (cok yavas)")
    p.add_argument("--frontmatter-yok", action="store_true", help="YAML frontmatter ekleme")
    p.add_argument("--uzerine-yaz", action="store_true", help="Var olan .md dosyasinin uzerine yaz")
    p.add_argument("-v", "--ayrintili", action="store_true", help="Ayrintili gunluk")
    return p


def download_models_cli(with_formula: bool = False) -> int:
    """Modelleri indir ve durumu yazdir. Arayuzsuz ilk kurulum icin."""
    from .core import models

    models.migrate_legacy_easyocr()
    wanted = [s for s in models.SPECS if s.required or (with_formula and s.key == "formula")]
    todo = [s for s in wanted if not models.is_installed(s)]

    for s in wanted:
        durum = "kurulu" if models.is_installed(s) else "eksik"
        print(f"  {s.key:8s} {models.format_size(s.approx_bytes):>8s}  {durum}")

    if not todo:
        print("Tum modeller hazir.")
        return 0

    print(f"\n{len(todo)} model indirilecek (~{models.format_size(models.total_bytes(todo))})...")
    try:
        models.download_all(todo, on_status=lambda s: print(f"  indiriliyor: {s.title}", flush=True))
    except models.ModelDownloadError as exc:
        print(f"HATA: {exc}")
        return 1
    print("Modeller hazir.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.ayrintili else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.modelleri_indir:
        return download_models_cli(with_formula=args.formul)

    if not args.pdf:
        build_parser().print_usage()
        print("Hata: cevrilecek en az bir PDF verin (veya --modelleri-indir).")
        return 2

    opts = ConversionOptions(
        output_dir=args.cikti,
        page_range=parse_page_range(args.sayfa),
        ocr_mode=OcrMode(args.ocr),
        image_mode=ImageMode.SKIP if args.gorsel_yok else ImageMode.REFERENCED,
        do_formula=args.formul,
        frontmatter=not args.frontmatter_yok,
        existing_file=ExistingFile.OVERWRITE if args.uzerine_yaz else ExistingFile.RENAME,
    )

    engine = Pdf2MdConverter()
    failed = 0

    for pdf in args.pdf:
        print(f"\n=== {pdf.name} ===")

        def show(pct: int, msg: str) -> None:
            print(f"  [{pct:3d}%] {msg}", flush=True)

        try:
            res = engine.convert(pdf, opts, progress=show)
        except ConversionCancelled:
            print("  iptal edildi")
            failed += 1
            continue
        except (PdfReadError, OSError) as exc:
            print(f"  HATA: {exc}")
            failed += 1
            continue

        if res is None:
            print("  atlandi (cikti dosyasi zaten var)")
            continue

        st = res.image_stats
        vision = page_image_tokens(res.pages_converted_count)
        pct = savings_percent(vision, res.md_tokens)
        print(f"  -> {res.markdown_path}")
        print(f"  sure: {res.duration:.1f} sn | sayfa: {res.pages_converted}/{res.page_count}"
              f"{' | OCR' if res.used_ocr else ''}")
        if st is not None:
            print(f"  gorsel: {st.saved} kaydedildi, {st.dropped} elendi "
                  f"(kucuk={st.skipped_small}, tekrar={st.skipped_repeated}, "
                  f"bozuk={st.skipped_broken}), {st.dedup_reused} tekrar kullanildi")
        print(f"  token: {format_tokens(res.md_tokens)}"
              f" | ham PDF metni {format_tokens(res.pdf_tokens)}"
              f" | sayfa goruntusu olarak {format_tokens(vision)}"
              + (f" (%{pct} tasarruf)" if pct is not None else ""))
        for w in res.warnings:
            print(f"  uyari: {w}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
