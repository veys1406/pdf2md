"""Token tahmini, cikti yolu cozumleme ve CLI argüman ayristirma."""

import pytest

from pdf2md.cli import parse_page_range
from pdf2md.core import tokens
from pdf2md.core.converter import OutputError, resolve_output_path
from pdf2md.core.options import ConversionOptions, ExistingFile


# -- tokens ---------------------------------------------------------------

def test_bos_metin_sifir_token():
    assert tokens.count_tokens("") == 0


def test_uzun_metin_daha_fazla_token():
    kisa = tokens.count_tokens("merhaba")
    uzun = tokens.count_tokens("merhaba " * 200)
    assert uzun > kisa > 0


@pytest.mark.parametrize(
    "sayi,beklenen",
    [(0, "~0"), (999, "~999"), (1000, "~1K"), (12400, "~12.4K"), (2_500_000, "~2.5M")],
)
def test_token_bicimlendirme(sayi, beklenen):
    assert tokens.format_tokens(sayi) == beklenen


def test_sayfa_goruntusu_maliyeti_sayfayla_orantili():
    assert tokens.page_image_tokens(4) == 4 * tokens.TOKENS_PER_PAGE_IMAGE


def test_tasarruf_yuzdesi():
    assert tokens.savings_percent(1000, 400) == 60
    assert tokens.savings_percent(1000, 1500) == -50  # markdown daha pahaliysa negatif
    assert tokens.savings_percent(0, 100) is None


# -- cikti yolu -----------------------------------------------------------

def test_cikti_pdf_yaninda_olusur(tmp_path):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    assert resolve_output_path(pdf, ConversionOptions()) == tmp_path / "ders.md"


def test_cikti_klasoru_verilirse_oraya_yazilir(tmp_path):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    hedef = tmp_path / "cikti"
    yol = resolve_output_path(pdf, ConversionOptions(output_dir=hedef))
    assert yol == hedef / "ders.md" and hedef.is_dir()


def test_var_olan_dosya_yeniden_adlandirilir(tmp_path):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    (tmp_path / "ders.md").touch()
    (tmp_path / "ders-1.md").touch()
    yol = resolve_output_path(pdf, ConversionOptions(existing_file=ExistingFile.RENAME))
    assert yol == tmp_path / "ders-2.md"


def test_uzerine_yaz_ayni_dosyayi_verir(tmp_path):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    (tmp_path / "ders.md").touch()
    yol = resolve_output_path(pdf, ConversionOptions(existing_file=ExistingFile.OVERWRITE))
    assert yol == tmp_path / "ders.md"


def test_atla_politikasi_none_dondurur(tmp_path):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    (tmp_path / "ders.md").touch()
    assert resolve_output_path(pdf, ConversionOptions(existing_file=ExistingFile.SKIP)) is None


def test_cikti_klasoru_bir_dosyaysa_anlasilir_hata(tmp_path):
    """Kullanici cikti olarak dosya secerse 'beklenmeyen hata' gormemeli."""
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    engel = tmp_path / "aslinda-dosya"
    engel.write_text("x", encoding="utf-8")

    with pytest.raises(OutputError, match="Çıktı klasörü"):
        resolve_output_path(pdf, ConversionOptions(output_dir=engel))


def test_999_kopya_dolduysa_hata_verir(tmp_path, monkeypatch):
    pdf = tmp_path / "ders.pdf"
    pdf.touch()
    (tmp_path / "ders.md").touch()
    # Her ismi "var" gostererek bos isim aramasini tuketiyoruz.
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

    with pytest.raises(OutputError):
        resolve_output_path(pdf, ConversionOptions(existing_file=ExistingFile.RENAME))


# -- sayfa araligi --------------------------------------------------------

@pytest.mark.parametrize(
    "girdi,beklenen",
    [(None, None), ("", None), ("7", (7, 7)), ("5-20", (5, 20)), (" 3 - 9 ", (3, 9))],
)
def test_sayfa_araligi_ayristirma(girdi, beklenen):
    assert parse_page_range(girdi) == beklenen


def test_gecersiz_sayfa_araligi_hata_verir():
    with pytest.raises(ValueError):
        parse_page_range("bes-on")


# -- secenek onbellek anahtari -------------------------------------------

def test_ayni_secenekler_ayni_onbellek_anahtari():
    assert ConversionOptions().cache_key() == ConversionOptions().cache_key()


def test_pipeline_disi_ayar_onbellegi_bozmaz():
    # frontmatter cikti bicimini etkiler, model yuklemesini degil
    a = ConversionOptions(frontmatter=True).cache_key()
    b = ConversionOptions(frontmatter=False).cache_key()
    assert a == b


def test_ocr_ayari_onbellegi_ayirir():
    from pdf2md.core.options import OcrMode

    a = ConversionOptions(ocr_mode=OcrMode.OFF).cache_key()
    b = ConversionOptions(ocr_mode=OcrMode.FORCE).cache_key()
    assert a != b
