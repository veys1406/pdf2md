"""Koyu/acik tema. QSS tek bir renk sozlugunden uretilir."""

from __future__ import annotations

DARK = {
    "bg": "#14161a",
    "surface": "#1b1e25",
    "surface2": "#232733",
    "surface3": "#2b3040",
    "border": "#2e3340",
    "text": "#e7eaf0",
    "muted": "#98a1b2",
    "accent": "#5b93f5",
    "accent_hover": "#6ea1f7",
    "accent_press": "#4a7fdd",
    "on_accent": "#ffffff",
    "success": "#4ade80",
    "danger": "#f87171",
    "warning": "#fbbf24",
    "drop_bg": "#191d26",
}

LIGHT = {
    "bg": "#f4f6f9",
    "surface": "#ffffff",
    "surface2": "#eef1f6",
    "surface3": "#e3e8f0",
    "border": "#d5dbe5",
    "text": "#171a21",
    "muted": "#5e6878",
    "accent": "#2563eb",
    "accent_hover": "#3b76ef",
    "accent_press": "#1d4fd0",
    "on_accent": "#ffffff",
    "success": "#16a34a",
    "danger": "#dc2626",
    "warning": "#d97706",
    "drop_bg": "#f8fafc",
}

_QSS = """
* {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {text};
}}

QMainWindow, QDialog {{ background: {bg}; }}

QLabel {{ background: transparent; }}
QLabel#appTitle {{ font-size: 19px; font-weight: 700; letter-spacing: -0.3px; }}
QLabel#appSubtitle {{ color: {muted}; font-size: 12px; }}
QLabel#sectionLabel {{ color: {muted}; font-size: 11px; font-weight: 600;
                       text-transform: uppercase; letter-spacing: 0.6px; }}
QLabel#dropTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#dropHint {{ color: {muted}; font-size: 12px; }}
QLabel#statTokens {{ font-size: 12px; color: {muted}; }}

/* -- kartlar -- */
QFrame#card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}

QFrame#dropZone {{
    background: {drop_bg};
    border: 2px dashed {border};
    border-radius: 12px;
}}
QFrame#dropZone[hover="true"] {{
    border: 2px dashed {accent};
    background: {surface2};
}}

/* -- butonlar -- */
QPushButton {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {surface3}; }}
QPushButton:pressed {{ background: {border}; }}
QPushButton:disabled {{ color: {muted}; background: {surface}; }}

QPushButton#primary {{
    background: {accent};
    border: 1px solid {accent};
    color: {on_accent};
    font-weight: 600;
    padding: 9px 22px;
}}
QPushButton#primary:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#primary:pressed {{ background: {accent_press}; }}
QPushButton#primary:disabled {{ background: {surface2}; border-color: {border}; color: {muted}; }}

QPushButton#danger {{ color: {danger}; }}
QPushButton#iconButton {{ padding: 6px 10px; font-size: 14px; }}

/* -- girisler -- */
QLineEdit, QComboBox, QSpinBox {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 6px 10px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}
QLineEdit::placeholder {{ color: {muted}; }}
QLineEdit:read-only {{ color: {muted}; }}

/* Ok cizimi Fusion stiline birakiliyor: QSS ile ucgen kurmak (image:none +
   kenarlik) Qt'de kare bir blok cizdiriyor. */
QComboBox::drop-down {{ border: none; width: 20px; margin-right: 4px; }}
QComboBox QAbstractItemView {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 7px;
    selection-background-color: {accent};
    selection-color: {on_accent};
    padding: 4px;
    outline: none;
}}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {border};
    border-radius: 4px;
    background: {surface2};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QCheckBox::indicator:hover {{ border-color: {accent}; }}

/* -- tablo -- */
QTableWidget {{
    background: {surface};
    border: none;
    gridline-color: transparent;
    outline: none;
}}
QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {border}; }}
QTableWidget::item:selected {{ background: {surface3}; color: {text}; }}
QHeaderView::section {{
    background: {surface};
    color: {muted};
    border: none;
    border-bottom: 1px solid {border};
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
}}

QProgressBar {{
    background: {surface3};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}

/* -- sekmeler -- */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {muted};
    padding: 7px 14px;
    margin-right: 2px;
    border-radius: 7px;
    font-weight: 500;
}}
QTabBar::tab:selected {{ background: {surface2}; color: {text}; }}
QTabBar::tab:hover:!selected {{ color: {text}; }}

QTextBrowser, QPlainTextEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QPlainTextEdit {{ font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px; }}

/* -- kaydirma cubugu -- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {surface3}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {muted}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {surface3}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: transparent; width: 8px; }}

QMenu {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {accent}; color: {on_accent}; }}

QStatusBar {{ background: {bg}; color: {muted}; border-top: 1px solid {border}; }}
QToolTip {{
    background: {surface3};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 8px;
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
            line-height: 1.55; }}
    h1 {{ font-size: 20px; margin: 14px 0 8px; }}
    h2 {{ font-size: 17px; margin: 12px 0 6px; }}
    h3, h4, h5, h6 {{ font-size: 15px; margin: 10px 0 5px; }}
    p {{ margin: 6px 0; }}
    a {{ color: {c['accent']}; }}
    code {{ background: {c['surface2']}; padding: 1px 5px; border-radius: 4px;
            font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }}
    pre {{ background: {c['surface2']}; padding: 10px; border-radius: 6px; }}
    blockquote {{ border-left: 3px solid {c['border']}; margin-left: 0;
                  padding-left: 12px; color: {c['muted']}; }}
    table {{ border-collapse: collapse; margin: 10px 0; }}
    th, td {{ border: 1px solid {c['border']}; padding: 5px 9px; }}
    th {{ background: {c['surface2']}; }}
    img {{ max-width: 100%; }}
    hr {{ border: none; border-top: 1px solid {c['border']}; }}
    p.meta {{ color: {c['muted']}; font-size: 11px; margin: 0 0 4px; }}
    """
