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


def is_frozen() -> bool:
    """PyInstaller ile paketlenmis halde mi calisiyoruz?"""
    return getattr(sys, "frozen", False)


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
    # NOT: DOCLING_ARTIFACTS_PATH bilerek ayarlanmiyor; dolu olmayan bir klasoru
    # gosterdiginde docling hata veriyor. HF_HOME zaten modelleri buraya indiriyor.
    # torch'un CPU cekirdek sayisini sinirla: arayuz donmasin
    os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 4) // 2)))

    _env_ready = True
