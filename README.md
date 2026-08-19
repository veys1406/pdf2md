# pdf2md

PDF dosyalarını **LLM'e verilmeye uygun Markdown'a** çeviren Windows uygulaması.
Kurulum gerektirmez, internet bağlantısı istemez, dosyaların bilgisayarından çıkmaz.

> Bir PDF'i sohbete olduğu gibi yapıştırmak sayfa başına ~1500 token yakar. Aynı
> belgenin başlıkları, tabloları ve listeleri korunmuş Markdown hâli çoğu belgede
> bunun yarısından azını tutar — üstelik model metni "okumak" yerine doğrudan
> anlar.

---

## Ne yapar

- **Yapıyı korur:** başlıklar, listeler, tablolar, kod blokları Markdown karşılıklarına çevrilir.
- **Taranmış belgeleri okur:** metin katmanı yoksa OCR (Türkçe + İngilizce) devreye girer.
- **Görselleri ayıklar:** şekiller ayrı bir klasöre kaydedilip Markdown'dan bağlanır; her
  sayfada tekrar eden logo/filigranlar atılır.
- **Gürültüyü temizler:** tekrar eden üst/alt bilgiler silinir, satır sonu tirelemeleri birleştirilir.
- **Token kazancını gösterir:** her dosya için "PDF'i sayfa görüntüsü olarak verseydin ne
  kadar tutardı" karşılaştırması yapılır.
- **Toplu çalışır:** klasör bırak, sıradaki tüm PDF'ler tek tek işlensin.

## Kurulum

1. [Releases](https://github.com/veys1406/pdf2md/releases) sayfasından `pdf2md-kurulum.exe` dosyasını indir.
2. Çalıştır, açılacağı klasörü seç. Kayıt defterine yazmaz, sistem klasörlerine dokunmaz.
3. `pdf2md.exe` ile başlat.

Kaldırmak için klasörü ve `%LOCALAPPDATA%\pdf2md` dizinini silmen yeterli.

### İlk açılış: modeller

Uygulama ilk açıldığında yapay zekâ modellerini indirmeyi teklif eder (~630 MB).
Bu **tek seferliktir**; indikten sonra internet bağlantısı gerekmez.

| Model | Boyut | Ne işe yarar |
|---|---|---|
| Sayfa düzeni | ~172 MB | Başlık, paragraf, tablo, görsel bloklarını tanır |
| Tablo yapısı | ~358 MB | Tabloları satır/sütun olarak çıkarır |
| OCR (tr + en) | ~98 MB | Taranmış, metin katmanı olmayan PDF'leri okur |
| Formül → LaTeX | ~640 MB | *İsteğe bağlı.* Formülleri LaTeX'e çevirir |

Modeller `%LOCALAPPDATA%\pdf2md\models` altına iner. Menüden **Modeller…** ile durumu
görebilir, isteğe bağlı olanı sonradan indirebilirsin.

## Kullanım

PDF'leri (veya bir klasörü) pencereye sürükle, **Dönüştür**'e bas. Sağ panelde çıktının
önizlemesi ve token sayısı görünür.

### Seçenekler

| Seçenek | Varsayılan | Not |
|---|---|---|
| Çıktı klasörü | PDF ile aynı yer | |
| Sayfa aralığı | tümü | `5-20` gibi |
| OCR | Otomatik | Metin katmanı yoksa çalışır. "Her zaman" taranmış gibi işler, çok yavaştır |
| Görseller | Ayrı klasöre kaydet | `belge_images/` klasörü açılır |
| Formülleri LaTeX'e çevir | **Kapalı** | CPU'da çok yavaş; küçük belgelerde bile dakikalar sürebilir |
| YAML başlığı | Açık | Dosya adı, sayfa sayısı, tarih |
| Dosya varsa | Yeni isim ver | `belge-1.md` |

### Neden formül dönüşümü kapalı?

Formül modeli (CodeFormulaV2) grafik kartı olmadan pratik değil: 8 sayfalık bir belge
denemede 50 dakikada bitmedi. İhtiyacın varsa seçeneği aç, ama küçük bir sayfa aralığıyla
başla.

## Gizlilik

Dönüştürme tamamen kendi bilgisayarında yapılır. Belgeler hiçbir sunucuya gönderilmez;
ağ erişimi yalnızca ilk açılıştaki model indirmesi içindir.

## Komut satırı

Aynı motor arayüzsüz de kullanılabilir:

```powershell
pdf2md.exe --help                                  # (geliştirme ortamında: uv run python -m pdf2md.cli)
uv run python -m pdf2md.cli belge.pdf --cikti C:\ciktilar --sayfa 1-10
uv run python -m pdf2md.cli --modelleri-indir      # modelleri indir ve çık
```

| Argüman | Anlamı |
|---|---|
| `--cikti KLASOR` | Çıktı klasörü |
| `--sayfa 5-20` | Sayfa aralığı |
| `--ocr auto\|off\|force` | OCR modu |
| `--gorsel-yok` | Görselleri atla |
| `--formul` | Formülleri LaTeX'e çevir (yavaş) |
| `--frontmatter-yok` | YAML başlığı ekleme |
| `--uzerine-yaz` | Var olan `.md` dosyasının üzerine yaz |
| `--modelleri-indir` | Modelleri indirip çık |

## Geliştirme

Python 3.12 ve [uv](https://docs.astral.sh/uv/) gerekir.

```powershell
uv sync --extra dev
uv run python -m pdf2md          # arayüzü aç
uv run pytest -q                 # testler
uv run pyinstaller packaging/pdf2md.spec --noconfirm
```

Proje düzeni:

```
src/pdf2md/
  core/      dönüşüm motoru, görsel işleme, post-process, model yönetimi
  gui/       ana pencere, kuyruk, önizleme, seçenekler, kurulum sihirbazı
  i18n/      arayüz metinleri
packaging/   PyInstaller spec ve derleme betikleri
tests/       pytest
```

## Neyin üzerine kurulu

[Docling](https://github.com/docling-project/docling) (belge çözümleme),
[PyMuPDF](https://pymupdf.readthedocs.io/) (PDF okuma),
[EasyOCR](https://github.com/JaidedAI/EasyOCR) (Türkçe OCR),
[PySide6](https://doc.qt.io/qtforpython-6/) (arayüz),
[tiktoken](https://github.com/openai/tiktoken) (token sayımı).

## Bilinen sınırlar

- Sadece Windows x64 için paketleniyor.
- Taranmış belgelerde OCR sayfa başına birkaç saniye sürer; 100 sayfalık bir tarama uzun iş.
- Karmaşık, çok sütunlu dergi düzenlerinde okuma sırası bozulabilir.
- Token sayıları tiktoken ile hesaplanır; Claude/Gemini için ±%10 bandında bir göstergedir.
