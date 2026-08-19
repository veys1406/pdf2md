"""Token tahmini ve PDF'e kiyasla tasarruf hesabi.

tiktoken Claude'un tokenizer'i degil; buradaki sayilar +/- %10 bandinda bir
GOSTERGEDIR. Arayuzde "~" isaretiyle sunulur.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            import tiktoken

            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as exc:  # ag yoksa veya tiktoken bozuksa
            log.info("tiktoken yuklenemedi, karakter tahminine dusuluyor: %s", exc)
            _encoder = False
    return _encoder


def count_tokens(text: str) -> int:
    """Metnin yaklasik token sayisi."""
    if not text:
        return 0
    enc = _get_encoder()
    if enc:
        try:
            return len(enc.encode(text, disallowed_special=()))
        except Exception:
            pass
    # Yedek: Turkce metinde karakter/token orani ~3.2
    return max(1, round(len(text) / 3.2))


def format_tokens(n: int) -> str:
    """12400 -> '~12.4K'"""
    if n < 1000:
        return f"~{n}"
    if n < 1_000_000:
        return f"~{n / 1000:.1f}K".replace(".0K", "K")
    return f"~{n / 1_000_000:.1f}M"


# Bir PDF sayfasini goruntu olarak bir vision modeline vermenin yaklasik maliyeti.
# A4 sayfa 1568px'e olceklendiginde ~1.1K x 1.5K piksel eder; yaygin modellerde
# bu ~1500-2300 token. Muhafazakar olsun diye alt siniri aliyoruz.
TOKENS_PER_PAGE_IMAGE = 1500


def page_image_tokens(page_count: int) -> int:
    """PDF'i sayfa goruntusu olarak modele vermenin yaklasik token maliyeti."""
    return page_count * TOKENS_PER_PAGE_IMAGE


def savings_percent(baseline_tokens: int, md_tokens: int) -> int | None:
    """Baz alinan maliyete kiyasla yuzde kac token tasarrufu saglandi.

    Negatif deger markdown'in daha pahali oldugunu gosterir; tablo agirlikli
    belgelerde yapiyi korumanin bedeli budur ve oldugu gibi gosterilir.
    """
    if baseline_tokens <= 0:
        return None
    return round((baseline_tokens - md_tokens) / baseline_tokens * 100)
