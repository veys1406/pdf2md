"""Arayuzde gecen tum metinler.

Tek dosyada toplu: ileride EN eklenecekse burasi cogaltilir, widget kodlarina
dokunulmaz.
"""

APP_TITLE = "pdf2md"
APP_SUBTITLE = "PDF → Markdown"

# -- birakma alani --------------------------------------------------------
DROP_TITLE = "PDF dosyalarını buraya sürükleyin"
DROP_HINT = "veya aşağıdaki butonlarla seçin · klasör de bırakabilirsiniz"
BTN_PICK_FILES = "PDF Seç"
BTN_PICK_FOLDER = "Klasör Seç"
BTN_CLEAR = "Listeyi Temizle"

# -- kuyruk ---------------------------------------------------------------
COL_FILE = "Dosya"
COL_PAGES = "Sayfa"
COL_STATUS = "Durum"
COL_PROGRESS = "İlerleme"
COL_TIME = "Süre"
COL_TOKENS = "Token"

STATUS_WAITING = "Bekliyor"
STATUS_RUNNING = "Dönüştürülüyor"
STATUS_DONE = "Tamamlandı"
STATUS_ERROR = "Hata"
STATUS_CANCELLED = "İptal edildi"
STATUS_SKIPPED = "Atlandı"

CTX_OPEN_FOLDER = "Klasörde göster"
CTX_OPEN_MD = "Markdown'ı aç"
CTX_RETRY = "Yeniden dene"
CTX_REMOVE = "Listeden çıkar"

# -- secenekler -----------------------------------------------------------
OPT_OUTPUT = "Çıktı klasörü"
OPT_OUTPUT_SAME = "PDF ile aynı klasör"
OPT_BROWSE = "Gözat…"
OPT_PAGES = "Sayfa aralığı"
OPT_PAGES_PLACEHOLDER = "tümü · örn. 5-20"
OPT_OCR = "OCR"
OPT_OCR_AUTO = "Otomatik (taranmışsa)"
OPT_OCR_OFF = "Kapalı"
OPT_OCR_FORCE = "Her zaman"
OPT_IMAGES = "Görseller"
OPT_IMAGES_SAVE = "Ayrı klasöre kaydet"
OPT_IMAGES_SKIP = "Atla"
OPT_FORMULA = "Formülleri LaTeX'e çevir (çok yavaş)"
OPT_FRONTMATTER = "YAML başlığı ekle"
OPT_EXISTING = "Dosya varsa"
OPT_EXISTING_RENAME = "Yeni isim ver"
OPT_EXISTING_OVERWRITE = "Üzerine yaz"
OPT_EXISTING_SKIP = "Atla"

BTN_CONVERT = "Dönüştür"
BTN_CANCEL = "İptal"

# -- onizleme -------------------------------------------------------------
TAB_PREVIEW = "Önizleme"
TAB_RAW = "Ham Markdown"
BTN_COPY = "Kopyala"
BTN_COPIED = "Kopyalandı ✓"
BTN_SHOW_IN_FOLDER = "Klasörde Göster"
PREVIEW_EMPTY = "Dönüştürülen bir dosya seçin"

# -- durum cubugu ---------------------------------------------------------
READY = "Hazır"
ENGINE_LOADING = "Motor hazırlanıyor…"
MODELS_DOWNLOADING = "Modeller indiriliyor…"

def queue_summary(done: int, total: int, tokens: str) -> str:
    return f"{done}/{total} dosya tamamlandı · toplam {tokens} token"


def savings_label(md: str, vision: str, percent: int | None) -> str:
    if percent is None:
        return f"{md} token"
    return f"{md} token · PDF sayfa görüntüsü olarak {vision} (%{percent} tasarruf)"


# -- hatalar / uyarilar ---------------------------------------------------
ERR_TITLE = "Dönüştürülemedi"
ERR_NO_MODELS = (
    "Modeller indirilemedi. İlk kullanımda internet bağlantısı gerekiyor.\n"
    "Bağlantını kontrol edip tekrar dene."
)
WARN_OCR_SLOW = "Taranmış belge: OCR çalıştırıldı, bu dosya daha yavaş işlendi."
CONFIRM_CANCEL = "Devam eden dönüştürme iptal edilsin mi?"
CONFIRM_CANCEL_TITLE = "İptal"

# -- menu / ayarlar -------------------------------------------------------
MENU_THEME_DARK = "Koyu tema"
MENU_THEME_LIGHT = "Açık tema"
MENU_MODELS = "Modeller…"
MENU_ABOUT = "Hakkında"
ABOUT_TEXT = (
    "pdf2md — PDF dosyalarını LLM dostu Markdown'a çevirir.\n\n"
    "Tamamen bilgisayarında çalışır, hiçbir veri dışarı gönderilmez.\n"
    "Docling + PyMuPDF + EasyOCR ile geliştirildi."
)

# -- model sihirbazi ------------------------------------------------------
MODELS_TITLE = "Modeller"
MODELS_FIRST_RUN_TITLE = "İlk kurulum"
MODELS_INTRO = (
    "pdf2md dönüştürmeyi tamamen kendi bilgisayarında yapar. Bunun için yapay "
    "zekâ modellerinin bir kez indirilmesi gerekiyor. İndirme bittikten sonra "
    "internet bağlantısına ihtiyaç kalmaz."
)
MODELS_INTRO_DONE = (
    "Zorunlu modeller kurulu, dönüştürmeye hazırsın. İstersen isteğe bağlı "
    "modelleri de indirebilirsin."
)
MODELS_INSTALLED = "Kurulu"
MODELS_REQUIRED = "Bu model olmadan dönüştürme yapılamaz"
MODELS_OPTIONAL = "İsteğe bağlı"
MODELS_ALL_READY = "İndirilecek yeni model yok"
MODELS_STARTING = "İndirme başlatılıyor…"
MODELS_DONE = "Modeller hazır ✓"
MODELS_CANCELLED = "İndirme iptal edildi. Yarım inen dosyalar korundu, sonra kaldığı yerden devam eder."
MODELS_CANCEL_HINT = "İptal ediliyor… Sürmekte olan model bittiğinde duracak."

BTN_DOWNLOAD = "İndir"
BTN_LATER = "Şimdi değil"
BTN_CLOSE = "Kapat"


def models_total(count: int, size: str) -> str:
    return f"{count} model · toplam {size}"


def models_location(path: str) -> str:
    return f"İndirme konumu: {path}"


def models_downloading(title: str) -> str:
    return f"İndiriliyor: {title}…"


def models_error(message: str) -> str:
    return f"İndirme başarısız — {message}\nBağlantını kontrol edip tekrar dene."


MODELS_MISSING_TITLE = "Modeller eksik"
MODELS_MISSING_ASK = (
    "Dönüştürme için gereken modeller henüz inmedi. Şimdi indirilsin mi?"
)
