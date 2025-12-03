import threading
import time
from typing import Callable

import screeninfo
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QSlider, QFormLayout, QLineEdit
from pynput.keyboard import KeyCode, Key

from keybindhandlers import KeybindCollector, get_virtual_key_code, SavedKeybind

PROGRESS_BAR_STYLE = """
QProgressBar {
    border: 2px dashed grey;
    border-radius: 0;
    text-align: center;
}
"""


def get_key_name(key: Key | KeyCode):
    name = key.name if hasattr(key, 'name') else key.char
    if name is None:
        return str(get_virtual_key_code(key))
    return name.capitalize()


def pretty_binding_string(binding: SavedKeybind):
    if binding.is_scroll_based():
        binding_activation_string = binding.bound_scroll.value
    else:
        binding_activation_string = binding.saved_bound_key if hasattr(binding, 'saved_bound_key') else get_key_name(
            binding.bound_key)
    binding_activation_string = binding_activation_string.capitalize()
    if hasattr(binding, 'saved_modifiers'):
        return ' + '.join([name.capitalize() for name in binding.saved_modifiers]) + f' + {binding_activation_string}'
    else:
        return ' + '.join([get_key_name(key) for key in binding.modifiers]) + f' + {binding_activation_string}'


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

    def __init__(self, save_file: str):
        self.save_file = save_file
        QThread.__init__(self)

    def run(self):
        collector = KeybindCollector()
        binding = collector.collect_keybind()
        print(f'Modifier: {binding.modifiers}, Key: {binding.bound_key}, Scroll: {binding.bound_scroll}')
        collector.save_keybind(self.save_file)
        keybind_string = pretty_binding_string(binding)
        self.keybind_changed.emit(keybind_string)


class KeybindSetter(QWidget):

    def __init__(self, label: str, save_file: str, current_binding: SavedKeybind, after_set_callback: Callable):
        super().__init__()
        self.save_file = save_file
        layout = QFormLayout()
        self.label = QLabel(label)
        layout.addRow(self.label)
        self.keybind_input = ClickableLineEdit(pretty_binding_string(current_binding))
        self.keybind_input.resize(250, 40)
        self.keybind_input.clicked.connect(self._clicked)
        layout.addRow(self.keybind_input)
        self.setLayout(layout)
        self.after_set_callback = after_set_callback

    def _update_keybind_text(self, text):
        self.keybind_input.setText(text)

    def _clicked(self):
        self.keybind_input.setText('Press keybind...')
        # threading.Thread(target=self._collect_keybind_from_user).start()
        self.keybind_collector = UserKeybindInputThread(self.save_file)
        self.keybind_collector.keybind_changed.connect(self._update_keybind_text)
        self.keybind_collector.keybind_changed.connect(self.after_set_callback)
        self.keybind_collector.start()


class OptionsWindow(QWidget):

    def __init__(self,
                 volume_up_keybind_file: str,
                 volume_down_keybind_file: str,
                 volume_up_binding: SavedKeybind,
                 volume_down_binding: SavedKeybind,
                 restart_listeners_callback: Callable):
        super().__init__()
        self.setAutoFillBackground(False)
        layout = QFormLayout()
        self.volume_tick_selector = VolumeTickSelector()
        layout.addRow(self.volume_tick_selector)
        self.volume_up_keybind_input = KeybindSetter(
            'Volume Up',
            volume_up_keybind_file,
            volume_up_binding,
            restart_listeners_callback)
        layout.addRow(self.volume_up_keybind_input)
        self.volume_down_keybind_input = KeybindSetter(
            'Volume Down',
            volume_down_keybind_file,
            volume_down_binding,
            restart_listeners_callback)
        layout.addRow(self.volume_down_keybind_input)
        self.setLayout(layout)
