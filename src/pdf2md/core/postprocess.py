r"""Docling ciktisini LLM'e verilmeye hazir markdown'a cevirir.

Yapilanlar: bos gorsel yer tutucularini temizleme, gorsel linklerini relatif ve
POSIX bicimine cevirme, alt metin ekleme, tekrarlayan ust/alt bilgi satirlarini
atma, satir sonu tirelemesini birlestirme, baslik seviyelerini normalize etme ve
gereksiz bos satirlari sikistirma.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .options import ConversionOptions

IMAGE_PLACEHOLDER = "<!-- image -->"
_IMG_LINK = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_PAGE_BREAK = re.compile(r"^\s*<!--\s*page break\s*-->\s*$", re.IGNORECASE)
_SEPARATOR_CELL = re.compile(r":?-+:?")

# "kelime-\ndevam" birlesmesi. Turkce'de satir sonu tirelemesi yaygin, ama
# "Turk-Islam", "e-posta" gibi gercek tireleri bozmamak icin yalnizca tireden
# sonra satir sonu gelen VE devami kucuk harfle baslayan durumu birlestiriyoruz.
_HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-zçğıöşü])")


def strip_image_placeholders(md: str) -> str:
    """Elenen gorsellerden kalan `<!-- image -->` yer tutucularini sil."""
    lines = [ln for ln in md.split("\n") if ln.strip() != IMAGE_PLACEHOLDER]
    return "\n".join(lines)


def fix_image_links(md: str, captions: dict[str, str] | None = None) -> str:
    """Gorsel linklerini POSIX ayraciyla yaz ve varsa alt metin ekle.

    Docling `![Image](...)` sabit alt metnini uretiyor; caption bulunan gorsellerde
    onu okunabilir bir alt metinle degistiriyoruz.
    """
    captions = captions or {}

    def repl(m: re.Match) -> str:
        path = m.group("path").replace("\\", "/").strip()
        alt = m.group("alt")
        caption = captions.get(path)
        if caption:
            alt = caption.replace("]", ")").replace("\n", " ").strip()
        elif alt in ("Image", ""):
            alt = Path(path).stem
        return f"![{alt}]({path})"

    return _IMG_LINK.sub(repl, md)


def strip_repeated_lines(md: str, page_count: int, threshold: float = 0.6) -> str:
    """Sayfa ust/alt bilgisi gibi tekrar eden kisa satirlari sil.

    Sadece kisa (<=80 karakter), baslik/liste/tablo/gorsel olmayan duz satirlar
    aday; belge 3 sayfadan kisaysa hic dokunulmaz.
    """
    if page_count < 3:
        return md

    lines = md.split("\n")
    counts = Counter()
    for ln in lines:
        s = ln.strip()
        if not s or len(s) > 80:
            continue
        if s.startswith(("#", "-", "*", ">", "|", "!", "```")):
            continue
        counts[s] += 1

    limit = max(3, int(page_count * threshold))
    junk = {s for s, n in counts.items() if n >= limit}
    if not junk:
        return md

    return "\n".join(ln for ln in lines if ln.strip() not in junk)


def fix_hyphenation(md: str) -> str:
    """Satir sonundaki tirelemeyi birlestir (kod bloklari ve tablolar haric)."""
    parts = md.split("```")
    for i in range(0, len(parts), 2):  # cift indeksler kod blogu DISI
        parts[i] = _HYPHEN_BREAK.sub(r"\1", parts[i])
    return "```".join(parts)


def normalize_headings(md: str) -> str:
    """En ust baslik `#` olacak sekilde kaydir ve atlanan seviyeleri sikistir."""
    levels = sorted({len(m.group(1)) for ln in md.split("\n") if (m := _HEADING.match(ln))})
    if not levels or levels == list(range(1, len(levels) + 1)):
        return md

    mapping = {lvl: i + 1 for i, lvl in enumerate(levels)}
    out = []
    for ln in md.split("\n"):
        m = _HEADING.match(ln)
        if m:
            new_level = min(6, mapping[len(m.group(1))])
            out.append("#" * new_level + " " + m.group(2))
        else:
            out.append(ln)
    return "\n".join(out)


def collapse_blank_lines(md: str) -> str:
    """Satir sonu bosluklarini kirp, 2'den fazla ardisik bos satiri teke indir."""
    md = "\n".join(ln.rstrip() for ln in md.split("\n"))
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def is_separator_row(row: str) -> bool:
    """GFM tablo ayirici satiri mi (`| --- | :--: |`)?"""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return bool(cells) and all(_SEPARATOR_CELL.fullmatch(c) for c in cells if c != "")


def collapse_duplicate_cells(row: str, min_run: int = 3) -> str:
    """Birlesik hucrelerin sutunlara kopyalanmasini geri al.

    PDF'te 7 sutuna yayilan tek bir hucre docling ciktisinda ayni degeri 7 kez
    tekrarliyor ("| Yok | Yok | Yok | ..."). Ust uste `min_run` kez tekrarlayan
    hucrelerin ilki disindakiler bosaltilir. Esik 3: gercek veride yan yana uc
    ayni deger nadir, birlesik hucrede ise kural.
    """
    if is_separator_row(row):
        return row

    cells = row.split("|")
    if len(cells) < 4:
        return row

    i = 1
    while i < len(cells) - 1:
        value = cells[i].strip()
        if not value:
            i += 1
            continue
        j = i + 1
        while j < len(cells) - 1 and cells[j].strip() == value:
            j += 1
        if j - i >= min_run:
            for k in range(i + 1, j):
                cells[k] = " "
        i = j
    return "|".join(cells)


def fix_tables(md: str) -> str:
    """Tamamen bos tablolari at ve satir sutun sayilarini basliga hizala."""
    out: list[str] = []
    block: list[str] = []

    def flush() -> None:
        if not block:
            return
        header_cols = block[0].count("|") - 1
        if header_cols < 1:
            out.extend(block)
            block.clear()
            return
        # Hicbir hucresinde icerik olmayan tabloyu tamamen at
        content = "".join(block).replace("|", "").replace("-", "").strip()
        if not content:
            block.clear()
            return
        for row in block:
            cols = row.count("|") - 1
            if cols < header_cols:
                row = row.rstrip() + " |" * (header_cols - cols)
            out.append(collapse_duplicate_cells(row))
        block.clear()

    for ln in md.split("\n"):
        if ln.lstrip().startswith("|"):
            block.append(ln)
        else:
            flush()
            out.append(ln)
    flush()
    return "\n".join(out)


def build_frontmatter(source: Path, page_count: int, pages_converted: str) -> str:
    """Kaynak bilgisini tasiyan YAML frontmatter."""
    title = source.stem.replace("_", " ").strip()
    return (
        "---\n"
        f'kaynak: "{source.name}"\n'
        f'baslik: "{title}"\n'
        f"sayfa_sayisi: {page_count}\n"
        f'donusturulen_sayfalar: "{pages_converted}"\n'
        f'tarih: "{datetime.now().strftime("%Y-%m-%d %H:%M")}"\n'
        "---\n\n"
    )


def clean(
    md: str,
    opts: ConversionOptions,
    page_count: int,
    captions: dict[str, str] | None = None,
) -> str:
    """Tum temizlik adimlarini sirayla uygula."""
    md = strip_image_placeholders(md)
    md = fix_image_links(md, captions)
    md = _PAGE_BREAK.sub("", md)
    if opts.strip_repeated_headers:
        md = strip_repeated_lines(md, page_count, opts.repeated_line_threshold)
    if opts.fix_hyphenation:
        md = fix_hyphenation(md)
    if opts.normalize_headings:
        md = normalize_headings(md)
    md = fix_tables(md)
    return collapse_blank_lines(md)
