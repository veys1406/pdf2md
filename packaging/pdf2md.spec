# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: pdf2md tasinabilir Windows derlemesi.

onedir kullaniliyor, onefile DEGIL: paket ~2 GB ve onefile her acilista bunu
temp klasore acardi (30+ sn beklemek ve 2 GB fazladan disk). Klasor derlemesi
sonra 7-Zip SFX ile tek bir kurulum exe'sine sarilir.

Derleme:
    uv run pyinstaller packaging/pdf2md.spec --noconfirm
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

SPEC_DIR = Path(SPECPATH)
ROOT = SPEC_DIR.parent

binaries = []
datas = []
hiddenimports = []


def add(package: str, include_binaries: bool = True) -> None:
    """Paketin modul + veri (+ ikili) dosyalarini derlemeye ekle."""
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas.extend(pkg_datas)
    if include_binaries:
        binaries.extend(pkg_binaries)
    hiddenimports.extend(pkg_hidden)


# -- docling ailesi -------------------------------------------------------
# Bu paketler model tanimlarini, JSON semalarini ve C++ ayristirici
# kaynaklarini veri dosyasi olarak tasiyor; collect_all sarttir.
for pkg in ("docling", "docling_core", "docling_parse", "docling_ibm_models"):
    add(pkg)

# -- OCR ------------------------------------------------------------------
# easyocr karakter listelerini ve ag tanimlarini veri dosyasi olarak tutar.
add("easyocr")

# -- transformers / torch -------------------------------------------------
# transformers'in tamami cok buyuk; yalnizca calisma aninda gereken veri
# dosyalari ve dinamik olarak import edilen model siniflari alinir.
datas += collect_data_files("transformers", include_py_files=False)
hiddenimports += [
    "transformers.models.auto",
    "transformers.models.auto.modeling_auto",
    "transformers.models.auto.processing_auto",
    "transformers.models.auto.tokenization_auto",
]
hiddenimports += collect_submodules("torchvision.models")

# -- tiktoken -------------------------------------------------------------
# Kodlayici eklentileri dinamik yuklenir; ayrica cl100k_base'in BPE dosyasi
# build sirasinda indirilip gomulur ki uygulama tamamen cevrimdisi calissin.
hiddenimports += collect_submodules("tiktoken_ext")
hiddenimports += ["tiktoken_ext.openai_public"]

_tiktoken_cache = SPEC_DIR / "build_cache" / "tiktoken"
_tiktoken_cache.mkdir(parents=True, exist_ok=True)
import os as _os

_os.environ["TIKTOKEN_CACHE_DIR"] = str(_tiktoken_cache)
try:
    import tiktoken as _tiktoken

    _tiktoken.get_encoding("cl100k_base")
    datas += [(str(p), "tiktoken_cache") for p in _tiktoken_cache.iterdir() if p.is_file()]
except Exception as exc:  # ag yoksa: uygulama karakter tahminine duser
    print(f"UYARI: tiktoken onbellegi gomulemedi ({exc}); token sayilari tahmini olacak.")

# -- uygulama varliklari ---------------------------------------------------
datas += [
    (str(ROOT / "assets" / name), "assets")
    for name in ("icon.ico", "logo.png", "logo-mono-light.png", "logo-mono-dark.png")
]

# -- digerleri ------------------------------------------------------------
add("pymupdf")
hiddenimports += ["markdown_it", "mdit_py_plugins", "PIL._tkinter_finder"]

# Kullanilmayan agir bagimliliklar.
# DIKKAT: torch alt modulleri (ozellikle torch.distributed) DISLANMAZ -- docling
# pipeline'i acilirken bunlari import ediyor ve "No module named
# 'torch.distributed'" ile donusumu bastan bitiriyor.
excludes = [
    "tkinter",
    "matplotlib",
    "IPython",
    "notebook",
    "jupyter",
    "pytest",
    "sphinx",
    "tensorboard",
    "torchaudio",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.Qt3DCore",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtQuick",
    "PySide6.QtQml",
]


a = Analysis(
    [str(SPEC_DIR / "entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[str(SPEC_DIR / "runtime_hook.py")],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdf2md",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX torch DLL'lerini bozuyor
    console=False,      # pencere modu: konsol acilmasin
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="pdf2md",
)
