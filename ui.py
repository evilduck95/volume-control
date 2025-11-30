import threading
import time

import screeninfo
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QSlider, QFormLayout, QLineEdit
from pynput.keyboard import KeyCode, Key

from keybindhandlers import KeybindCollector

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


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        else:
            super().mousePressEvent(event)


class UserKeybindInputThread(QThread):
    keybind_changed = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)

    def _get_key_name(self, key: Key | KeyCode):
        name = key.name if hasattr(key, 'name') else key.char
        return name.capitalize()

    def run(self):
        collector = KeybindCollector()
        binding = collector.collect_keybind()
        modifier_keys = binding.modifiers
        bound_key = binding.bound_key
        bound_scroll = binding.bound_scroll
        print(f'Modifier: {modifier_keys}, Key: {bound_key}, Scroll: {bound_scroll}')
        collector.save_keybind('keybind')
        keybind_string = ' + '.join([self._get_key_name(key) for key in modifier_keys]) + f' + {self._get_key_name(bound_key) if bound_scroll is None else bound_scroll.value}'
        self.keybind_changed.emit(keybind_string)


class KeybindSetter(QWidget):

    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.keybind_input = ClickableLineEdit('Click to set')
        self.keybind_input.resize(250, 40)
        self.keybind_input.clicked.connect(self._clicked)
        layout.addRow(self.keybind_input)
        self.setLayout(layout)

    def _update_keybind_text(self, text):
        self.keybind_input.setText(text)

    def _clicked(self):
        self.keybind_input.setText('Press keybind...')
        # threading.Thread(target=self._collect_keybind_from_user).start()
        self.keybind_collector = UserKeybindInputThread()
        self.keybind_collector.keybind_changed.connect(self._update_keybind_text)
        self.keybind_collector.start()


class OptionsWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(False)
        layout = QFormLayout()
        self.volume_tick_selector = VolumeTickSelector()
        layout.addRow(self.volume_tick_selector)
        self.keybind_input = KeybindSetter()
        layout.addRow(self.keybind_input)
        self.setLayout(layout)
