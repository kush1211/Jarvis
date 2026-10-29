"""Jarvis window (basic, for testing the connection; the real design replaces it).
Run: .venv\\Scripts\\python app.py"""
import sys

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QVBoxLayout, QWidget

import config
import jarvis


class Worker(QThread):
    """Runs one turn off the UI thread, so the window doesn't freeze while the model thinks."""
    done = Signal(str)

    def __init__(self, messages: list[dict], text: str):
        super().__init__()
        self.messages, self.text = messages, text

    def run(self):
        try:
            self.done.emit(jarvis.ask(self.messages, self.text))
        except Exception as e:  # anything ask() doesn't expect; without this the input stays locked
            self.done.emit(f"Unexpected error: {e}")


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Jarvis ({config.BASE_URL})")
        self.resize(600, 500)
        self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

        self.chat = QTextEdit(readOnly=True)
        self.input = QLineEdit(placeholderText="Message Jarvis, Enter to send")
        self.input.returnPressed.connect(self.send)
        layout = QVBoxLayout(self)
        layout.addWidget(self.chat)
        layout.addWidget(self.input)

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.input.setEnabled(False)
        self.chat.append(f"<b>you&gt;</b> {text}")
        self.worker = Worker(self.messages, text)  # kept on self so it isn't garbage-collected mid-run
        self.worker.done.connect(self.show_answer)
        self.worker.start()

    def show_answer(self, answer: str):
        self.chat.append(f"<b>jarvis&gt;</b> {answer}<br>")
        self.input.setEnabled(True)
        self.input.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
