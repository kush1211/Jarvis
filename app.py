"""Jarvis window, "Quiet Glass" design. Run: .venv\\Scripts\\python app.py"""
import ctypes
import json
import math
import sys

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QEvent, QElapsedTimer, QPointF, QPropertyAnimation, QRectF, Qt,
                            QThread, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QFont, QPainter, QPainterPath, QPalette, QPen, QRadialGradient,
                           QTextBlockFormat, QTextCursor, QTextDocument)
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

import config
import jarvis
import tools

BG, TEXT, MUTED, ACCENT, DEEP = "#0f0f14", "#ececf3", "#9a9aac", "#a9a4ff", "#3b3a8f"
WARN = "#ffb48a"  # error text (board B5)
LIGHT = "#c4c0ff"  # the accent, brightened on hover
COLUMN = 640  # width of the chat column and the input pill

STYLE = f"""
QWidget#root {{ background: {BG}; }}
QLabel {{ color: {TEXT}; font-size: 15px; }}
QLabel#muted {{ color: {MUTED}; font-size: 13px; font-weight: 500; }}
QLabel#muted[failed="true"] {{ color: {WARN}; }}
QFrame#error {{ background: #261a16; border: 1px solid #5a3426; border-radius: 14px; }}
QLabel#errorTitle {{ color: {WARN}; font-weight: 600; }}
QLabel#errorBody {{ color: #e7d6cf; font-size: 14px; }}
QPushButton#retry {{ background: {ACCENT}; color: #14142a; border: 0; border-radius: 22px; padding: 0 20px;
                     font-size: 14px; font-weight: 600; min-height: 44px; }}
QLabel#hint {{ color: {MUTED}; font-size: 14px; }}
QLabel#heading {{ font-size: 28px; font-weight: 600; }}
QFrame#steps {{ background: #16161e; border: 1px solid #25252f; border-radius: 14px; }}
QLabel#step {{ font-size: 14px; }}
QLabel#step[failed="true"] {{ color: {MUTED}; }}
QLabel#user {{ background: #23232e; padding: 12px 18px; border-radius: 20px; border-bottom-right-radius: 6px; }}
QFrame#pill {{ background: #1a1a23; border: 1px solid #2c2c3a; border-radius: 30px; }}
QLineEdit {{ background: transparent; border: 0; color: {TEXT}; font-size: 15px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: #2c2c3a; border-radius: 4px; min-height: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
"""


class Worker(QThread):
    """Runs one turn off the UI thread, so the window doesn't freeze while the model thinks."""
    done = Signal(str, bool)  # text, ok

    def __init__(self, messages: list[dict], text: str):
        super().__init__()
        self.messages, self.text = messages, text

    def run(self):
        start = len(self.messages)
        try:
            self.done.emit(*jarvis.ask(self.messages, self.text))
        except Exception as e:  # anything ask() doesn't expect; without this the input stays locked
            del self.messages[start:]  # keep history to complete turns, so Try again starts clean
            self.done.emit(f"Unexpected error: {e}", False)


def animate(owner: QWidget, start: float, end: float, ms: int, on_value,
            curve=QEasingCurve.OutCubic) -> QVariantAnimation:
    """Run on_value(v) every frame as v goes from start to end. owner keeps it alive; it deletes itself after."""
    anim = QVariantAnimation(owner, startValue=float(start), endValue=float(end), duration=ms, easingCurve=curve)
    anim.valueChanged.connect(on_value)
    anim.start(QAbstractAnimation.DeleteWhenStopped)
    return anim


def tween(owner: QWidget, ms: int, on_value) -> QVariantAnimation:
    """A reusable animation (it is never deleted); point it at a new end with retarget()."""
    anim = QVariantAnimation(owner, duration=ms, easingCurve=QEasingCurve.OutCubic)
    anim.valueChanged.connect(on_value)
    return anim


def retarget(anim: QVariantAnimation, now: float, end: float):
    """Restart anim from where things are now (so a quick hover-in-and-out doesn't jump)."""
    anim.stop()
    anim.setStartValue(float(now))
    anim.setEndValue(float(end))
    anim.start()


def mix(a: str, b: str, t: float) -> QColor:
    """Colour between a (t=0) and b (t=1)."""
    ca, cb = QColor(a), QColor(b)
    return QColor.fromRgbF(*(x + (y - x) * t for x, y in zip(ca.getRgbF(), cb.getRgbF())))


CLOCK = QElapsedTimer()  # shared by every orb, so they all breathe in step (no jump when one hands over)
CLOCK.start()


class Orb(QWidget):
    """The glowing ball: a radial gradient lit from the top left. Orbs with a glow are alive: the glow
    breathes, rings ripple out while working, and the colour fades to grey on errors (board B5)."""
    BREATH, RIPPLE = 3.5, 2.4  # seconds per loop

    def __init__(self, size: int, glow: int = 0):
        super().__init__()
        self.size, self.glow = size, glow
        self.working = False  # True sends rings rippling outwards
        self.grey = 0.0  # 0 = purple, 1 = grey; set_grey() fades between them
        self.fade = None
        self.ghost = False  # True keeps its place in the layout but draws nothing (while a copy flies in)
        self.setFixedSize(size + 2 * glow, size + 2 * glow)
        if glow:  # small avatars stay still
            self.timer = QTimer(self, interval=33)  # ~30 fps is smooth enough for slow motion
            self.timer.timeout.connect(self.tick)
            self.timer.start()

    def tick(self):
        if self.isVisible() and not self.window().isMinimized():  # no repaints nobody can see
            self.update()

    def resize_to(self, size: float, glow: float):
        self.size, self.glow = size, glow
        self.setFixedSize(round(size + 2 * glow), round(size + 2 * glow))
        self.update()

    def set_grey(self, grey: bool):
        if self.fade:
            self.fade.stop()
        self.fade = animate(self, self.grey, 1.0 if grey else 0.0, 400, self.set_grey_value)
        self.fade.finished.connect(lambda: setattr(self, "fade", None))  # it deletes itself when done

    def set_grey_value(self, value: float):
        self.grey = value
        self.update()

    def paintEvent(self, event):
        if self.ghost:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        center = QPointF(self.width() / 2, self.height() / 2)
        r = self.size / 2
        t = CLOCK.elapsed() / 1000
        if self.glow:
            breath = 0.5 - 0.5 * math.cos(2 * math.pi * t / self.BREATH)  # 0..1..0, smooth
            reach = r + self.glow * (0.85 + 0.15 * breath)
            halo = QRadialGradient(center, reach)
            edge = mix(ACCENT, "#5d5d70", self.grey)
            edge.setAlphaF((0.4 - 0.15 * self.grey) * (0.75 + 0.25 * breath))
            halo.setColorAt(r / reach * 0.8, edge)
            halo.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(halo)
            p.drawEllipse(center, reach, reach)
        if self.working and self.glow:
            for offset in (0.0, 0.5):  # two rings, half a loop apart
                k = (t / self.RIPPLE + offset) % 1  # 0 = at the ball, 1 = fully out
                ring = QColor(ACCENT)
                ring.setAlphaF(0.16 * (1 - k))
                p.setBrush(ring)
                p.drawEllipse(center, r + k * self.glow * 0.95, r + k * self.glow * 0.95)
        light = QPointF(center.x() - 0.3 * self.size, center.y() - 0.4 * self.size)
        body = QRadialGradient(light, self.size * 0.95)
        body.setColorAt(0, mix("#ffffff", "#c9c9d8", self.grey))
        body.setColorAt(0.38, mix(ACCENT, "#5d5d70", self.grey))
        body.setColorAt(1, mix(DEEP, "#2a2a38", self.grey))
        p.setBrush(body)
        p.drawEllipse(center, r, r)


class SendButton(QPushButton):
    """Round accent button with an up arrow, painted so it needs no icon files.
    Brightens on hover, presses in when clicked, and its arrow nudges up when a message goes."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Send")
        self.hover = self.press = self.lift = 0.0  # each 0..1
        self.hover_anim = tween(self, 150, lambda v: self.set_value("hover", v))
        self.press_anim = tween(self, 100, lambda v: self.set_value("press", v))

    def set_value(self, name: str, value: float):
        setattr(self, name, value)
        self.update()

    def enterEvent(self, event):
        retarget(self.hover_anim, self.hover, 1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        retarget(self.hover_anim, self.hover, 0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        retarget(self.press_anim, self.press, 1)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        retarget(self.press_anim, self.press, 0)
        super().mouseReleaseEvent(event)

    def changeEvent(self, event):
        if not self.isEnabled():  # disabled widgets get no leave event, so drop the hover here
            self.hover_anim.stop()
            self.hover = self.press = 0.0
        super().changeEvent(event)

    def nudge(self):
        """Arrow goes up 4 px and back (a sine bump)."""
        animate(self, 0, 1, 300, lambda v: self.set_value("lift", math.sin(math.pi * v)), QEasingCurve.Linear)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.translate(22, 22)
        p.scale(1 - 0.06 * self.press, 1 - 0.06 * self.press)  # pressed in to 94 %
        p.translate(-22, -22)
        p.setBrush(mix(ACCENT, LIGHT, self.hover) if self.isEnabled() else QColor("#2c2c3a"))
        p.drawEllipse(QRectF(0.5, 0.5, 43, 43))  # half a pixel in, so the edge isn't clipped
        p.translate(0, -4 * self.lift)
        arrow = QPainterPath()
        arrow.moveTo(22, 30); arrow.lineTo(22, 14)
        arrow.moveTo(16, 19); arrow.lineTo(22, 13); arrow.lineTo(28, 19)
        p.setPen(QPen(QColor("#14142a"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(arrow)


class Check(QWidget):
    """16 px circle with a tick (done) or a plain grey circle (the tool returned an error)."""

    TICK = (QPointF(5, 8.2), QPointF(7, 10.2), QPointF(11, 5.8))

    def __init__(self, ok: bool):
        super().__init__()
        self.ok = ok
        self.progress = 0.0  # 0..0.6 draws the circle, 0.6..1 draws the tick
        self.setFixedSize(16, 16)
        animate(self, 0, 1, 450, self.set_progress)

    def set_progress(self, value: float):
        self.progress = value
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(ACCENT if self.ok else "#5d5d70"), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        circle = min(1.0, self.progress / 0.6)
        p.drawArc(QRectF(1.2, 1.2, 13.6, 13.6), 90 * 16, round(-360 * 16 * circle))  # clockwise from the top
        tick = max(0.0, (self.progress - 0.6) / 0.4)
        if self.ok and tick:
            a, b, c = self.TICK
            first, second = (b - a).manhattanLength(), (c - b).manhattanLength()
            left = tick * (first + second)  # how much of the tick's length to draw
            path = QPainterPath(a)
            path.lineTo(a + (b - a) * min(1.0, left / first))
            if left > first:
                path.lineTo(b + (c - b) * ((left - first) / second))
            p.drawPath(path)


class TypingDots(QWidget):
    """Three dots that pulse one after another while Jarvis works."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(44, 28)
        self.timer = QTimer(self, interval=33)
        self.timer.timeout.connect(lambda: self.isVisible() and not self.window().isMinimized() and self.update())
        self.timer.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        t = CLOCK.elapsed() / 1000
        for i in range(3):
            pulse = 0.5 - 0.5 * math.cos(2 * math.pi * (t / 1.2 - i * 0.15))  # each dot a bit later
            dot = QColor(MUTED)
            dot.setAlphaF(0.3 + 0.7 * pulse)
            p.setBrush(dot)
            p.drawEllipse(QPointF(5 + i * 14, 14 - 2 * pulse), 3.5, 3.5)


def dark_title_bar(window: QWidget) -> bool:
    """Make the native Windows title bar dark and the window's color, so it blends in.
    Asks Windows' window manager (DWM); snap, resize and rounded corners keep working.
    Returns False if Windows refuses (e.g. Windows 10 has no caption color); the app runs anyway."""
    if sys.platform != "win32":
        return False
    hwnd = int(window.winId())
    ok = True
    # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE, 35 = DWMWA_CAPTION_COLOR, 36 = DWMWA_TEXT_COLOR.
    # Colors are COLORREF: 0x00BBGGRR, so #0f0f14 is 0x00140f0f.
    for attribute, value in ((20, 1), (35, 0x00140F0F), (36, 0x00AC9A9A)):
        v = ctypes.c_int(value)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(v), ctypes.sizeof(v))
        ok = ok and result == 0  # 0 = S_OK
    return ok


class GlowButton(QPushButton):
    """A text button (Try again) whose accent background brightens on hover."""

    def __init__(self, text: str, **kwargs):
        super().__init__(text, **kwargs)
        self.hover = 0.0
        self.hover_anim = tween(self, 150, self.set_hover)

    def set_hover(self, value: float):
        self.hover = value
        self.setStyleSheet(f"background: {mix(ACCENT, LIGHT, value).name()};")  # adds to the app's QSS

    def enterEvent(self, event):
        retarget(self.hover_anim, self.hover, 1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        retarget(self.hover_anim, self.hover, 0)
        super().leaveEvent(event)


def markdown_html(text: str, font: QFont) -> str:
    """Markdown → HTML with roomier lines and paragraph gaps (QLabel's own Markdown is cramped)."""
    doc = QTextDocument()
    doc.setDefaultFont(font)
    doc.setMarkdown(text)
    block = doc.begin()
    while block.isValid():
        fmt = block.blockFormat()
        fmt.setLineHeight(150, QTextBlockFormat.ProportionalHeight.value)
        fmt.setBottomMargin(4 if block.textList() else 10)  # list items sit closer together
        QTextCursor(block).setBlockFormat(fmt)
        block = block.next()
    return doc.toHtml()


def centered(widget: QWidget) -> QHBoxLayout:
    """A row that keeps widget in the middle, no wider than the chat column."""
    widget.setMaximumWidth(COLUMN)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(widget, 1)
    row.addStretch()
    return row


class Window(QWidget):
    tool_called = Signal(str, str, str)  # name, arguments, result

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle("Jarvis")
        self.resize(1000, 680)
        self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.steps = None  # the tool card of the current turn, made on its first tool call
        self.worker = None
        self.dots = None  # the typing-dots row while Jarvis works
        self.intro_left = False  # the first-open screen has started to go
        self.tool_called.connect(self.add_step)
        tools.on_call = self.tool_called.emit  # runs in the worker thread; emit is safe there

        # Page 0: first open (board B1). Page 1: the chat.
        self.pages = QStackedWidget()
        self.pages.addWidget(self.empty_page())
        self.pages.addWidget(self.chat_page())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 28)
        layout.setSpacing(16)
        layout.addWidget(self.pages, 1)
        layout.addLayout(centered(self.input_pill()))

    def empty_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.addStretch()
        self.intro_orb = Orb(120, glow=40)
        col.addWidget(self.intro_orb, 0, Qt.AlignHCenter)
        col.addSpacing(28)
        self.intro_texts = [QLabel("How can I help?", objectName="heading"), QLabel("Type below.", objectName="hint")]
        col.addWidget(self.intro_texts[0], 0, Qt.AlignHCenter)
        col.addSpacing(8)
        col.addWidget(self.intro_texts[1], 0, Qt.AlignHCenter)
        col.addStretch()
        return page

    def chat_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        self.orb = Orb(72, glow=24)
        col.addWidget(self.orb, 0, Qt.AlignHCenter)
        self.status = QLabel("Ready", objectName="muted")
        col.addWidget(self.status, 0, Qt.AlignHCenter)

        self.thread_box = QWidget()  # holds the messages, top to bottom
        self.thread = QVBoxLayout(self.thread_box)
        self.thread.setContentsMargins(0, 16, 0, 16)
        self.thread.setSpacing(24)
        self.thread.addStretch()  # last item: keeps messages at the top while there are few

        inner = QWidget()
        inner.setLayout(centered(self.thread_box))
        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        bar = scroll.verticalScrollBar()
        self.glide = QPropertyAnimation(bar, b"value", self, duration=250, easingCurve=QEasingCurve.OutCubic)
        bar.rangeChanged.connect(self.follow)  # glide to the newest message
        col.addWidget(scroll, 1)
        return page

    def input_pill(self) -> QFrame:
        pill = QFrame(objectName="pill")
        self.pill, self.glow_level = pill, 0.0
        self.pill_anim = tween(pill, 150, self.set_pill_glow)  # owned by the pill, so it goes when the pill does
        shadow = QGraphicsDropShadowEffect(blurRadius=32, offset=QPointF(0, 8), color=QColor(0, 0, 0, 100))
        pill.setGraphicsEffect(shadow)
        row = QHBoxLayout(pill)
        row.setContentsMargins(22, 8, 8, 8)
        row.setSpacing(8)
        self.input = QLineEdit(placeholderText="Ask anything")
        self.input.setAccessibleName("Message")
        self.input.setMinimumHeight(44)
        self.input.returnPressed.connect(self.send)
        self.send_button = SendButton()
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        self.input.installEventFilter(self)  # to hear when it gains or loses focus (see eventFilter)
        return pill

    def eventFilter(self, watched, event):
        if watched is self.input and event.type() in (QEvent.FocusIn, QEvent.FocusOut):
            retarget(self.pill_anim, self.glow_level, event.type() == QEvent.FocusIn)  # border glows while you type
        return super().eventFilter(watched, event)

    def set_pill_glow(self, value: float):
        self.glow_level = value
        self.pill.setStyleSheet(f"QFrame#pill {{ border-color: {mix('#2c2c3a', ACCENT, 0.6 * value).name()}; }}")

    def follow(self, _min: int, top: int):
        self.glide.stop()
        self.glide.setStartValue(self.glide.targetObject().value())
        self.glide.setEndValue(top)
        self.glide.start()

    def reveal(self, row: QHBoxLayout) -> QWidget:
        """Put a row into the chat, fading it in while it rises 12 px."""
        holder = QWidget()
        holder.setLayout(row)
        effect = QGraphicsOpacityEffect(holder, opacity=0)
        holder.setGraphicsEffect(effect)
        self.thread.insertWidget(self.thread.count() - 1, holder)  # before the stretch

        def frame(v: float):
            effect.setOpacity(v)
            row.setContentsMargins(0, round(12 * (1 - v)), 0, 0)

        frame(0)
        # Remove the effect when done: left on, it would blur the text and slow scrolling.
        animate(holder, 0, 1, 250, frame).finished.connect(lambda: holder.setGraphicsEffect(None))
        return holder

    def show_dots(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(Orb(28), 0, Qt.AlignTop)
        row.addWidget(TypingDots(), 0, Qt.AlignTop)
        row.addStretch()
        self.dots = self.reveal(row)

    def drop_dots(self):
        if self.dots:
            self.dots.hide()
            self.dots.deleteLater()
            self.dots = None

    def add_user(self, text: str):
        bubble = QLabel(text, objectName="user", wordWrap=True, textFormat=Qt.PlainText)
        widest = int(COLUMN * 0.75)
        bubble.setMaximumWidth(widest)
        # A wrapping QLabel picks a narrow width on its own; ask for the text's width (+ padding) instead.
        bubble.ensurePolished()
        needed = bubble.fontMetrics().horizontalAdvance(text) + 40
        bubble.setMinimumWidth(min(needed, widest))
        bubble.setWordWrap(needed > widest)  # a one-line bubble that wraps gets reserved a 2nd line
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(bubble)
        self.reveal(row)

    def add_jarvis(self, text: str):
        answer = QLabel(wordWrap=True, openExternalLinks=True)
        answer.ensurePolished()
        answer.setText(markdown_html(text, answer.font()))
        answer.setTextInteractionFlags(Qt.TextBrowserInteraction)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(Orb(28), 0, Qt.AlignTop)
        row.addWidget(answer, 1)
        self.reveal(row)

    def add_step(self, name: str, arguments: str, result: str):
        """One row in the tool card (board B2), e.g. "open_app(notepad): Opened notepad"."""
        self.drop_dots()
        new_card = self.steps is None
        if new_card:
            self.steps = QFrame(objectName="steps")
            QVBoxLayout(self.steps).setContentsMargins(6, 6, 6, 6)
            row = QHBoxLayout()
            row.addSpacing(28 + 14)  # line up with Jarvis's text, past the avatar
            row.addWidget(self.steps, 1)
            self.reveal(row)
        try:
            shown = ", ".join(str(v) for v in json.loads(arguments).values())
        except (ValueError, AttributeError):  # not a JSON object: show it as it came
            shown = arguments
        ok = not result.startswith("Error")
        text = QLabel(f"{name}({shown}): {result}", objectName="step", wordWrap=True)
        text.setProperty("failed", not ok)
        line = QHBoxLayout()
        line.setContentsMargins(12, 10, 12, 10)
        line.setSpacing(12)
        line.addWidget(Check(ok))
        line.addWidget(text, 1)
        holder = QWidget()
        holder.setLayout(line)
        self.steps.layout().addWidget(holder)
        if not new_card:  # a new card already fades in as a whole
            effect = QGraphicsOpacityEffect(holder, opacity=0)
            holder.setGraphicsEffect(effect)
            animate(holder, 0, 1, 250, effect.setOpacity).finished.connect(lambda: holder.setGraphicsEffect(None))

    def add_error(self, message: str, text: str):
        """The error card (board B5) with a Try again button that resends text."""
        card = QFrame(objectName="error")
        inside = QVBoxLayout(card)
        inside.setContentsMargins(18, 16, 18, 16)
        inside.setSpacing(6)
        inside.addWidget(QLabel("I couldn't finish that", objectName="errorTitle"))
        inside.addWidget(QLabel(message, objectName="errorBody", wordWrap=True, textFormat=Qt.PlainText))
        retry = GlowButton("Try again", objectName="retry", cursor=Qt.PointingHandCursor)
        retry.clicked.connect(lambda: (retry.hide(), self.submit(text, again=True)))  # hide it: one retry per card
        col = QVBoxLayout()
        col.setSpacing(14)
        col.addWidget(card)
        col.addWidget(retry, 0, Qt.AlignLeft)
        avatar = Orb(28)
        avatar.grey = 1.0
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(avatar, 0, Qt.AlignTop)
        row.addLayout(col, 1)
        self.reveal(row)

    def set_failed(self, failed: bool):
        self.orb.set_grey(failed)
        self.status.setProperty("failed", failed)
        self.status.style().polish(self.status)  # re-read the stylesheet for the new property

    def set_working(self, working: bool):
        self.orb.working = working
        self.orb.update()
        self.status.setText("Working" if working else "Ready")
        self.input.setPlaceholderText("Jarvis is working…" if working else "Ask anything")
        self.input.setEnabled(not working)
        self.send_button.setEnabled(not working)
        if not working:
            self.input.setFocus()

    def send(self):
        text = self.input.text().strip()
        if not text or not self.input.isEnabled():
            return
        self.input.clear()
        self.send_button.nudge()
        self.submit(text)

    def leave_intro(self):
        """First message: fade out the welcome text, then fly the big orb up into the small top orb."""
        effects = []
        for label in self.intro_texts:
            effects.append(QGraphicsOpacityEffect(label))
            label.setGraphicsEffect(effects[-1])
        fade = animate(self, 1, 0, 150, lambda v: [e.setOpacity(v) for e in effects])
        fade.finished.connect(self.fly_orb)

    def fly_orb(self):
        start = QPointF(self.intro_orb.mapTo(self, self.intro_orb.rect().center()))
        self.pages.setCurrentIndex(1)
        self.layout().activate()  # place the chat page now, so the top orb's position is known
        self.orb.ghost = True
        fly = Orb(120, glow=40)
        fly.setParent(self)
        fly.working = self.orb.working
        fly.show()
        fly.raise_()

        def step(t: float):
            target = QPointF(self.orb.mapTo(self, self.orb.rect().center()))  # re-read: survives a resize
            fly.resize_to(120 + (72 - 120) * t, 40 + (24 - 40) * t)
            center = start + (target - start) * t
            fly.move(round(center.x() - fly.width() / 2), round(center.y() - fly.height() / 2))

        def land():
            fly.deleteLater()
            self.orb.ghost = False
            self.orb.update()

        step(0)
        animate(self, 0, 1, 450, step).finished.connect(land)

    def submit(self, text: str, again: bool = False):
        if self.worker and self.worker.isRunning():  # e.g. Try again clicked while a turn runs
            return
        if not self.intro_left:  # only once, even if a second turn starts mid-transition
            self.intro_left = True
            self.leave_intro()
        self.set_failed(False)
        self.set_working(True)
        self.steps = None
        if not again:  # a retry's question is already on screen
            self.add_user(text)
        self.show_dots()
        self.worker = Worker(self.messages, text)  # kept on self so it isn't garbage-collected mid-run
        self.worker.done.connect(lambda answer, ok: self.show_answer(answer, ok, text))
        self.worker.start()

    def show_answer(self, answer: str, ok: bool, text: str):
        self.drop_dots()
        if ok:
            self.add_jarvis(answer)
        else:
            self.add_error(answer, text)
        self.set_working(False)
        if not ok:
            self.status.setText("Something went wrong")
        self.set_failed(not ok)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI"))
    palette = app.palette()
    palette.setColor(QPalette.PlaceholderText, QColor(MUTED))
    palette.setColor(QPalette.Link, QColor(ACCENT))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
    window = Window()
    dark_title_bar(window)
    window.show()
    sys.exit(app.exec())
