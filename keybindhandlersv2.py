import pickle
import typing
from typing import Callable

from pynput import keyboard
from pynput.keyboard import KeyCode, Key
from pynput.mouse import Button

import fileutils
import generalutils
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


class SerializableButton(SerializableKey):

    def __init__(self, code: int, name: str):
        super().__init__(code, name, False)


class Binding:

    def __init__(self, keys: list[SerializableKey], mouse_button: [SerializableButton | None] = None):
        self.__keys = keys
        self.key_codes: set[int] = set([key.code for key in keys])
        self.__mouse_button = mouse_button

    def is_active(self, keys_pressed: set[Key | KeyCode], mouse_button_pressed: [Button | None] = None):
        pressed_key_codes = keybindutils.convert_to_vks(keys_pressed)
        all_keys_pressed = pressed_key_codes == self.key_codes
        if mouse_button_pressed is None:
            return all_keys_pressed
        else:
            return all_keys_pressed and mouse_button_pressed.value == self.__mouse_button.code

    @property
    def keys(self):
        return self.__keys

    @property
    def mouse_button(self):
        return self.__mouse_button


class BoundAction:

    def __init__(self, bindings: list[Binding], name: str, action: Callable = generalutils.noop_func):
        self.__bindings = bindings
        self.__name = name
        self.__action = action

    def try_trigger_with(self, keys: set[Key | KeyCode]):
        for binding in self.bindings:
            if binding.is_active(keys):
                self.action()

    @property
    def bindings(self):
        return self.__bindings

    @property
    def name(self):
        return self.__name

    @property
    def action(self):
        return self.__action

    @action.setter
    def action(self, action):
        self.__action = action

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_BoundAction__action']
        return state


class KeybindCollector:

    def __init__(self):
        self.key_listener = keyboard.Listener(on_press=self._key_pressed, suppress=True)
        self.modifiers_pressed: set[Key | KeyCode] = set()
        self.terminal_key: [Key | KeyCode]

    def _key_pressed(self, key: [Key | KeyCode]):
        if not keybindutils.is_modifier_key(key):
            self.terminal_key = key
            self.key_listener.stop()
        else:
            self.modifiers_pressed.add(key)

    def _key_released(self, key: [Key | KeyCode]):
        if key in self.modifiers_pressed:
            self.modifiers_pressed.remove(key)
        else:
            print(f'Unknown key: {key} released, cleared all keys')
            self.modifiers_pressed.clear()

    def collect_keybind(self):
        with self.key_listener as listener:
            listener.join()
        print(f'Collected\n Modifiers: {self.modifiers_pressed}, Terminator: {self.terminal_key}')
        return self.modifiers_pressed, self.terminal_key


class KeybindListener:

    def __init__(self, bound_actions: list[BoundAction]):
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


def save_bind(bound_action: BoundAction):
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
#
while True:
    pass
