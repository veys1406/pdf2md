"""Animasyon yardimcilari ve elle cizilen kontroller.

Qt stil sayfalari `transition` desteklemez: QSS ile yazilan bir hover kurali
aninda devreye girer, yumusak gecis olmaz. Bu yuzden hareketli parcalar
(butonlar, birakma alani, ilerleme cubugu) burada QPropertyAnimation ve elle
cizim ile yapiliyor.

Sureler kasitli olarak kisa: 120-260 ms bandi "yumusak" hissettiriyor, uzayinca
arayuz agir gorunuyor.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

FAST = 140
NORMAL = 200
SLOW = 280


def mix(a: str | QColor, b: str | QColor, t: float) -> QColor:
    """Iki rengi t oraninda karistir (t=0 -> a, t=1 -> b)."""
    ca, cb = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
        round(ca.alpha() + (cb.alpha() - ca.alpha()) * t),
    )


def fade_in(widget: QWidget, duration: int = NORMAL, start: float = 0.0) -> QPropertyAnimation:
    """Widget'i saydamdan tam gorunure getir.

    Animasyon nesnesi widget'a bagli tutulur; yerel degiskende birakilirsa
    Python onu hemen topluyor ve animasyon hic calismiyor.
    """
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    # Efekt kalirsa alt widget'larin cizimi yavasliyor; bitince kaldiriliyor.
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_anim = anim  # referansi canli tut
    anim.start()
    return anim


class AnimatedProgressBar(QProgressBar):
    """Degeri sicratmadan, yumusak gecisle guncelleyen ilerleme cubugu."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTextVisible(False)
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(NORMAL)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def animate_to(self, value: int) -> None:
        self._anim.stop()
        # Geriye dogru (sifirlama) animasyonsuz: iptal/yeniden deneme aninda olsun.
        if value < self.value():
            self.setValue(value)
            return
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(value)
        self._anim.start()


class SoftButton(QPushButton):
    """Hover ve basma gecisleri animasyonlu, elle cizilen buton.

    variant:
      primary -> dolu zemin (ana eylem)
      ghost   -> ince kenarlikli (varsayilan)
      quiet   -> kenarliksiz, yalnizca hover zemini (ikon/menu butonlari)
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "ghost",
        parent=None,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
    ) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self._align = align
        self._hover = 0.0
        self._press = 0.0
        self._colors: dict[str, str] = {}
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        # Tiklayinca odak halkasi takili kalmasin; Tab ile gezinen kullanici
        # yine de nerede oldugunu gorsun.
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(FAST)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_value)

        self._press_anim = QVariantAnimation(self)
        self._press_anim.setDuration(90)
        self._press_anim.valueChanged.connect(self._on_press_value)

        self.setMinimumHeight(34 if variant != "primary" else 38)

    # -- tema ----------------------------------------------------------

    def set_colors(self, colors: dict[str, str]) -> None:
        self._colors = colors
        self.update()

    # -- animasyon degerleri -------------------------------------------

    def _on_hover_value(self, value) -> None:
        self._hover = float(value)
        self.update()

    def _on_press_value(self, value) -> None:
        self._press = float(value)
        self.update()

    def _animate(self, anim: QVariantAnimation, current: float, target: float) -> None:
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    def enterEvent(self, event) -> None:
        if self.isEnabled():
            self._animate(self._hover_anim, self._hover, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate(self._hover_anim, self._hover, 0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._animate(self._press_anim, self._press, 1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._animate(self._press_anim, self._press, 0.0)
        super().mouseReleaseEvent(event)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (Qt adlandirmasi)
        if not enabled:
            self._hover_anim.stop()
            self._hover = 0.0
        super().setEnabled(enabled)

    # -- cizim ---------------------------------------------------------

    def _palette_colors(self) -> tuple[QColor, QColor, QColor | None]:
        """(zemin, yazi, kenarlik) uclusunu variant ve animasyon degerine gore uret."""
        c = self._colors
        bg = QColor(c.get("surface2", "#1a1a1a"))
        text = QColor(c.get("text", "#f2f2f2"))
        border: QColor | None = QColor(c.get("border", "#2a2a2a"))

        if not self.isEnabled():
            return QColor(c.get("surface", "#121212")), QColor(c.get("disabled", "#5a5a5a")), border

        if self._variant == "primary":
            base = QColor(c.get("accent", "#f2f2f2"))
            bg = mix(base, c.get("accent_hover", "#ffffff"), self._hover)
            bg = mix(bg, c.get("accent_press", "#cfcfcf"), self._press)
            return bg, QColor(c.get("on_accent", "#0a0a0a")), None

        if self._variant == "quiet":
            bg = mix(QColor(0, 0, 0, 0), QColor(c.get("surface2", "#1a1a1a")), self._hover)
            bg = mix(bg, QColor(c.get("surface3", "#242424")), self._press)
            return bg, text, None

        # ghost
        bg = mix(c.get("surface", "#121212"), c.get("surface2", "#1a1a1a"), self._hover)
        bg = mix(bg, c.get("surface3", "#242424"), self._press)
        border = mix(c.get("border", "#2a2a2a"), c.get("border_strong", "#3d3d3d"), self._hover)
        return bg, text, border

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg, fg, border = self._palette_colors()
        radius = 9.0
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, bg)

        if border is not None:
            painter.setPen(QPen(border, 1.0))
            painter.drawPath(path)

        if self.hasFocus():
            focus = QColor(self._colors.get("focus", "#6b6b6b"))
            painter.setPen(QPen(focus, 1.0))
            painter.drawPath(path)

        painter.setPen(fg)
        font = self.font()
        # PySide6'da setWeight int kabul etmiyor, QFont.Weight istiyor; int
        # verilince paintEvent TypeError ile kesiliyor ve buton BOS ciziliyor.
        font.setWeight(
            QFont.Weight.DemiBold if self._variant == "primary" else QFont.Weight.Medium
        )
        painter.setFont(font)
        rect_text = self.rect().adjusted(12, 0, -12, 0)
        painter.drawText(rect_text, self._align | Qt.AlignmentFlag.AlignVCenter, self.text())
        painter.end()

    def sizeHint(self):  # noqa: N802
        hint = super().sizeHint()
        extra = 26 if self._variant == "primary" else 14
        hint.setWidth(hint.width() + extra)
        hint.setHeight(max(hint.height(), self.minimumHeight()))
        return hint


class FadeStack:
    """Bir widget'in icerigi degistiginde kisa bir fade uygular."""

    def __init__(self, widget: QWidget, duration: int = NORMAL) -> None:
        self._widget = widget
        self._duration = duration

    def refresh(self) -> None:
        fade_in(self._widget, self._duration, start=0.25)


class Fader:
    """Deger degisince yumusak gecis yapan `opacity` ozelligi tasiyicisi.

    QLabel gibi metni degisen widget'larda metin degistirilmeden once soluklastirip
    sonra geri getirmek icin kullanilir.
    """

    def __init__(self, widget: QWidget) -> None:
        self._widget = widget
        self._effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)
        self._anim = QPropertyAnimation(self._effect, b"opacity", widget)
        self._anim.setDuration(FAST)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def flash(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(0.15)
        self._anim.setEndValue(1.0)
        self._anim.start()


class OpacityAnimator(QWidget):
    """Pencere genelinde crossfade icin yardimci (tema degisimi vb.)."""

    def __init__(self, target: QWidget) -> None:
        super().__init__(target)
        self._target = target
        self._value = 1.0
        self.hide()

    def get_value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        self._value = value
        self._target.setWindowOpacity(value)

    value = Property(float, get_value, set_value)


def fade_window_in(window: QWidget, duration: int = SLOW) -> None:
    """Pencereyi saydamdan acilir gibi getir (acilista bir kez)."""
    window.setWindowOpacity(0.0)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    window._window_fade = anim
    anim.start()


def pulse_opacity(window: QWidget, duration: int = NORMAL) -> None:
    """Kisa bir soluklas-geri gel: tema degisiminde gecisi yumusatir."""
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setKeyValueAt(0.0, 1.0)
    anim.setKeyValueAt(0.45, 0.55)
    anim.setKeyValueAt(1.0, 1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
    window._theme_fade = anim
    anim.start()


class CollapsibleSection(QWidget):
    """Basligina tiklanınca icerigi animasyonla acilip kapanan bolum.

    Kucuk ekranlarda secenek seridi dikey alanin buyuk kismini yiyordu; burada
    varsayilan olarak kapali durup istenince aciliyor.
    """

    toggled_open = Signal(bool)

    def __init__(self, title: str, content: QWidget, expanded: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._content = content
        self._expanded = expanded
        self._title = title

        self.header = SoftButton(self._label(), "quiet", align=Qt.AlignmentFlag.AlignLeft)
        self.header.setMinimumHeight(30)
        self.header.clicked.connect(self.toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.header)
        layout.addWidget(content)

        self._anim = QPropertyAnimation(content, b"maximumHeight", self)
        self._anim.setDuration(NORMAL)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        content.setMaximumHeight(16777215 if expanded else 0)
        content.setVisible(True)

    def _label(self) -> str:
        return f"{self._title}   {'▾' if self._expanded else '▸'}"

    def set_colors(self, colors: dict[str, str]) -> None:
        self.header.set_colors(colors)

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        self._expanded = expanded
        self.header.setText(self._label())

        target = self._content.sizeHint().height() if expanded else 0
        if not animate:
            self._content.setMaximumHeight(target if not expanded else 16777215)
            return

        self._anim.stop()
        self._anim.setStartValue(self._content.maximumHeight())
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled_open.emit(expanded)
