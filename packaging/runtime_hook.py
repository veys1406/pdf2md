"""Paketlenmis exe icin calisma zamani hazirligi.

PyInstaller bu dosyayi uygulamanin kendi kodundan ONCE calistirir. Burada
yalnizca ortam degiskenleri ayarlanir; is mantigi yok.
"""

import os
import sys

_MEIPASS = getattr(sys, "_MEIPASS", None)

if _MEIPASS:
    # tiktoken'in BPE dosyasi derlemeye gomuldu: cevrimdisi de dogru token
    # sayimi yapilabilsin, uygulama ilk acilista aga cikmasin.
    cache = os.path.join(_MEIPASS, "tiktoken_cache")
    if os.path.isdir(cache):
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", cache)

    # PyInstaller'da stdout/stderr pencere modunda None olabiliyor; bazi
    # kutuphaneler (tqdm, huggingface_hub) buna hazirliksiz.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
