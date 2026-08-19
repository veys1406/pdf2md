"""postprocess katmaninin metin temizleme kurallari."""

from pathlib import Path

import pytest

from pdf2md.core import postprocess as pp
from pdf2md.core.options import ConversionOptions


def test_gorsel_yer_tutuculari_silinir():
    md = "Metin\n\n<!-- image -->\n\nDevam"
    assert "<!-- image -->" not in pp.strip_image_placeholders(md)


def test_gorsel_linki_posix_ayraca_cevrilir():
    md = r"![Image](belge_images\p001_img01.png)"
    assert pp.fix_image_links(md) == "![p001_img01](belge_images/p001_img01.png)"


def test_caption_varsa_alt_metin_olur():
    md = "![Image](img/p001_img01.png)"
    out = pp.fix_image_links(md, {"img/p001_img01.png": "Sekil 3: Akis semasi"})
    assert out == "![Sekil 3: Akis semasi](img/p001_img01.png)"


def test_tekrarlayan_ustbilgi_silinir():
    lines = []
    for i in range(10):
        lines += ["Lokman Hekim Universitesi", f"Sayfa {i} icerigi burada."]
    md = "\n".join(lines)
    out = pp.strip_repeated_lines(md, page_count=10)
    assert "Lokman Hekim Universitesi" not in out
    assert "Sayfa 3 icerigi burada." in out


def test_kisa_belgede_tekrar_temizligi_yapilmaz():
    md = "Basliktir\nBasliktir\nBasliktir"
    assert pp.strip_repeated_lines(md, page_count=2) == md


def test_baslik_ve_tablo_satirlari_tekrar_temizliginden_muaf():
    md = "\n".join(["# Ayni Baslik", "| a | b |"] * 8)
    out = pp.strip_repeated_lines(md, page_count=8)
    assert "# Ayni Baslik" in out and "| a | b |" in out


def test_satir_sonu_tirelemesi_birlestirilir():
    assert pp.fix_hyphenation("istatis-\ntiksel") == "istatistiksel"


def test_gercek_tire_bozulmaz():
    # Devami buyuk harfle basliyorsa gercek bilesik kelimedir
    assert pp.fix_hyphenation("Turk-\nIslam") == "Turk-\nIslam"


def test_kod_blogundaki_tire_bozulmaz():
    md = "```\nlong-\nname\n```"
    assert pp.fix_hyphenation(md) == md


def test_baslik_seviyeleri_normalize_edilir():
    md = "## Ust\n\n#### Alt\n\nmetin"
    assert pp.normalize_headings(md) == "# Ust\n\n## Alt\n\nmetin"


def test_zaten_normal_basliklar_degismez():
    md = "# Bir\n\n## Iki"
    assert pp.normalize_headings(md) == md


def test_birlesik_hucre_tekrari_bosaltilir():
    row = "| Onkosul | Yok | Yok | Yok | Yok | Yok |"
    out = pp.collapse_duplicate_cells(row)
    assert out.count("Yok") == 1
    assert out.count("|") == row.count("|")  # sutun sayisi korunur


def test_iki_ayni_hucre_korunur():
    # Esik 3: yan yana iki ayni deger gercek veri olabilir, dokunulmaz
    row = "| Ders | 3 | 3 | 5 |"
    assert pp.collapse_duplicate_cells(row) == row


def test_ayirici_satir_bozulmaz():
    row = "| --- | --- | --- | --- |"
    assert pp.collapse_duplicate_cells(row) == row
    assert pp.is_separator_row(row)
    assert not pp.is_separator_row("| a | b |")


def test_bos_tablo_atilir():
    md = "Once\n\n|  |  |\n| - | - |\n|  |  |\n\nSonra"
    out = pp.fix_tables(md)
    assert "|" not in out
    assert "Once" in out and "Sonra" in out


def test_eksik_sutunlar_tamamlanir():
    md = "| a | b | c |\n| - | - | - |\n| 1 |"
    out = pp.fix_tables(md)
    son = out.strip().split("\n")[-1]
    assert son.count("|") == 4


def test_fazla_bos_satirlar_sikistirilir():
    assert pp.collapse_blank_lines("a\n\n\n\n\nb") == "a\n\nb\n"


def test_satir_sonu_bosluklari_kirpilir():
    assert pp.collapse_blank_lines("a   \nb\t") == "a\nb\n"


def test_frontmatter_alanlari():
    fm = pp.build_frontmatter(Path("C:/x/Ders Notu.pdf"), 12, "1-5")
    assert 'kaynak: "Ders Notu.pdf"' in fm
    assert "sayfa_sayisi: 12" in fm
    assert 'donusturulen_sayfalar: "1-5"' in fm
    assert fm.startswith("---\n") and fm.rstrip().endswith("---")


def test_clean_tum_adimlari_uygular():
    md = "\n".join(
        [
            "<!-- image -->",
            "",
            r"![Image](x_images\p001_img01.png)",
            "",
            "## Baslik",
            "",
            "",
            "",
            "istatis-",
            "tiksel analiz",
        ]
    )
    out = pp.clean(md, ConversionOptions(), page_count=4)
    assert "<!-- image -->" not in out
    assert "x_images/p001_img01.png" in out
    assert out.count("\n\n\n") == 0
    assert "istatistiksel analiz" in out
    assert "# Baslik" in out


@pytest.mark.parametrize("secenek", ["strip_repeated_headers", "fix_hyphenation", "normalize_headings"])
def test_secenekler_kapatilabilir(secenek):
    opts = ConversionOptions(**{secenek: False})
    md = "## Baslik\n\nistatis-\ntiksel"
    out = pp.clean(md, opts, page_count=4)
    if secenek == "fix_hyphenation":
        assert "istatis-" in out
    if secenek == "normalize_headings":
        assert "## Baslik" in out
