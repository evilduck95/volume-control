import math
import threading
import time
from typing import Callable

import screeninfo
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pynput.keyboard import KeyCode, Key

from keybindhandlers import KeybindCollector, get_virtual_key_code, SavedKeybind

PROGRESS_BAR_STYLE_DEFAULT = """
QProgressBar {
    border: 2px dashed grey;
    border-radius: 0;
    text-align: center;
}
"""

PROGRESS_BAR_ERROR_STYLE = """
QProgressBar {
    border: 2px dashed grey;
    border-radius: 0;
    text-align: center;
}
QProgressBar::chunk {
    background-color: red;
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


def get_monitor_center(monitor_index, window_width, window_height) -> QRect:
    monitor: screeninfo.Monitor = screeninfo.get_monitors()[monitor_index]
    return QRect(round(monitor.x + monitor.width / 2 - window_width / 2),
                 round(monitor.y + monitor.height / 2 - window_height / 2), window_width, window_height)


def get_primary_monitor():
    for idx, monitor in enumerate(screeninfo.get_monitors()):
        if monitor.is_primary:
            return idx
    print('How did we get here??')
    return 0


# Credit to: https://stackoverflow.com/questions/64290561/qlabel-correct-positioning-for-text-outline
class OutlinedLabel(QLabel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stroke_thickness = 1 / 25
        self.stroke_mode = False
        q_brush = QBrush(QColor("white"))
        q_brush.setStyle(Qt.BrushStyle.SolidPattern)
        self.set_brush(q_brush)
        self.set_pen(QPen(QColor("black")))

    def scaled_outline_mode(self):
        return self.stroke_mode

    def set_scaled_outline_mode(self, mode):
        self.stroke_mode = mode

    def outline_thickness(self):
        return self.stroke_thickness * self.font().pointSize() if self.stroke_mode else self.stroke_thickness

    def set_outline_thickness(self, thickness):
        self.stroke_thickness = thickness

    def set_brush(self, brush):
        if not isinstance(brush, QBrush):
            brush = QBrush(brush)
        self.brush = brush

    def set_pen(self, pen):
        if not isinstance(pen, QPen):
            pen = QPen(pen)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.pen = pen

    def sizeHint(self):
        w = math.ceil(self.outline_thickness() * 2)
        return super().sizeHint() + QSize(w, w)

    def minimumSizeHint(self):
        w = math.ceil(self.outline_thickness() * 2)
        return super().minimumSizeHint() + QSize(w, w)

    def paintEvent(self, event):
        stroke_width = self.outline_thickness()
        rect = self.rect()
        metrics = QFontMetricsF(self.font())
        tr = metrics.boundingRect(self.text()).adjusted(0, 0, stroke_width, stroke_width)

        # Indentation
        if self.indent() == -1:
            if self.frameWidth():
                indentation = (metrics.boundingRect('x').width() + stroke_width * 2) / 2
            else:
                indentation = stroke_width
        else:
            indentation = self.indent()

        # Horizontal Alignment
        if self.alignment() & Qt.AlignmentFlag.AlignLeft:
            path_start_x = rect.left() + indentation - min(metrics.leftBearing(self.text()[0]), 0)
        elif self.alignment() & Qt.AlignmentFlag.AlignRight:
            path_start_x = rect.x() + rect.width() - indentation - tr.width()
        else:
            path_start_x = (rect.width() - tr.width()) / 2

        # Vertical Alignment
        if self.alignment() & Qt.AlignmentFlag.AlignTop:
            path_start_y = rect.top() + indentation + metrics.ascent()
        elif self.alignment() & Qt.AlignmentFlag.AlignBottom:
            path_start_y = rect.y() + rect.height() - indentation - metrics.descent()
        else:
            path_start_y = (rect.height() + metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(path_start_x, path_start_y, self.font(), self.text())
        qp = QPainter(self, )
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.pen.setWidth(int(stroke_width))
        qp.strokePath(path, self.pen)
        if 1 < self.brush.style().value < 15:
            qp.fillPath(path, self.palette().window())
        qp.fillPath(path, self.brush)


class VolumeBar(QWidget):

    def __init__(self, hide_timeout, monitor_index=0, bar_width=400, bar_height=100):
        super().__init__()
        self.hide_timeout = hide_timeout
        self.monitor_index = monitor_index
        self.last_update_stamp = 0
        layout = QVBoxLayout()
        self.label = OutlinedLabel("Volume Bar")
        self.label.set_brush(QBrush(QColor("white")))
        self.label.setStyleSheet("font-size: 20pt; font-family: Monaco;")
        self.label.set_outline_thickness(2)
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(PROGRESS_BAR_STYLE_DEFAULT)
        layout.addWidget(self.progress_bar)
        self.setGeometry(get_monitor_center(monitor_index, bar_width, bar_height))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setLayout(layout)
        self.hide_thread = threading.Thread(target=self._hide_listener, daemon=True)
        self.hide_thread.start()
        self.show()

    def set_error(self, text: str):
        self.label.set_brush(QBrush(QColor("lightcoral")))
        self.label.setText(text)
        # self.show()
        self._stamp_update_time()

    def set_percentage(self, value: int, text: str = ''):
        self.show()
        self._reset_style()
        self.label.setText(text)
        self.progress_bar.setValue(value)
        self._stamp_update_time()

    def _add_shadow(self, item: QWidget):
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(2)
        effect.setColor(QColor("black"))
        effect.setOffset(2, 2)
        item.setGraphicsEffect(effect)

    def _reset_style(self):
        self.label.set_brush(QBrush(QColor("white")))
        self.label.clear()

    def _stamp_update_time(self):
        self.last_update_stamp = time.time()

    def _hide_listener(self):
        while True:
            time.sleep(.5)
            if time.time() - self.last_update_stamp > self.hide_timeout:
                self.hide()


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
        self.setWindowTitle('Options')
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
        self.setGeometry(get_monitor_center(get_primary_monitor(), 100, 100))
