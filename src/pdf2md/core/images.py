r"""Gorsel cikarma, filtreleme ve kaydetme.

Docling'in kendi `save_as_markdown(artifacts_dir=...)` yolu iki sorun uretiyor:
markdown'a MUTLAK dosya yolu yaziyor (dosyayi tasiyinca linkler kiriliyor) ve
her sayfada tekrarlayan logoyu ayri dosya olarak defalarca kaydediyor. Bu yuzden
gorselleri burada kendimiz isliyoruz: filtrele, tekilleştir, olcekle, `pNNN_imgMM`
duzeninde kaydet ve picture item'in uri'sini RELATIF yola cevir.
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .options import ConversionOptions, ImageMode

log = logging.getLogger(__name__)


@dataclass
class ImageStats:
    """Bir donusumde gorsellere ne oldugunun ozeti."""

    total: int = 0
    saved: int = 0
    skipped_small: int = 0
    skipped_repeated: int = 0
    skipped_broken: int = 0
    dedup_reused: int = 0
    files: list[Path] = field(default_factory=list)

    @property
    def dropped(self) -> int:
        return self.skipped_small + self.skipped_repeated + self.skipped_broken


def _image_hash(img: Image.Image) -> str:
    """Gorsel iceriginin hash'i. Ayni logo farkli sayfalarda ayni hash'i verir."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=False)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:16]


def _is_too_small(img: Image.Image, area_ratio: float | None, opts: ConversionOptions) -> bool:
    """Gorsel gurultu mu? Hem piksel boyutuna hem sayfadaki alan oranina bakilir.

    `area_ratio` gorselin sayfa uzerinde kapladigi alanin oranidir (bbox / sayfa);
    ikisi de PDF puntosunda oldugu icin render olceginden bagimsizdir.
    """
    w, h = img.size
    if w < opts.min_image_px or h < opts.min_image_px:
        return True
    if area_ratio is not None and area_ratio < opts.min_image_area_ratio:
        return True
    return False


def _downscale(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    return img.resize((max_width, max(1, round(img.height * ratio))), Image.LANCZOS)


def _save_png(img: Image.Image, path: Path) -> None:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    img.save(path, format="PNG", optimize=True)


def collect_candidates(doc, opts: ConversionOptions) -> list[dict]:
    """Belgedeki gorselleri sayfa numarasi, boyut ve hash bilgisiyle topla.

    Donen her kayit: {"item", "page", "image", "hash", "area_ratio"}.
    Bozuk/okunamayan gorseller `image=None` ile isaretlenir.
    """
    out: list[dict] = []
    for item in doc.pictures:
        page_no = None
        area_ratio = None
        if item.prov:
            prov = item.prov[0]
            page_no = prov.page_no
            page = doc.pages.get(page_no) if doc.pages else None
            if page is not None and page.size is not None and prov.bbox is not None:
                page_area = float(page.size.width) * float(page.size.height)
                bbox = prov.bbox
                bbox_area = abs(bbox.r - bbox.l) * abs(bbox.t - bbox.b)
                if page_area > 0:
                    area_ratio = bbox_area / page_area
        try:
            img = item.get_image(doc=doc)
        except Exception as exc:  # bozuk gomulu gorsel
            log.warning("Gorsel okunamadi (sayfa %s): %s", page_no, exc)
            img = None
        out.append(
            {
                "item": item,
                "page": page_no or 0,
                "image": img,
                "hash": _image_hash(img) if img is not None else None,
                "area_ratio": area_ratio,
            }
        )
    return out


def _repeated_hashes(candidates: list[dict], opts: ConversionOptions) -> set[str]:
    """Sayfalarin buyuk kismında tekrarlayan gorsellerin hash'leri (logo/filigran)."""
    if not opts.drop_repeated_images:
        return set()

    pages_with: dict[str, set[int]] = {}
    all_pages: set[int] = set()
    for c in candidates:
        if c["hash"] is None:
            continue
        all_pages.add(c["page"])
        pages_with.setdefault(c["hash"], set()).add(c["page"])

    # Tek sayfalik belgede "her sayfada tekrarliyor" kiyaslamasi anlamsiz
    if len(all_pages) < 3:
        return set()

    threshold = max(
        opts.repeated_image_min_pages,
        opts.repeated_image_threshold * len(all_pages),
    )
    return {h for h, pages in pages_with.items() if len(pages) >= threshold}


def process_images(doc, images_dir: Path, rel_prefix: str, opts: ConversionOptions) -> ImageStats:
    """Belgedeki gorselleri diske yaz ve picture uri'lerini relatif yola cevir.

    Elenen gorsellerin `image` alani None birakilir; markdown serializer bunlar icin
    `<!-- image -->` yer tutucusu uretir, postprocess bunlari temizler.
    """
    from docling_core.types.doc import ImageRef, Size

    def make_ref(rel: str, img: Image.Image) -> ImageRef:
        """Picture item icin relatif yollu ImageRef. Olcu diske YAZILAN gorselden
        alinir; olcekleme sonrasi degeri yansitmasi icin."""
        return ImageRef(
            mimetype="image/png",
            dpi=72,
            size=Size(width=float(img.width), height=float(img.height)),
            uri=Path(rel),
        )

    stats = ImageStats()

    if opts.image_mode is ImageMode.SKIP:
        for item in doc.pictures:
            item.image = None
            stats.total += 1
        return stats

    candidates = collect_candidates(doc, opts)
    stats.total = len(candidates)
    if not candidates:
        return stats

    repeated = _repeated_hashes(candidates, opts)
    hash_to_rel: dict[str, dict] = {}
    per_page_counter: dict[int, int] = {}
    made_dir = False

    for c in candidates:
        item, img = c["item"], c["image"]

        if img is None:
            item.image = None
            stats.skipped_broken += 1
            continue

        if c["hash"] in repeated:
            item.image = None
            stats.skipped_repeated += 1
            continue

        if _is_too_small(img, c["area_ratio"], opts):
            item.image = None
            stats.skipped_small += 1
            continue

        # Ayni gorsel birden fazla yerde geciyorsa tek dosya paylasilir
        existing = hash_to_rel.get(c["hash"])
        if existing is not None:
            item.image = make_ref(existing["rel"], existing["image"])
            stats.dedup_reused += 1
            continue

        if not made_dir:
            images_dir.mkdir(parents=True, exist_ok=True)
            made_dir = True

        page = c["page"]
        per_page_counter[page] = per_page_counter.get(page, 0) + 1
        name = f"p{page:03d}_img{per_page_counter[page]:02d}.png"
        target = images_dir / name

        final = _downscale(img, opts.max_image_width)
        try:
            _save_png(final, target)
        except Exception as exc:
            log.warning("Gorsel kaydedilemedi %s: %s", target, exc)
            item.image = None
            stats.skipped_broken += 1
            continue

        rel = f"{rel_prefix}/{name}"
        hash_to_rel[c["hash"]] = {"rel": rel, "image": final}
        item.image = make_ref(rel, final)
        stats.saved += 1
        stats.files.append(target)

    return stats
