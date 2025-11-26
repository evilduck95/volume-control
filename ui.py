import random
import threading
import time

import screeninfo
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMainWindow, QPushButton, QProgressBar, QLabel

PROGRESS_BAR_STYLE = """
QProgressBar {
    border: 2px dashed grey;
    border-radius: 0;
    text-align: center;
}
"""


class VolumeBar(QWidget):

    def __init__(self, hide_timeout, monitor_index=0, bar_width=400, bar_height=100):
        super().__init__()
        self.hide_timeout = hide_timeout
        self.monitor_index = monitor_index
        self.last_update_stamp = 0
        layout = QVBoxLayout()
        self.label = QLabel("Volume Bar")
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(PROGRESS_BAR_STYLE)
        layout.addWidget(self.progress_bar)
        self.setGeometry(self._get_monitor_center(bar_width, bar_height))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setLayout(layout)
        self.hide_thread = threading.Thread(target=self._hide_listener, daemon=True)
        self.hide_thread.start()
        self.show()

    def set_percentage(self, value: int):
        self.show()
        self.progress_bar.setValue(value)
        self.last_update_stamp = time.time()

    def _hide_listener(self):
        while True:
            time.sleep(.5)
            if time.time() - self.last_update_stamp > self.hide_timeout:
                self.hide()

    def _get_monitor_center(self, bar_width, bar_height) -> QRect:
        monitor: screeninfo.Monitor = screeninfo.get_monitors()[self.monitor_index]
        return QRect(round(monitor.x + monitor.width / 2 - bar_width / 2),
                     round(monitor.y + monitor.height / 2 - bar_height / 2), bar_width, bar_height)


class OptionsWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.w = VolumeBar(2)
        self.w.hide()
        self.button = QPushButton("Trick or Treat!")
        self.button.clicked.connect(self.show_new_window)
        self.setCentralWidget(self.button)

    def show_new_window(self):
        self.w.set_percentage(random.randint(0, 100))

# app = QApplication(sys.argv)
# w = OptionsWindow()
# w.show()
# app.exec()
