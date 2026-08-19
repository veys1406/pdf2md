"""Gorsel filtreleme, tekilleştirme ve kaydetme mantigi.

DoclingDocument kurmak pahali oldugundan `process_images`in ihtiyac duydugu
arayuz sahte nesnelerle taklit ediliyor: doc.pictures, item.prov, item.image,
item.get_image(doc).
"""

from dataclasses import dataclass

import pytest
from PIL import Image

from pdf2md.core import images as im
from pdf2md.core.options import ConversionOptions, ImageMode


@dataclass
class FakeBBox:
    l: float
    t: float
    r: float
    b: float


@dataclass
class FakeSize:
    width: float
    height: float


@dataclass
class FakeProv:
    page_no: int
    bbox: FakeBBox


@dataclass
class FakePage:
    size: FakeSize


class FakeImageRef:
    def __init__(self, size=None):
        self.size = size
        self.uri = None


class FakePicture:
    def __init__(self, img, page_no, bbox=None):
        self._img = img
        self.prov = [FakeProv(page_no, bbox or FakeBBox(0, 400, 400, 0))]
        self.image = FakeImageRef()

    def get_image(self, doc=None):
        return self._img


class FakeDoc:
    def __init__(self, pictures, page_size=(600.0, 800.0)):
        self.pictures = pictures
        self.pages = {
            p.prov[0].page_no: FakePage(FakeSize(*page_size)) for p in pictures
        }


def solid(w, h, color=(200, 30, 30)):
    return Image.new("RGB", (w, h), color)


def test_normal_gorsel_kaydedilir(tmp_path):
    doc = FakeDoc([FakePicture(solid(400, 300), 1)])
    stats = im.process_images(doc, tmp_path / "belge_images", "belge_images", ConversionOptions())

    assert stats.saved == 1
    assert (tmp_path / "belge_images" / "p001_img01.png").exists()
    assert str(doc.pictures[0].image.uri).replace("\\", "/") == "belge_images/p001_img01.png"


def test_cok_kucuk_gorsel_elenir(tmp_path):
    doc = FakeDoc([FakePicture(solid(10, 10), 1, FakeBBox(0, 10, 10, 0))])
    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.saved == 0 and stats.skipped_small == 1
    assert doc.pictures[0].image is None


def test_sayfada_kucuk_alan_kaplayan_gorsel_elenir(tmp_path):
    # 480000 puntoluk sayfada 20x20 = 400 punto -> orani %0.08, esik %0.5
    doc = FakeDoc([FakePicture(solid(300, 300), 1, FakeBBox(0, 20, 20, 0))])
    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.skipped_small == 1


def test_her_sayfada_tekrarlayan_logo_atilir(tmp_path):
    logo = solid(200, 200, (10, 10, 10))
    pics = [FakePicture(logo.copy(), sayfa) for sayfa in range(1, 7)]
    doc = FakeDoc(pics)

    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.saved == 0
    assert stats.skipped_repeated == 6
    assert not (tmp_path / "img").exists()


def test_iki_sayfada_gecen_gorsel_logo_sayilmaz(tmp_path):
    ortak = solid(200, 200, (10, 10, 10))
    pics = [FakePicture(ortak.copy(), 1), FakePicture(ortak.copy(), 2)]
    pics += [FakePicture(solid(200, 200, (i * 40, 5, 5)), i) for i in range(3, 7)]
    doc = FakeDoc(pics)

    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.skipped_repeated == 0
    assert stats.saved == 5  # ortak gorsel bir kez kaydedilir
    assert stats.dedup_reused == 1


def test_ayni_gorsel_tek_dosya_paylasir(tmp_path):
    ayni = solid(300, 300)
    doc = FakeDoc([FakePicture(ayni.copy(), 1), FakePicture(ayni.copy(), 1)])

    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.saved == 1 and stats.dedup_reused == 1
    uris = {str(p.image.uri).replace("\\", "/") for p in doc.pictures}
    assert uris == {"img/p001_img01.png"}


def test_genis_gorsel_olceklenir(tmp_path):
    opts = ConversionOptions(max_image_width=800)
    doc = FakeDoc([FakePicture(solid(2400, 1200), 1)])

    im.process_images(doc, tmp_path / "img", "img", opts)

    with Image.open(tmp_path / "img" / "p001_img01.png") as kaydedilen:
        assert kaydedilen.size == (800, 400)


def test_skip_modunda_hicbir_dosya_yazilmaz(tmp_path):
    opts = ConversionOptions(image_mode=ImageMode.SKIP)
    doc = FakeDoc([FakePicture(solid(400, 300), 1)])

    stats = im.process_images(doc, tmp_path / "img", "img", opts)

    assert stats.saved == 0 and stats.total == 1
    assert not (tmp_path / "img").exists()
    assert doc.pictures[0].image is None


def test_okunamayan_gorsel_bozuk_sayilir(tmp_path):
    doc = FakeDoc([FakePicture(None, 1)])
    stats = im.process_images(doc, tmp_path / "img", "img", ConversionOptions())

    assert stats.skipped_broken == 1


def test_dosya_adi_sayfa_ve_sirayla_numaralanir(tmp_path):
    pics = [
        FakePicture(solid(300, 300, (10, 0, 0)), 1),
        FakePicture(solid(300, 300, (20, 0, 0)), 1),
        FakePicture(solid(300, 300, (30, 0, 0)), 7),
    ]
    im.process_images(FakeDoc(pics), tmp_path / "img", "img", ConversionOptions())

    adlar = sorted(p.name for p in (tmp_path / "img").iterdir())
    assert adlar == ["p001_img01.png", "p001_img02.png", "p007_img01.png"]


def test_tekrar_temizligi_kapatilabilir(tmp_path):
    logo = solid(200, 200, (10, 10, 10))
    doc = FakeDoc([FakePicture(logo.copy(), s) for s in range(1, 7)])
    opts = ConversionOptions(drop_repeated_images=False)

    stats = im.process_images(doc, tmp_path / "img", "img", opts)

    assert stats.skipped_repeated == 0 and stats.saved == 1
