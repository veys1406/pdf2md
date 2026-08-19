"""Tek renkli (siyah-beyaz) tema. QSS tek bir renk sozlugunden uretilir.

Palette bilerek renksiz: vurgu rengi yok, ayrim yalnizca parlaklikla yapiliyor.
Durum bilgisi (tamamlandi/hata) renk yerine sembol + parlaklik ile veriliyor;
`queue_view` bu yuzden ✓ / ✕ isaretleri kullaniyor.

Butonlar ve birakma alani QSS ile degil `animations.py` icindeki elle cizilen
kontrollerle boyaniyor; QSS'te yalnizca onlarin kapsamadigi durumlar var.
"""

from __future__ import annotations

DARK = {
    "bg": "#0b0b0c",
    "surface": "#121213",
    "surface2": "#1a1a1c",
    "surface3": "#242427",
    "border": "#242427",
    "border_strong": "#3a3a3e",
    "text": "#f4f4f5",
    "muted": "#8b8b91",
    "disabled": "#55555a",
    "focus": "#6f6f76",
    # Vurgu = beyaz. Ana eylem butonu beyaz zemin, siyah yazi.
    "accent": "#f4f4f5",
    "accent_hover": "#ffffff",
    "accent_press": "#c9c9cd",
    "on_accent": "#0b0b0c",
    # Durum tonlari: renk degil, parlaklik kademesi
    "state_strong": "#ffffff",
    "state_mid": "#b6b6bb",
    "state_weak": "#75757b",
    "drop_bg": "#101011",
}

LIGHT = {
    "bg": "#f7f7f8",
    "surface": "#ffffff",
    "surface2": "#f0f0f1",
    "surface3": "#e4e4e6",
    "border": "#e2e2e5",
    "border_strong": "#c2c2c7",
    "text": "#0c0c0d",
    "muted": "#6b6b72",
    "disabled": "#a5a5ab",
    "focus": "#8c8c93",
    "accent": "#0c0c0d",
    "accent_hover": "#232326",
    "accent_press": "#000000",
    "on_accent": "#ffffff",
    "state_strong": "#0c0c0d",
    "state_mid": "#4d4d54",
    "state_weak": "#8f8f96",
    "drop_bg": "#fbfbfc",
}

_QSS = """
* {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {text};
}}

QMainWindow, QDialog {{ background: {bg}; }}

QLabel {{ background: transparent; }}
QLabel#appTitle {{ font-size: 26px; font-weight: 300; letter-spacing: 5px; }}
QLabel#appSubtitle {{ color: {muted}; font-size: 11px; letter-spacing: 2.4px;
                      text-transform: uppercase; }}
QLabel#sectionLabel {{ color: {muted}; font-size: 10px; font-weight: 600;
                       text-transform: uppercase; letter-spacing: 1.4px; }}
QLabel#dropTitle {{ font-size: 15px; font-weight: 500; letter-spacing: 0.3px; }}
QLabel#dropHint {{ color: {muted}; font-size: 12px; }}
QLabel#statTokens {{ font-size: 12px; color: {muted}; letter-spacing: 0.2px; }}

/* -- kartlar -- */
QFrame#card, QFrame#previewCard {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 18px;
}}

/* Kartin icindeki metin gorunumleri kendi cercevesini cizmesin: ic ice iki
   yuvarlak kenarlik kotu duruyor. */
QFrame#previewCard QTextBrowser,
QFrame#previewCard QPlainTextEdit {{
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 4px 2px;
}}
QLabel#hairline {{ background: {border}; max-height: 1px; }}

/* Birakma alani animations.DropZone tarafindan elle ciziliyor. */
QFrame#dropZone {{ background: transparent; border: none; }}

/* -- butonlar --
   Gorunur butonlar SoftButton; asagisi yalnizca duz QPushButton kalan yerler
   (orn. dialog varsayilanlari) icin guvenlik agi. */
QPushButton {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 11px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background: {surface3}; }}
QPushButton:disabled {{ color: {disabled}; }}

/* -- girisler -- */
QLineEdit, QComboBox, QSpinBox {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 11px;
    padding: 8px 12px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {border_strong}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {focus}; }}
QLineEdit::placeholder {{ color: {muted}; }}
QLineEdit:read-only {{ color: {muted}; }}

/* Ok cizimi Fusion stiline birakiliyor: QSS ile ucgen kurmak (image:none +
   kenarlik) Qt'de kare bir blok cizdiriyor. */
QComboBox::drop-down {{ border: none; width: 22px; margin-right: 4px; }}
QComboBox QAbstractItemView {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
    selection-background-color: {surface3};
    selection-color: {text};
    padding: 5px;
    outline: none;
}}

QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {border_strong};
    border-radius: 5px;
    background: {surface};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:hover {{ border-color: {focus}; }}

/* -- tablo -- */
QTableWidget {{
    background: {surface};
    border: none;
    gridline-color: transparent;
    outline: none;
}}
QTableWidget::item {{ padding: 7px 10px; border-bottom: 1px solid {border}; }}
QTableWidget::item:selected {{ background: {surface2}; color: {text}; }}
QHeaderView::section {{
    background: {surface};
    color: {muted};
    border: none;
    border-bottom: 1px solid {border};
    padding: 9px 10px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}

QProgressBar {{
    background: {surface3};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}

/* -- sekmeler -- */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {muted};
    padding: 7px 2px;
    margin-right: 20px;
    border-bottom: 1px solid transparent;
    font-size: 11px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
QTabBar::tab:selected {{ color: {text}; border-bottom: 1px solid {accent}; }}
QTabBar::tab:hover:!selected {{ color: {text}; }}

QTextBrowser, QPlainTextEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 14px;
    selection-background-color: {surface3};
    selection-color: {text};
}}
QPlainTextEdit {{ font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px; }}

/* -- kaydirma cubugu -- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px; }}
QScrollBar::handle:vertical {{ background: {surface3}; border-radius: 5px; min-height: 34px; }}
QScrollBar::handle:vertical:hover {{ background: {border_strong}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 3px; }}
QScrollBar::handle:horizontal {{ background: {surface3}; border-radius: 5px; min-width: 34px; }}
QScrollBar::handle:horizontal:hover {{ background: {border_strong}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Iki panel dip dibe durmasin: ayirici genis birakiliyor. */
QSplitter::handle {{ background: transparent; width: 22px; }}

QMenu {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{ padding: 7px 24px 7px 14px; border-radius: 8px; }}
QMenu::item:selected {{ background: {surface2}; color: {text}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}

QStatusBar {{ background: {bg}; color: {muted}; border-top: 1px solid {border}; }}
QStatusBar::item {{ border: none; }}
QToolTip {{
    background: {surface2};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 9px;
}}
"""


def palette(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def stylesheet(dark: bool) -> str:
    return _QSS.format(**palette(dark))


def preview_css(dark: bool) -> str:
    """Onizleme panelindeki markdown HTML'i icin stil."""
    c = palette(dark)
    return f"""
    body {{ color: {c['text']}; font-family: "Segoe UI", sans-serif; font-size: 13px;
            line-height: 1.65; }}
    h1 {{ font-size: 21px; font-weight: 500; letter-spacing: -0.2px; margin: 16px 0 8px; }}
    h2 {{ font-size: 17px; font-weight: 500; margin: 14px 0 6px; }}
    h3, h4, h5, h6 {{ font-size: 15px; font-weight: 500; margin: 12px 0 5px; }}
    p {{ margin: 7px 0; }}
    a {{ color: {c['text']}; }}
    code {{ background: {c['surface2']}; padding: 1px 5px; border-radius: 5px;
            font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }}
    pre {{ background: {c['surface2']}; padding: 12px; border-radius: 10px; }}
    blockquote {{ border-left: 2px solid {c['border_strong']}; margin-left: 0;
                  padding-left: 14px; color: {c['muted']}; }}
    table {{ border-collapse: collapse; margin: 12px 0; }}
    th, td {{ border: 1px solid {c['border']}; padding: 6px 10px; }}
    th {{ background: {c['surface2']}; font-weight: 500; }}
    img {{ max-width: 100%; }}
    hr {{ border: none; border-top: 1px solid {c['border']}; }}
    p.meta {{ color: {c['muted']}; font-size: 11px; letter-spacing: 0.4px; margin: 0 0 6px; }}
    """
