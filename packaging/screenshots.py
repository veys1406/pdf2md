"""README icin ekran goruntulerini uretir.

Gercek bir pencere acilir (offscreen DEGIL): offscreen platformda fontlar
yuklenmedigi icin tum yazilar bos kutu cikiyor. Goruntuler `docs/images/`
altina yazilir.

Gosterilen veriler gercek: samples/ altindaki PDF'ler gercekten cevrilip
kuyruga ve onizlemeye konuyor.

Calistirma:
    uv run python packaging/screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from pdf2md.core.paths import ensure_env

ensure_env()

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pdf2md.core.options import ConversionOptions  # noqa: E402
from pdf2md.gui import queue_view  # noqa: E402
from pdf2md.gui.main_window import MainWindow  # noqa: E402
from pdf2md.gui.queue_view import JobState  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
SHOTS = [
    "01-ana-ekran",
    "02-dosyalar-eklendi",
    "03-donusturuluyor",
    "04-tamamlandi",
    "05-secenekler",
    "06-modeller",
    "07-acik-tema",
]


def save(widget, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    widget.grab().save(str(path))
    print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window._models_checked = True  # sihirbaz kendiliginden acilmasin
    window.resize(1180, 770)

    # Goruntuler kullanicinin kayitli ayarlarindan degil, varsayilanlardan
    # uretilmeli: kisisel cikti yolu ve acik kalmis paneller kilavuzda kafa
    # karistiriyor.
    window._opts = ConversionOptions()
    window.options_panel.set_options(window._opts)
    window.options_section.set_expanded(False, animate=False)
    window._dark = True
    window._apply_theme()
    window.show()
    app.processEvents()

    samples = sorted((ROOT / "samples").glob("*.pdf"))
    if not samples:
        print("samples/ altinda PDF yok; ekran goruntuleri gercekci olmaz.")
        return 1

    def bekle(ms: int) -> None:
        son = QTimer()
        son.setSingleShot(True)
        son.start(ms)
        while son.isActive():
            app.processEvents()

    # 1) bos ana ekran
    bekle(600)
    save(window, SHOTS[0])

    # 2) kuyruga dosyalar eklendi
    gosterilecek = samples[:5]
    window._add_files(gosterilecek)
    bekle(500)
    save(window, SHOTS[1])

    # 3) donusum surerken (ilk dosya calisiyor)
    window.queue.set_running(0, 46, "Sayfalar analiz ediliyor")
    window._set_running(True)
    bekle(400)
    save(window, SHOTS[2])
    window._set_running(False)

    # Calisiyor gorunumu yalnizca 3. goruntu icindi; kuyruk temiz baslasin.
    window.queue.jobs[0].state = JobState.WAITING
    window.queue.set_running(0, 0, "")
    window.queue.jobs[0].state = JobState.WAITING
    window.queue._set_text(0, 2, queue_view.format_status(JobState.WAITING))
    window.queue._set_progress(0, 0)
    window.queue._paint_status(0)

    # 4) gercek bir donusum sonucu
    print("  ornek dosya cevriliyor (ekran goruntusu gercek cikti gostersin diye)...")
    # Kuyrukta gorunen dosyalardan biri cevrilmeli; kisa olani sec.
    kaynak = min(gosterilecek, key=lambda p: p.stat().st_size)
    hedef_dizin = ROOT / "docs" / "_ornek-cikti"
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    opts = ConversionOptions(output_dir=hedef_dizin, page_range=(1, 2))
    sonuc = window._engine.convert(kaynak, opts)

    satir = next(i for i, j in enumerate(window.queue.jobs) if j.path == kaynak)
    window.queue.set_done(satir, sonuc)
    window.queue.selectRow(satir)
    window._on_row_selected(satir)
    window._update_summary()
    bekle(700)
    save(window, SHOTS[3])

    # 5) secenekler acik
    window.options_section.set_expanded(True)
    bekle(600)
    save(window, SHOTS[4])
    window.options_section.set_expanded(False)
    bekle(400)

    # 6) model sihirbazi (kurulu olmayan modeller varmis gibi)
    from pdf2md.core import models
    from pdf2md.gui import setup_wizard

    gercek = models.is_installed
    models.is_installed = lambda spec: False
    try:
        dialog = setup_wizard.ModelsDialog(window, first_run=True)
        dialog.show()
        bekle(700)
        save(dialog, SHOTS[5])
        dialog.close()
    finally:
        models.is_installed = gercek

    # 7) acik tema
    window._dark = False
    window._apply_theme()
    bekle(600)
    save(window, SHOTS[6])

    # Kullanicinin kayitli tercihlerini bozma
    from pdf2md.core import settings as app_settings

    app_settings.save_options_expanded(False)

    print("bitti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
