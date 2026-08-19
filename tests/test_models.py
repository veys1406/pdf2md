"""Model onbellegi mantiginin testleri.

Gercek indirme yapilmaz; onbellek yapisi gecici klasorde taklit edilir.
"""

from __future__ import annotations

import pytest

from pdf2md.core import models


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    """models_dir'i tmp_path'e cevir; hub/ ve easyocr/ bos baslar."""
    hub = tmp_path / "hub"
    easyocr = tmp_path / "easyocr"
    hub.mkdir()
    easyocr.mkdir()
    monkeypatch.setattr(models, "hf_cache_dir", lambda: hub)
    monkeypatch.setattr(models, "easyocr_dir", lambda: easyocr)
    return tmp_path


def _install_hf(hub, spec, size=1024):
    repo = hub / ("models--" + spec.repo_id.replace("/", "--"))
    snap = repo / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "model.safetensors").write_bytes(b"x" * size)


def _install_easyocr(root):
    model = root / "model"
    model.mkdir(parents=True)
    for name in models._EASYOCR_FILES:
        (model / name).write_bytes(b"x" * 512)


# -- durum tespiti --------------------------------------------------------


def test_bos_onbellekte_zorunlu_modeller_eksik(fake_cache):
    eksik = models.missing()
    assert {s.key for s in eksik} == {"layout", "tables", "ocr"}


def test_istege_bagli_model_yalnizca_istenince_listelenir(fake_cache):
    keys = {s.key for s in models.missing(include_optional=True)}
    assert "formula" in keys


def test_hf_modeli_snapshot_varsa_kurulu_sayilir(fake_cache):
    layout = models.spec("layout")
    assert not models.is_installed(layout)
    _install_hf(fake_cache / "hub", layout)
    assert models.is_installed(layout)


def test_bos_snapshot_klasoru_kurulu_sayilmaz(fake_cache):
    """Yarim kalan indirme snapshots/ acar ama icini doldurmaz."""
    layout = models.spec("layout")
    (fake_cache / "hub" / "models--docling-project--docling-layout-heron" / "snapshots").mkdir(
        parents=True
    )
    assert not models.is_installed(layout)


def test_easyocr_eksik_dosyayla_kurulu_sayilmaz(fake_cache):
    ocr = models.spec("ocr")
    model = fake_cache / "easyocr" / "model"
    model.mkdir(parents=True)
    (model / "craft_mlt_25k.pth").write_bytes(b"x")  # taniyici eksik
    assert not models.is_installed(ocr)

    (model / "latin_g2.pth").write_bytes(b"x")
    assert models.is_installed(ocr)


def test_installed_bytes_inen_veriyi_olcer(fake_cache):
    layout = models.spec("layout")
    assert models.installed_bytes(layout) == 0
    _install_hf(fake_cache / "hub", layout, size=4096)
    assert models.installed_bytes(layout) >= 4096


def test_cache_size_iki_onbellegi_toplar(fake_cache):
    _install_hf(fake_cache / "hub", models.spec("layout"), size=2048)
    _install_easyocr(fake_cache / "easyocr")
    assert models.cache_size() >= 2048 + 1024


# -- yardimcilar ----------------------------------------------------------


def test_format_size_gb_esiginde_gb_gosterir():
    assert models.format_size(500 * models.MB) == "500 MB"
    assert models.format_size(2048 * models.MB) == "2.0 GB"


def test_total_bytes_secili_modelleri_toplar():
    specs = [models.spec("layout"), models.spec("tables")]
    assert models.total_bytes(specs) == sum(s.approx_bytes for s in specs)


def test_spec_bilinmeyen_anahtarda_hata_verir():
    with pytest.raises(KeyError):
        models.spec("yok-boyle-bir-model")


# -- indirme akisi --------------------------------------------------------


def test_download_all_kurulu_modeli_atlar(fake_cache, monkeypatch):
    _install_hf(fake_cache / "hub", models.spec("layout"))
    cagrilanlar = []
    monkeypatch.setattr(models, "download", lambda s: cagrilanlar.append(s.key))

    models.download_all([models.spec("layout"), models.spec("tables")])
    assert cagrilanlar == ["tables"]


def test_download_all_iptalde_durur(fake_cache, monkeypatch):
    cagrilanlar = []
    monkeypatch.setattr(models, "download", lambda s: cagrilanlar.append(s.key))

    with pytest.raises(models.DownloadCancelled):
        models.download_all(
            [models.spec("layout"), models.spec("tables")],
            is_cancelled=lambda: len(cagrilanlar) >= 1,
        )
    assert cagrilanlar == ["layout"]


def test_download_dosya_inmezse_hata_verir(fake_cache, monkeypatch):
    """Indirme sessizce basarisiz olursa "tamam" demeyelim."""
    monkeypatch.setattr(models, "_download_hf", lambda s: None)
    with pytest.raises(models.ModelDownloadError):
        models.download(models.spec("layout"))


def test_download_alt_katman_hatasini_sarmalar(fake_cache, monkeypatch):
    def patla(spec):
        raise OSError("baglanti yok")

    monkeypatch.setattr(models, "_download_hf", patla)
    with pytest.raises(models.ModelDownloadError, match="baglanti yok"):
        models.download(models.spec("tables"))


# -- eski surumden tasima -------------------------------------------------


def test_legacy_easyocr_tasinir(fake_cache, monkeypatch, tmp_path):
    home = tmp_path / "home"
    legacy = home / ".EasyOCR" / "model"
    legacy.mkdir(parents=True)
    for name in models._EASYOCR_FILES:
        (legacy / name).write_bytes(b"model-verisi")
    monkeypatch.setattr(models.Path, "home", staticmethod(lambda: home))

    assert models.migrate_legacy_easyocr() is True
    assert models.is_installed(models.spec("ocr"))


def test_legacy_easyocr_yoksa_sessizce_gecer(fake_cache, monkeypatch, tmp_path):
    monkeypatch.setattr(models.Path, "home", staticmethod(lambda: tmp_path / "bos-ev"))
    assert models.migrate_legacy_easyocr() is False


def test_zaten_kurulusa_tasima_yapilmaz(fake_cache, monkeypatch, tmp_path):
    _install_easyocr(fake_cache / "easyocr")
    home = tmp_path / "home"
    (home / ".EasyOCR" / "model").mkdir(parents=True)
    monkeypatch.setattr(models.Path, "home", staticmethod(lambda: home))
    assert models.migrate_legacy_easyocr() is False
