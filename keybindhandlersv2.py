import pickle
import time
from enum import Enum
from typing import Callable

from pynput import keyboard, mouse
from pynput.keyboard import KeyCode, Key
from pynput.mouse import Button

import fileutils
import keybindutils

MODIFIER_KEYS = {
    Key.ctrl_l,
    Key.ctrl_r,
    Key.ctrl,

    Key.shift_l,
    Key.shift_r,
    Key.shift,

    Key.alt_gr,
    Key.alt_l,
    Key.alt_r,
    Key.alt,

    Key.cmd_l,
    Key.cmd_r,
    Key.cmd
}

MODIFIER_KEY_CODES = set(keybindutils.get_virtual_key_code(key) for key in Key)


def _convert_to_serializable_key(key: [Key | KeyCode]):
    code = keybindutils.get_virtual_key_code(key)
    name = keybindutils.get_key_name(key)
    is_modifier = keybindutils.is_modifier_key(key)
    return SerializableKey(code, name, is_modifier)


class SerializableKey:

    def __init__(self, code: int, name: str, is_modifier: bool):
        self.__code = code
        self.__name = name
        self.__is_modifier = is_modifier

    @property
    def code(self):
        return self.__code

    @property
    def name(self):
        return self.__name

    @property
    def is_modifier(self):
        return self.__is_modifier


class SerializableMouseButton(SerializableKey):

    def __init__(self, code: int, name: str):
        super().__init__(code, name, False)


class Scroll(Enum):
    DOWN = 'WheelDown'
    UP = 'WheelUp'


class SerializableMouseAction:

    def __init__(self, button: [SerializableMouseButton | None] = None, scroll: [Scroll | None] = None):
        self.__button = button
        self.__scroll = scroll

    @property
    def button(self):
        return self.__button

    @property
    def scroll(self):
        return self.__scroll

    def __str__(self):
        print('str')
        if self.button is None:
            return f'Mouse{self.scroll.value}'
        else:
            return f'Mouse{self.button.name.capitalize()}'


class Binding:

    def __init__(self, keys: list[SerializableKey], mouse_action: [SerializableMouseAction | None] = None):
        self.__keys = keys
        self.key_codes: set[int] = set([key.code for key in keys])
        self.__mouse_action: [SerializableMouseAction | None] = mouse_action

    def is_active(self, keys_pressed: set[Key | KeyCode], mouse_button_pressed: [Button | None] = None,
                  scroll: [Scroll | None] = None):
        pressed_key_codes = keybindutils.convert_to_vks(keys_pressed)
        all_keys_pressed = pressed_key_codes == self.key_codes
        if mouse_button_pressed is None and scroll is None:
            return all_keys_pressed
        else:
            mouse_action_done = (mouse_button_pressed.value == self.__mouse_action.button.code or
                                 scroll == self.__mouse_action.scroll)
            return all_keys_pressed and mouse_action_done

    @property
    def keys(self):
        return self.__keys

    @property
    def mouse_action(self):
        return self.__mouse_action

    def __str__(self):
        key_names = [key.name for key in self.keys]
        keys_pressed_string = ' + '.join(key_names)
        if self.mouse_action is None:
            return keys_pressed_string
        else:
            return f'{keys_pressed_string} + {self.mouse_action}'


class BindingGroup:

    def __init__(self, bindings: list[Binding], name: str):
        self.__bindings = bindings
        self.__name = name

    def try_trigger_with(self, keys: set[Key | KeyCode], action: Callable):
        for binding in self.bindings:
            if binding.is_active(keys):
                action()

    @property
    def bindings(self):
        return self.__bindings

    @property
    def name(self):
        return self.__name


class KeybindCollector:

    def __init__(self):
        self.key_listener = keyboard.Listener(on_press=self._key_pressed, on_release=self._key_released, suppress=True)
        self.mouse_listener = mouse.Listener(on_click=self._mouse_clicked, on_scroll=self._mouse_scrolled)
        self.modifiers_pressed: set[Key | KeyCode] = set()
        self.terminal_key: [Key | KeyCode] = None
        self.terminal_mouse_action: [Button | Scroll] = None
        self.keybind_complete = False

    def _key_pressed(self, key: [Key | KeyCode]):
        if not keybindutils.is_modifier_key(key):
            self.terminal_key = key
            self.keybind_complete = True
        else:
            self.modifiers_pressed.add(key)

    def _key_released(self, key: [Key | KeyCode]):
        if self.keybind_complete:
            return
        if key in self.modifiers_pressed:
            self.modifiers_pressed.remove(key)
        else:
            print(f'Unknown key: {key} released, cleared all keys')
            self.modifiers_pressed.clear()

    def _mouse_clicked(self, _x, _y, button: Button, pressed):
        if pressed and button not in [Button.left, Button.right]:
            self.terminal_mouse_action = button
            self.keybind_complete = True

    def _mouse_scrolled(self, _x, _y, _dx, dy):
        if dy > 0:
            self.terminal_mouse_action = Scroll.UP
        else:
            self.terminal_mouse_action = Scroll.DOWN
        self.keybind_complete = True

    def collect_keybind(self):
        self.key_listener.start()
        self.mouse_listener.start()
        while not self.keybind_complete:
            time.sleep(.1)
        self.mouse_listener.stop()
        self.key_listener.stop()
        if self.terminal_mouse_action is not None:
            if type(self.terminal_mouse_action) is Button:
                mouse_action = SerializableMouseAction(button=self.terminal_mouse_action)
            else:
                mouse_action = SerializableMouseAction(scroll=self.terminal_mouse_action)
        else:
            mouse_action = None
        all_keys = [*self.modifiers_pressed]
        print(
            f'Collected\n Modifiers: {self.modifiers_pressed}, Terminator: {self.terminal_key}, Mouse: {self.terminal_mouse_action}')
        if self.terminal_key is not None:
            all_keys.append(self.terminal_key)
        pressed_keys = [_convert_to_serializable_key(key) for key in all_keys]
        return Binding(pressed_keys, mouse_action)


class KeybindListener:

    def __init__(self, bound_actions: list[BindingGroup]):
        self.bound_actions = bound_actions
        self.key_listener = keyboard.Listener(on_press=self._key_pressed, on_release=self._key_released, suppress=True)
        self.keys_pressed = set()
        self.prev_keys_pressed = set()

    def _key_pressed(self, key: [Key | KeyCode]):
        self.keys_pressed.add(key)
        # Only activate when the number of keys pressed changes (prevent key repetition)
        if self.keys_pressed != self.prev_keys_pressed:
            self.prev_keys_pressed = self.keys_pressed.copy()
            for action in self.bound_actions:
                action.try_trigger_with(self.keys_pressed)

    def _key_released(self, key: [Key | KeyCode]):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
        else:
            print('Unknown key released, cleared all keys')
            self.keys_pressed.clear()
        self.prev_keys_pressed = self.keys_pressed.copy()

    def start(self):
        self.key_listener.start()


def get_callback(num: int) -> Callable:
    return lambda: print(f'Keybind {num} activated')


def save_bind(bound_action: BindingGroup):
    with fileutils.open_resource(f'binding_{bound_action.name}', 'wb') as save_file:
        # noinspection PyTypeChecker
        pickle.dump(bound_action, save_file, pickle.HIGHEST_PROTOCOL)


def load_bind(name: str):
    file_name = f'binding_{name}'
    if not fileutils.does_resource_exist(file_name):
        return None
    with fileutils.open_resource(file_name, 'rb') as save_file:
        # noinspection PyTypeChecker
        return pickle.load(save_file)

# with fileutils.open_resource('name', 'rb') as file:
#     test_bind_action: BoundAction = pickle.load(file)
#     test_bind_action.action = lambda: print('Woohoo')
#
#
# KeybindListener([test_bind_action]).start()

# bound_actions = []
#
# for i in range(2):
#     print(f'Collecting keybind: {i}')
#     collector = KeybindCollector()
#     modifiers_pressed, terminal_key = collector.collect_keybind()
#     binding_keys = [terminal_key, *modifiers_pressed]
#
#     binding = Binding(keys=[_convert_to_serializable_key(key) for key in binding_keys])
#     bound_actions.append(BoundAction([binding], 'name', get_callback(i)))
#
# for bound_action in bound_actions:
#     save_bind(bound_action)
#
#
# print('Listening for keybinds')
# listener = KeybindListener(bound_actions)
# listener.start()

# while True:
#     pass
