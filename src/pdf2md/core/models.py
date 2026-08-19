r"""Model onbelleginin durumu ve indirilmesi.

Uygulama ilk acilista bos bir onbellekle gelir; docling modelleri kendisi
indirir ama bunu donusum sirasinda, sessizce ve iptal edilemez sekilde yapar.
Kullanici 1 GB'lik indirmeyi "program dondu" diye yasamasin diye modeller
burada ONCEDEN, gorunur bir sihirbazla indirilir.

Onbellek iki ayri yerde tutulur:
  - HF modelleri  -> %LOCALAPPDATA%\pdf2md\models\hub  (HF_HOME uzerinden)
  - EasyOCR .pth  -> %LOCALAPPDATA%\pdf2md\models\easyocr  (EASYOCR_MODULE_PATH)
EasyOCR kendi indiricisini kullanir, huggingface_hub'i degil; bu yuzden iki
farkli `kind` var.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .paths import easyocr_dir, ensure_env, hf_cache_dir

log = logging.getLogger(__name__)

MB = 1024 * 1024


class ModelDownloadError(Exception):
    """Model indirilemedi (baglanti yok, disk dolu, repo erisilemez)."""


class DownloadCancelled(Exception):
    """Kullanici indirmeyi iptal etti."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    title: str
    detail: str
    approx_bytes: int   # ilerleme yuzdesi icin; olculmus gercek boyutlar
    required: bool
    kind: str           # "hf" | "easyocr"
    repo_id: str = ""
    revision: str = ""


# Boyutlar dolu bir onbellek uzerinde olculdu (du -sh), ~%5 sapma normal.
SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="layout",
        title="Sayfa düzeni",
        detail="Başlık, paragraf, tablo ve görsel bloklarını tanır. Zorunlu.",
        approx_bytes=172 * MB,
        required=True,
        kind="hf",
        repo_id="docling-project/docling-layout-heron",
        revision="main",
    ),
    ModelSpec(
        key="tables",
        title="Tablo yapısı",
        detail="Tabloları satır/sütun olarak çıkarır (TableFormer).",
        approx_bytes=358 * MB,
        required=True,
        kind="hf",
        repo_id="docling-project/docling-models",
        revision="v2.3.0",
    ),
    ModelSpec(
        key="ocr",
        title="OCR (Türkçe + İngilizce)",
        detail="Taranmış, metin katmanı olmayan PDF'leri okur.",
        approx_bytes=98 * MB,
        required=True,
        kind="easyocr",
    ),
    ModelSpec(
        key="formula",
        title="Formül → LaTeX",
        detail="Formülleri LaTeX'e çevirir. İsteğe bağlı, CPU'da çok yavaş.",
        approx_bytes=640 * MB,
        required=False,
        kind="hf",
        repo_id="docling-project/CodeFormulaV2",
        revision="main",
    ),
)

# EasyOCR'in tr+en icin indirdigi dosyalar: detector + latin tanıyıcı.
_EASYOCR_FILES = ("craft_mlt_25k.pth", "latin_g2.pth")


def spec(key: str) -> ModelSpec:
    for s in SPECS:
        if s.key == key:
            return s
    raise KeyError(key)


# -- onbellek durumu ------------------------------------------------------


def _hf_repo_dir(s: ModelSpec) -> Path:
    return hf_cache_dir() / ("models--" + s.repo_id.replace("/", "--"))


def _dir_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def is_installed(s: ModelSpec) -> bool:
    """Model onbellekte kullanilabilir durumda mi?

    Yarim inen dosyalar (.incomplete) sayilmaz: HF onlari blobs altinda tutar,
    biz snapshots altindaki cozulmus dosyalara bakariz.
    """
    if s.kind == "easyocr":
        d = easyocr_dir() / "model"
        return all((d / name).is_file() for name in _EASYOCR_FILES)

    snapshots = _hf_repo_dir(s) / "snapshots"
    if not snapshots.is_dir():
        return False
    for snap in snapshots.iterdir():
        if snap.is_dir() and any(snap.iterdir()):
            return True
    return False


def installed_bytes(s: ModelSpec) -> int:
    """Su ana kadar diske inen bayt (yarim dosyalar dahil).

    Ilerleme cubugu icin kullanilir; HF/EasyOCR indirme ilerlemesini disariya
    guvenilir sekilde vermedigi icin dizin boyutu olculur.
    """
    if s.kind == "easyocr":
        return _dir_size(easyocr_dir())
    return _dir_size(_hf_repo_dir(s))


def missing(include_optional: bool = False) -> list[ModelSpec]:
    """Eksik modeller. Varsayilan olarak yalnizca zorunlu olanlar."""
    return [
        s
        for s in SPECS
        if (s.required or include_optional) and not is_installed(s)
    ]


def total_bytes(specs: Iterable[ModelSpec]) -> int:
    return sum(s.approx_bytes for s in specs)


def format_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * MB:
        return f"{num_bytes / (1024 * MB):.1f} GB"
    return f"{num_bytes / MB:.0f} MB"


def cache_size() -> int:
    """Onbellegin toplam disk kullanimi."""
    return _dir_size(hf_cache_dir()) + _dir_size(easyocr_dir())


# -- indirme --------------------------------------------------------------


StatusFn = Callable[[ModelSpec], None]
CancelFn = Callable[[], bool]


def _never_cancel() -> bool:
    return False


def _download_hf(s: ModelSpec) -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=s.repo_id, revision=s.revision)


def _download_easyocr() -> None:
    """EasyOCR modellerini indir.

    Reader kurmak modelleri hem indirir hem RAM'e yukler; ayri bir indirme API'si
    yok. Nesne hemen birakilir, bellek geri gelir.
    """
    import easyocr

    reader = easyocr.Reader(["tr", "en"], gpu=False, verbose=False)
    del reader


def download(s: ModelSpec) -> None:
    """Tek bir modeli indir. Basarisiz olursa ModelDownloadError firlatir."""
    ensure_env()
    log.info("Model indiriliyor: %s", s.key)
    try:
        if s.kind == "easyocr":
            _download_easyocr()
        else:
            _download_hf(s)
    except Exception as exc:
        raise ModelDownloadError(f"{s.title}: {exc}") from exc

    if not is_installed(s):
        raise ModelDownloadError(f"{s.title}: indirme tamamlandı ama dosyalar bulunamadı.")


def download_all(
    specs: Iterable[ModelSpec],
    on_status: StatusFn = lambda s: None,
    is_cancelled: CancelFn = _never_cancel,
) -> None:
    """Verilen modelleri sirayla indir.

    Iptal yalnizca model sinirlarinda etkili: tek bir snapshot_download
    bolunemiyor, bu yuzden calisan indirme bitene kadar beklenir.
    """
    for s in specs:
        if is_cancelled():
            raise DownloadCancelled()
        if is_installed(s):
            continue
        on_status(s)
        download(s)
    if is_cancelled():
        raise DownloadCancelled()


# -- eski surumden tasima -------------------------------------------------


def migrate_legacy_easyocr() -> bool:
    """EasyOCR modellerini ~/.EasyOCR'dan uygulama klasorune tasi.

    EASYOCR_MODULE_PATH eklenmeden onceki surumler modelleri kullanicinin ev
    dizinine indiriyordu. 98 MB'i yeniden indirtmemek icin bir kez tasinir.
    """
    target = easyocr_dir() / "model"
    if all((target / name).is_file() for name in _EASYOCR_FILES):
        return False

    legacy = Path.home() / ".EasyOCR" / "model"
    if not legacy.is_dir():
        return False

    moved = False
    target.mkdir(parents=True, exist_ok=True)
    for name in _EASYOCR_FILES:
        src = legacy / name
        if src.is_file() and not (target / name).is_file():
            try:
                shutil.copy2(src, target / name)
                moved = True
            except OSError as exc:
                log.warning("EasyOCR modeli taşınamadı (%s): %s", name, exc)
    return moved
