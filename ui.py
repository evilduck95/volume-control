import math
import threading
import time
from functools import cached_property
from typing import Callable

import screeninfo
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from pynput import keyboard
from pynput.keyboard import KeyCode, Key

import generalutils
import keybindhandlers as kb2
import keybindutils
from loggingutils import get_logger

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

ADD_ROW_BUTTON_DEFAULT = """
QPushButton {
    margin-top: 5px;
}
"""

REMOVE_BUTTON_DEFAULT = """
QPushButton {
    margin-left: 10px;
}
"""

user_editing_signal: generalutils.Signal = generalutils.Signal[bool]('user_editing')

logger = get_logger(__file__)


def get_key_name(key: Key | KeyCode):
    name = key.name if hasattr(key, 'name') else key.char
    if name is None:
        return str(keybindutils.get_virtual_key_code(key))
    return name.capitalize()


def get_monitor_center(monitor_index, window_width, window_height) -> QRect:
    monitor: screeninfo.Monitor = screeninfo.get_monitors()[monitor_index]
    return QRect(round(monitor.x + monitor.width / 2 - window_width / 2),
                 round(monitor.y + monitor.height / 2 - window_height / 2), window_width, window_height)


def get_primary_monitor():
    for idx, monitor in enumerate(screeninfo.get_monitors()):
        if monitor.is_primary:
            return idx
    logger.critical('How did we get here??')
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
        self.label.set_outline_thickness(3)
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

    # Make the window clear itself in 3/4s of a second when the mouse is over the window
    def enterEvent(self, event):
        self.last_update_stamp = self.hide_timeout - .75

    def set_error(self, text: str):
        self.label.set_brush(QBrush(QColor("lightcoral")))
        self.label.setText(text.capitalize())
        # self.show() Requires a better keyboard event library
        self._stamp_update_time()

    def set_percentage(self, value: int, text: str = ''):
        self.show()
        self._reset_style()
        self.label.setText(text.capitalize())
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

    def __init__(self, change_callback: Callable, starting_value=10):
        super().__init__()
        layout = QFormLayout()
        self.slider_value_label = QLabel()
        self.update_value(starting_value)
        layout.addRow(self.slider_value_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QSlider.TickPosition.TicksAbove)
        self.slider.setRange(1, 50)
        self.slider.setValue(starting_value)
        self.slider.setSingleStep(1)
        self.slider.setTickInterval(5)
        self.slider.wheelEvent = generalutils.noop_func
        # self.slider.setStyleSheet(SLIDER_STYLE_DEFAULT)
        self.slider.valueChanged.connect(self.update_value)
        self.slider.sliderReleased.connect(lambda: change_callback(self.slider.value() / 100))

        layout.addRow(self.slider)
        self.setLayout(layout)

    def update_value(self, value):
        self.slider_value_label.setText(f'Volume Change/Tick: {value}%')


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        global user_editing_signal
        if event.button() == Qt.MouseButton.LeftButton:
            user_editing_signal.emit(True)
            self.clicked.emit()
        else:
            super().mousePressEvent(event)


class UserKeybindInputThread(QThread):
    keybind_changed = pyqtSignal(str)

    def __init__(self, bind_name: str, bind_index: int):
        self.bind_name = bind_name
        self.bind_index = bind_index
        self.saved_bind: kb2.BindingGroup = kb2.load_bind(bind_name)
        QThread.__init__(self)

    def _update_or_add_binding(self, binding: kb2.Binding):
        if self.saved_bind is None:
            saved_bindings = []
        else:
            saved_bindings = self.saved_bind.bindings
        if len(saved_bindings) <= self.bind_index:
            saved_bindings.append(binding)
        else:
            saved_bindings[self.bind_index] = binding
        return saved_bindings.copy()

    def run(self):
        global user_editing_signal
        collector = kb2.KeybindCollector()
        binding = collector.collect_keybind()
        user_editing_signal.emit(False)
        logger.debug(f'Collected: {binding.keys}, {binding.mouse_action}')
        updated_bindings = self._update_or_add_binding(binding)
        updated_bound_action = kb2.BindingGroup(bindings=updated_bindings, name=self.bind_name)
        kb2.save_bind(updated_bound_action)
        self.keybind_changed.emit(str(binding))


class KeybindSetter(QWidget):

    def __init__(self, bind_name: str, bind_index: int, after_set_callback: Callable):
        super().__init__()
        self.bind_name = bind_name
        self.bind_index = bind_index
        layout = QVBoxLayout()
        self.current_bound_action: kb2.BindingGroup = kb2.load_bind(bind_name)
        if self.current_bound_action is not None and len(self.current_bound_action.bindings) > bind_index:
            display_text = str(self.current_bound_action.bindings[bind_index])
        else:
            display_text = 'Press to set keybind...'
        bottom_row = QHBoxLayout()
        layout.addLayout(bottom_row)
        self.keybind_input = ClickableLineEdit(display_text)
        self.keybind_input.resize(250, 40)
        self.keybind_input.setReadOnly(True)
        self.keybind_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.keybind_input.clicked.connect(self._clicked)
        bottom_row.addWidget(self.keybind_input)
        remove_button = QPushButton('-')
        remove_button.setStyleSheet(REMOVE_BUTTON_DEFAULT)
        remove_button.setMinimumHeight(25)
        remove_button.setMinimumWidth(40)
        remove_button.clicked.connect(self._remove_bind)
        bottom_row.addWidget(remove_button, alignment=Qt.AlignmentFlag.AlignBottom)
        bottom_row.setSpacing(0)
        self.setLayout(layout)
        self.after_set_callback = after_set_callback

    def select(self):
        self.keybind_input.clicked.emit()

    def _remove_bind(self):
        saved_binding: kb2.BindingGroup = kb2.load_bind(self.bind_name)
        if saved_binding is not None and len(saved_binding.bindings) > self.bind_index:
            saved_binding.bindings.pop(self.bind_index)
            kb2.save_bind(saved_binding)
        self.after_set_callback()
        self.deleteLater()
        user_editing_signal.emit(False)

    def _update_keybind_text(self, text):
        self.keybind_input.setText(text)

    def _clicked(self):
        self.keybind_input.setText('Press keybind...')
        self.keybind_collector = UserKeybindInputThread(self.bind_name, self.bind_index)
        self.keybind_collector.keybind_changed.connect(self._update_keybind_text)
        self.keybind_collector.keybind_changed.connect(self.after_set_callback)
        self.keybind_collector.start()


class ExtendableKeybindSetterList(QWidget):

    def __init__(self, label: str, bind_name: str, after_set_callback: Callable):
        super().__init__()
        self.bind_name = bind_name
        self.inputs = []
        self.after_set_callback = after_set_callback
        bound_action: kb2.BindingGroup = kb2.load_bind(bind_name)
        num_of_bindings = 0 if bound_action is None else len(bound_action.bindings)
        layout = QVBoxLayout()
        self.label = QLabel(label)
        self.label.setMargin(10)
        layout.addWidget(self.label)
        for i in range(num_of_bindings):
            self.inputs.append(
                KeybindSetter(bind_name, i, self._after_new_row_set)
            )
        for widget in self.inputs:
            self._stacked_widget.addWidget(widget)
        layout.addLayout(self._stacked_widget)
        self.add_row_button = QPushButton('Add a keybind')
        self.add_row_button.setStyleSheet(ADD_ROW_BUTTON_DEFAULT)
        self.add_row_button.setMinimumHeight(30)
        self.add_row_button.setFixedWidth(245)
        self.add_row_button.clicked.connect(self._add_row)
        layout.addWidget(self.add_row_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.setLayout(layout)
        self.row_added = False
        global user_editing_signal
        user_editing_signal.connect(self._user_editing_update)

    def _user_editing_update(self, is_editing: bool):
        self.add_row_button.setDisabled(is_editing)

    @cached_property
    def _stacked_widget(self):
        return QVBoxLayout()

    def _after_new_row_set(self):
        self.row_added = False
        self.add_row_button.show()
        self.after_set_callback()

    def _add_row(self):
        global user_editing_signal
        self.row_added = True
        user_editing_signal.emit(True)
        new_setter_row = KeybindSetter(self.bind_name, self._stacked_widget.count(), self._after_new_row_set)
        self._stacked_widget.addWidget(
            new_setter_row
        )
        self.add_row_button.hide()
        new_setter_row.select()


class ExponentialSlider(QSlider):

    slider_values = [1, 2, 3, 4, 5, 10, 20, 30, 40, 50]
    smoothing_factor = 2.75
    base = 1.03
    offset = -2.7

    def __init__(self, minimum, maximum, interval):
        super().__init__(Qt.Orientation.Horizontal)
        self.setFixedHeight(50)
        self.valueChanged.connect(self.test)
        self.min = minimum
        self.max = maximum
        self.interval = interval

    def lin_to_exp(self, value):
        return self.smoothing_factor * math.pow(self.base, value) + self.offset

    def test(self, value):
        print(f'Slider: {value} -> {self.lin_to_exp(value)} -> {round(self.lin_to_exp(value))}')

    def should_print_tick_value(self, value):
        for test_val in self.slider_values:
            if math.fabs(value - test_val) < (value / 51):
                return True
        return False
    def paintEvent(self, ev, QPaintEvent=None):
        super().paintEvent(ev)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.white))

        rect: QRect = self.geometry()
        num_ticks = 100
        font_metrics = QFontMetrics(self.font())

        font_height = font_metrics.height()
        adjusted_width = rect.width() * 0.9
        x_offset = 10
        for i in range(100):
            next_tick_value = self.lin_to_exp(i)
            if self.should_print_tick_value(next_tick_value):
                tick_num = self.min + (self.interval * i)
                tick_x = ((rect.width() / num_ticks) * i) - (font_metrics.boundingRect(str(tick_num)).width() / 2) + x_offset
                tick_y = rect.height() - font_height * 2.5

                painter.drawText(QPoint(int(tick_x), int(tick_y)), str(round(next_tick_value)))

        painter.drawRect(rect)


class VolumeTargetSelector(QWidget):

    def __init__(self,
                 state_changed_callback: Callable[[generalutils.ControlTarget], None],
                 starting_value: generalutils.ControlTarget):
        super().__init__()
        self.layout = QHBoxLayout()
        self.state_changed_callback = state_changed_callback
        self.starting_value = starting_value
        self.all_buttons = []
        self._add_button('System', generalutils.ControlTarget.SYSTEM)
        self._add_button('Application', generalutils.ControlTarget.CURRENT_APPLICATION)
        self.setLayout(self.layout)

    def _add_button(self, text: str, control_target: generalutils.ControlTarget):
        button = QPushButton(text)
        button.clicked.connect(lambda: self._button_selection(button, control_target))
        button.setCheckable(True)
        if control_target == self.starting_value:
            button.setChecked(True)
        self.all_buttons.append(button)
        self.layout.addWidget(button)

    def _button_selection(self, pressed_button: QPushButton, control_target: generalutils.ControlTarget):
        for button in self.all_buttons:
            if button is not pressed_button:
                button.setChecked(False)
                self.state_changed_callback(control_target)


class KeyLogger(QWidget):
    key_added_signal = pyqtSignal(object)
    key_removed_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.text_block = QPlainTextEdit()
        self.text_block.zoomIn(2)
        self.text_block.setMaximumBlockCount(20)
        self.text_block.setReadOnly(True)
        layout.addWidget(self.text_block)
        self.logging = False
        self.button = QPushButton('Start Log')
        self.button.clicked.connect(self._toggle_key_logger)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.key_added_signal.connect(self._press_key)
        self.key_removed_signal.connect(self._release_key)
        self.key_listener = keyboard.Listener(on_press=lambda k: self.key_added_signal.emit(k),
                                              on_release=lambda k: self.key_removed_signal.emit(k),
                                              suppress=True)

    def _toggle_key_logger(self):
        self.logging = not self.logging
        if self.logging:
            self.button.setText('Stop Log')
            self.key_listener.start()
        else:
            self.button.setText('Start Log')
            self.key_listener.stop()

    def _key_as_log(self, key: [Key | KeyCode], pressed: bool):
        return (f'{"Pressed" if pressed else "Released"}: [{keybindutils.stringify_key(key)}], '
                f'Code: [{keybindutils.get_virtual_key_code(key)}]')

    def _press_key(self, key: [Key | KeyCode]):
        self.text_block.appendPlainText(self._key_as_log(key, True))

    def _release_key(self, key: [Key | KeyCode]):
        self.text_block.appendPlainText(self._key_as_log(key, False))


class Line(QFrame):

    def __init__(self, horizontal: bool = True):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class OptionsWindow(QWidget):

    def __init__(self,
                 volume_up_keybind_name: str,
                 volume_down_keybind_name: str,
                 restart_listeners_callback: Callable,
                 volume_tick_change_callback: Callable,
                 volume_target_change_callback: Callable[[generalutils.ControlTarget], None],
                 volume_tick: int,
                 control_target: generalutils.ControlTarget):
        super().__init__()
        self.setWindowTitle('Options')
        self.setAutoFillBackground(False)
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)
        root_layout = QVBoxLayout()
        self.volume_tick_selector = VolumeTickSelector(
            change_callback=volume_tick_change_callback,
            starting_value=volume_tick
        )
        root_layout.addWidget(self.volume_tick_selector)
        self.volume_test = ExponentialSlider(0, 50, 2)
        root_layout.addWidget(self.volume_test)
        self.volume_target_selector = VolumeTargetSelector(
            state_changed_callback=volume_target_change_callback,
            starting_value=control_target
        )
        root_layout.addWidget(self.volume_target_selector)
        root_layout.addWidget(Line())
        volume_inputs_layout = QHBoxLayout()
        volume_up_inputs = ExtendableKeybindSetterList(
            'Volume Up',
            volume_up_keybind_name,
            restart_listeners_callback)
        volume_inputs_layout.addWidget(volume_up_inputs)
        volume_inputs_layout.addWidget(Line(horizontal=False))
        volume_down_inputs = ExtendableKeybindSetterList(
            'Volume Down',
            volume_down_keybind_name,
            restart_listeners_callback)
        volume_inputs_layout.addWidget(volume_down_inputs)
        root_layout.addLayout(volume_inputs_layout)
        key_logger = KeyLogger()
        root_layout.addWidget(key_logger)
        self.setLayout(root_layout)
        self.setGeometry(get_monitor_center(get_primary_monitor(), 100, 100))
