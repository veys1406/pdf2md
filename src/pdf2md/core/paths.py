r"""Uygulama dizinleri ve model onbellegi.

Modeller kullanicinin profilini kirletmemek icin %LOCALAPPDATA%\pdf2md altinda
tutulur. `ensure_env()` huggingface_hub ilk kez import edilmeden once cagrilmali,
aksi halde HF kendi varsayilan onbellegini (~/.cache/huggingface) kullanir.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "pdf2md"


def app_data_dir() -> Path:
    r"""Uygulama verisi kok dizini (%LOCALAPPDATA%\pdf2md)."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".pdf2md"


def models_dir() -> Path:
    return app_data_dir() / "models"


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def hf_cache_dir() -> Path:
    """huggingface_hub'in model onbellegi (HF_HOME/hub)."""
    return models_dir() / "hub"


def easyocr_dir() -> Path:
    """EasyOCR .pth dosyalarinin kok dizini (EASYOCR_MODULE_PATH).

    EasyOCR huggingface'i kullanmiyor; ayarlanmazsa modelleri ~/.EasyOCR
    altina, yani kullanicinin ev dizinine indirir.
    """
    return models_dir() / "easyocr"


def is_frozen() -> bool:
    """PyInstaller ile paketlenmis halde mi calisiyoruz?"""
    return getattr(sys, "frozen", False)


def resource_path(*parts: str) -> Path:
    """Paketle birlikte gelen varlik dosyasinin yolu (logo, ikon).

    Paketlenmis derlemede dosyalar `sys._MEIPASS` altina aciliyor; gelistirme
    ortaminda depo kokundeki `assets/` klasoru kullaniliyor.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base).joinpath(*parts)
    return Path(__file__).resolve().parent.parent.parent.parent.joinpath(*parts)


def icon_path() -> Path:
    return resource_path("assets", "icon.ico")


def logo_path() -> Path:
    return resource_path("assets", "logo.png")


def logo_mono_path(dark: bool) -> Path:
    """Zeminsiz logo; koyu arayuzde beyaz, acik arayuzde siyah cizim."""
    name = "logo-mono-light.png" if dark else "logo-mono-dark.png"
    return resource_path("assets", name)


_env_ready = False


def ensure_env() -> None:
    """HF onbellek yolunu ayarla ve gerekli dizinleri olustur.

    huggingface_hub / torch import edilmeden ONCE cagrilmalidir.
    """
    global _env_ready
    if _env_ready:
        return

    models = models_dir()
    models.mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(models))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(models / "transformers"))
    # Telemetriyi kapat: uygulama tamamen offline calisabilmeli
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    # EasyOCR'in kendi onbellegi: easyocr.config import edildiginde okundugu icin
    # bu satir da her import'tan once calismali.
    easyocr_dir().mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("EASYOCR_MODULE_PATH", str(easyocr_dir()))
    # NOT: DOCLING_ARTIFACTS_PATH bilerek ayarlanmiyor; dolu olmayan bir klasoru
    # gosterdiginde docling hata veriyor. HF_HOME zaten modelleri buraya indiriyor.
    # torch'un CPU cekirdek sayisini sinirla: arayuz donmasin
    os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 4) // 2)))

    _env_ready = True
