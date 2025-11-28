import threading
import time

import screeninfo
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QSlider, QFormLayout

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


class VolumeTickSelector(QWidget):

    def __init__(self, starting_value=10):
        super().__init__()
        layout = QFormLayout()
        self.slider_value_label = QLabel(f'Volume Change Interval: {starting_value}')
        layout.addRow(self.slider_value_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QSlider.TickPosition.TicksAbove)
        self.slider.setRange(1, 100)
        self.slider.setValue(starting_value)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.update_value)

        layout.addRow(self.slider)
        self.setLayout(layout)

    def update_value(self, value):
        self.slider_value_label.setText(f'Volume Change Interval: {value}')


class KeybindSetter(QWidget):

    def __init__(self):
        super().__init__()
        layout = QFormLayout()


class OptionsWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(False)
        layout = QFormLayout()
        self.volume_tick_selector = VolumeTickSelector()
        layout.addRow(self.volume_tick_selector)
        self.setLayout(layout)
