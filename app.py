"""Jarvis window, "Quiet Glass" design. Run: .venv\\Scripts\\python app.py"""
import ctypes
import json
import sys

from PySide6.QtCore import QPointF, Qt, QThread, Signal
from PySide6.QtGui import (QColor, QFont, QPainter, QPainterPath, QPalette, QPen, QRadialGradient,
                           QTextBlockFormat, QTextCursor, QTextDocument)
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

import config
import jarvis
import tools

BG, TEXT, MUTED, ACCENT, DEEP = "#0f0f14", "#ececf3", "#9a9aac", "#a9a4ff", "#3b3a8f"
WARN = "#ffb48a"  # error text (board B5)
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


class Orb(QWidget):
    """The glowing ball: a radial gradient lit from the top left, with an optional soft glow around it."""

    def __init__(self, size: int, glow: int = 0):
        super().__init__()
        self.size, self.glow = size, glow
        self.working = False  # True draws two faint rings around the ball
        self.offline = False  # True turns it grey (board B5)
        self.setFixedSize(size + 2 * glow, size + 2 * glow)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        center = QPointF(self.width() / 2, self.height() / 2)
        r = self.size / 2
        if self.glow:
            halo = QRadialGradient(center, r + self.glow)
            edge = QColor("#5d5d70" if self.offline else ACCENT)
            edge.setAlpha(0x40 if self.offline else 0x66)
            halo.setColorAt(r / (r + self.glow) * 0.8, edge)
            halo.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(halo)
            p.drawEllipse(center, r + self.glow, r + self.glow)
        if self.working:
            for ring, alpha in ((18, 0x10), (8, 0x1f)):
                tint = QColor(ACCENT)
                tint.setAlpha(alpha)
                p.setBrush(tint)
                p.drawEllipse(center, r + ring, r + ring)
        light = QPointF(center.x() - 0.3 * self.size, center.y() - 0.4 * self.size)
        body = QRadialGradient(light, self.size * 0.95)
        lit, mid, dark = ("#c9c9d8", "#5d5d70", "#2a2a38") if self.offline else ("#ffffff", ACCENT, DEEP)
        body.setColorAt(0, QColor(lit))
        body.setColorAt(0.38, QColor(mid))
        body.setColorAt(1, QColor(dark))
        p.setBrush(body)
        p.drawEllipse(center, r, r)


class SendButton(QPushButton):
    """Round accent button with an up arrow, painted so it needs no icon files."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Send")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACCENT if self.isEnabled() else "#2c2c3a"))
        p.drawEllipse(self.rect())
        arrow = QPainterPath()
        arrow.moveTo(22, 30); arrow.lineTo(22, 14)
        arrow.moveTo(16, 19); arrow.lineTo(22, 13); arrow.lineTo(28, 19)
        p.setPen(QPen(QColor("#14142a"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(arrow)


class Check(QWidget):
    """16 px circle with a tick (done) or a plain grey circle (the tool returned an error)."""

    def __init__(self, ok: bool):
        super().__init__()
        self.ok = ok
        self.setFixedSize(16, 16)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(ACCENT if self.ok else "#5d5d70"), 1.4))
        p.drawEllipse(QPointF(8, 8), 6.8, 6.8)
        if self.ok:
            tick = QPainterPath()
            tick.moveTo(5, 8.2); tick.lineTo(7, 10.2); tick.lineTo(11, 5.8)
            p.drawPath(tick)


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
        col.addWidget(Orb(120, glow=40), 0, Qt.AlignHCenter)
        col.addSpacing(28)
        heading = QLabel("How can I help?", objectName="heading")
        col.addWidget(heading, 0, Qt.AlignHCenter)
        col.addSpacing(8)
        col.addWidget(QLabel("Type below.", objectName="hint"), 0, Qt.AlignHCenter)
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
        bar.rangeChanged.connect(lambda _min, top: bar.setValue(top))  # follow the newest message
        col.addWidget(scroll, 1)
        return page

    def input_pill(self) -> QFrame:
        pill = QFrame(objectName="pill")
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
        return pill

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
        self.thread.insertLayout(self.thread.count() - 1, row)  # before the stretch

    def add_jarvis(self, text: str):
        answer = QLabel(wordWrap=True, openExternalLinks=True)
        answer.ensurePolished()
        answer.setText(markdown_html(text, answer.font()))
        answer.setTextInteractionFlags(Qt.TextBrowserInteraction)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(Orb(28), 0, Qt.AlignTop)
        row.addWidget(answer, 1)
        self.thread.insertLayout(self.thread.count() - 1, row)  # before the stretch

    def add_step(self, name: str, arguments: str, result: str):
        """One row in the tool card (board B2), e.g. "open_app(notepad): Opened notepad"."""
        if self.steps is None:
            self.steps = QFrame(objectName="steps")
            QVBoxLayout(self.steps).setContentsMargins(6, 6, 6, 6)
            row = QHBoxLayout()
            row.addSpacing(28 + 14)  # line up with Jarvis's text, past the avatar
            row.addWidget(self.steps, 1)
            self.thread.insertLayout(self.thread.count() - 1, row)
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
        self.steps.layout().addLayout(line)

    def add_error(self, message: str, text: str):
        """The error card (board B5) with a Try again button that resends text."""
        card = QFrame(objectName="error")
        inside = QVBoxLayout(card)
        inside.setContentsMargins(18, 16, 18, 16)
        inside.setSpacing(6)
        inside.addWidget(QLabel("I couldn't finish that", objectName="errorTitle"))
        inside.addWidget(QLabel(message, objectName="errorBody", wordWrap=True, textFormat=Qt.PlainText))
        retry = QPushButton("Try again", objectName="retry", cursor=Qt.PointingHandCursor)
        retry.clicked.connect(lambda: (retry.hide(), self.submit(text, again=True)))  # hide it: one retry per card
        col = QVBoxLayout()
        col.setSpacing(14)
        col.addWidget(card)
        col.addWidget(retry, 0, Qt.AlignLeft)
        avatar = Orb(28)
        avatar.offline = True
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(avatar, 0, Qt.AlignTop)
        row.addLayout(col, 1)
        self.thread.insertLayout(self.thread.count() - 1, row)

    def set_failed(self, failed: bool):
        self.orb.offline = failed
        self.orb.update()
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
        self.submit(text)

    def submit(self, text: str, again: bool = False):
        if self.worker and self.worker.isRunning():  # e.g. Try again clicked while a turn runs
            return
        self.pages.setCurrentIndex(1)
        self.set_failed(False)
        self.set_working(True)
        self.steps = None
        if not again:  # a retry's question is already on screen
            self.add_user(text)
        self.worker = Worker(self.messages, text)  # kept on self so it isn't garbage-collected mid-run
        self.worker.done.connect(lambda answer, ok: self.show_answer(answer, ok, text))
        self.worker.start()

    def show_answer(self, answer: str, ok: bool, text: str):
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
