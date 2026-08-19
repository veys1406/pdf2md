"""pdf2md logosunu ve uygulama ikonlarini uretir.

Logo tek renkli: siyah yuvarlak kare zemin uzerine beyaz bir belge ve asagi ok
(PDF -> Markdown donusumu). Kendi zemini oldugu icin hem koyu hem acik arayuzde,
gorev cubugunda ve masaustunde ayni sekilde okunuyor.

Cerceveler "ciz ve icini oy" yontemiyle uretiliyor: kapali bir yolu `line` ile
cizmek baslangic kosesinde tirnak birakiyordu.

Calistirma:
    uv run python packaging/make_icon.py

Uretilenler (assets/):
    icon.ico          exe ve pencere ikonu (16..256 px)
    logo.png          256 px, arayuzde ve README'de
    logo-large.png    512 px
    logo-mono-light.png  512 px, zeminsiz beyaz (koyu arayuz icin)
    logo-mono-dark.png   512 px, zeminsiz siyah (acik arayuz icin)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SIZE = 1024
BLACK = (11, 11, 12, 255)
WHITE = (244, 244, 245, 255)
TRANSPARENT = (0, 0, 0, 0)

STROKE = 38  # cerceve kalinligi (1024 px kareye gore)


def _page_outline(inset: int = 0) -> list[tuple[int, int]]:
    """Sag ust kosesi kesik sayfa yolu; `inset` kadar iceri cekilmis."""
    left, top, right, bottom = 300, 156, 724, 592
    fold = 132
    left, top = left + inset, top + inset
    right, bottom = right - inset, bottom - inset
    fold = max(0, fold - inset)
    return [
        (left, top),
        (right - fold, top),
        (right, top + fold),
        (right, bottom),
        (left, bottom),
    ]


def _draw_mark(image: Image.Image, color: tuple[int, int, int, int]) -> None:
    """Belge + asagi ok isaretini cizer."""
    draw = ImageDraw.Draw(image)

    # Sayfa cercevesi: dolu sekli ciz, icini saydam birak
    draw.polygon(_page_outline(), fill=color)
    hole = Image.new("RGBA", image.size, TRANSPARENT)
    ImageDraw.Draw(hole).polygon(_page_outline(inset=STROKE), fill=(0, 0, 0, 255))
    image.paste(TRANSPARENT, (0, 0), hole)

    # Kivrik kosenin katlanma cizgisi
    draw = ImageDraw.Draw(image)
    right, top, fold = 724, 156, 132
    draw.line(
        [(right - fold, top + STROKE // 2), (right - fold, top + fold), (right - STROKE // 2, top + fold)],
        fill=color,
        width=STROKE,
        joint="curve",
    )

    # Sayfadaki metin satirlari (kisalan iki satir: markdown'in ritmi)
    draw.line([(396, 316), (628, 316)], fill=color, width=STROKE - 6)
    draw.line([(396, 412), (560, 412)], fill=color, width=STROKE - 6)

    # Donusum oku: ince gövde + chevron uc (dolgun ucgenden daha zarif)
    x = 512
    draw.line([(x, 664), (x, 856)], fill=color, width=STROKE + 2)
    draw.line(
        [(x - 104, 762), (x, 866), (x + 104, 762)],
        fill=color,
        width=STROKE + 2,
        joint="curve",
    )


def build_logo(with_background: bool = True, color=WHITE) -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), TRANSPARENT)

    if with_background:
        # Isaret once ayri bir katmana cizilip zemine yapistiriliyor: cerceve
        # oyugunun zemini delmesi gerekiyor.
        mark = Image.new("RGBA", (SIZE, SIZE), TRANSPARENT)
        _draw_mark(mark, color)
        ImageDraw.Draw(image).rounded_rectangle(
            [(0, 0), (SIZE - 1, SIZE - 1)], radius=232, fill=BLACK
        )
        image.alpha_composite(mark)
    else:
        _draw_mark(image, color)
    return image


def main() -> None:
    ASSETS.mkdir(exist_ok=True)

    logo = build_logo(with_background=True)
    logo.resize((512, 512), Image.LANCZOS).save(ASSETS / "logo-large.png")
    logo.resize((256, 256), Image.LANCZOS).save(ASSETS / "logo.png")

    # Zeminsiz varyantlar: bos onizlemede filigran gibi kullaniliyor, bu yuzden
    # koyu ve acik arayuz icin ayri ayri uretiliyor.
    build_logo(with_background=False, color=WHITE).resize((512, 512), Image.LANCZOS).save(
        ASSETS / "logo-mono-light.png"
    )
    build_logo(with_background=False, color=BLACK).resize((512, 512), Image.LANCZOS).save(
        ASSETS / "logo-mono-dark.png"
    )

    # ICO: Windows kucuk boyutlarda kendi olceklemesini yapmak yerine gomulu
    # olani seciyor; hepsini tek dosyaya koyuyoruz.
    logo.save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    for name in (
        "icon.ico",
        "logo.png",
        "logo-large.png",
        "logo-mono-light.png",
        "logo-mono-dark.png",
    ):
        path = ASSETS / name
        print(f"  {name:16s} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
