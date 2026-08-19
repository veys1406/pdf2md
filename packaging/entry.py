"""PyInstaller giris noktasi.

`src/pdf2md/__main__.py` dogrudan verilemez: PyInstaller onu paket baglami
olmadan calistiriyor ve dosyadaki `from .core.paths import ...` satiri
"attempted relative import with no known parent package" ile patliyor.
Buradan normal bir paket import'u yapilinca sorun kalmiyor.

`pdf2md.exe --cli ...` arayuzsuz motoru calistirir. Exe pencere modunda
derlendigi icin konsol yoktur; cikti logs\\cli.log dosyasina yazilir. Paketin
gercekten calistigini (model yukleme, donusum) dogrulamanin tek yolu budur.
"""

import sys

# ensure_env huggingface_hub / torch import edilmeden ONCE calismali; bu yuzden
# uygulamanin geri kalanindan once cagriliyor.
from pdf2md.core.paths import ensure_env, logs_dir

ensure_env()


def _run_cli(argv: list[str]) -> int:
    log_path = logs_dir() / "cli.log"
    with open(log_path, "w", encoding="utf-8") as stream:
        sys.stdout = stream
        sys.stderr = stream
        try:
            from pdf2md.cli import main as cli_main

            return cli_main(argv)
        except Exception:
            import traceback

            traceback.print_exc()
            return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.exit(_run_cli(sys.argv[2:]))

    from pdf2md.__main__ import main

    sys.exit(main())
