import os.path
import time
from enum import Enum
from typing import Iterable, Callable

from pynput import keyboard, mouse
from pynput.keyboard import KeyCode, Key
from pynput.mouse import Button

from customthreading import ReturningThread

MODIFIER_KEYS = (
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
    Key.cmd,
    Key.menu
)

noop = lambda *a, **k: None


def get_virtual_key_code(key: Key | KeyCode):
    return key.vk if hasattr(key, 'vk') else key.value.vk


def _convert_to_vks(keys: Iterable[Key | KeyCode]):
    return set([get_virtual_key_code(key) for key in keys])


def _get_key_name(key: Key | KeyCode):
    name = key.name if hasattr(key, 'name') else key.char
    return name.capitalize()


def _stringify_key(key: Key | KeyCode):
    vk = get_virtual_key_code(key)
    return _get_key_name(key) if vk is None else vk


class ScrollAction(Enum):
    UP = '<ScrollUp>'
    DOWN = '<ScrollDown>'
    NONE = '<None>'

    @staticmethod
    def for_value(value):
        if value == ScrollAction.UP.value:
            return ScrollAction.UP
        else:
            return ScrollAction.DOWN


class Binding:

    def __init__(self, modifier_keys: set[Key | KeyCode],
                 bound_key: [Key | KeyCode | None],
                 bound_scroll: [ScrollAction] = ScrollAction.NONE):
        # Raw Keys
        self.__modifier_keys: set[Key | KeyCode] = modifier_keys
        self.__bound_key: [Key | KeyCode] = bound_key

        # Key Codes only for logic
        self.__modifier_codes: set[int] = _convert_to_vks(modifier_keys)
        self.__bound_key_code: int = get_virtual_key_code(bound_key) if bound_key is not None else None

        # Scroll Value
        self.__bound_scroll: ScrollAction = bound_scroll

    def is_activated(self, keys_pressed: set[Key | KeyCode], scroll_action=None):
        # Check if all of our wanted modifiers are a part of the set of pressed keys
        pressed_codes = _convert_to_vks(keys_pressed)
        modifiers_pressed = self.__modifier_codes.issubset(pressed_codes)
        # Check if we're using a mouse scroll wheel based bind
        action_binding_pressed: bool
        if self.is_scroll_based():
            action_binding_pressed = scroll_action == self.__bound_scroll
        else:
            action_binding_pressed = self.__bound_key_code in pressed_codes
        return modifiers_pressed and action_binding_pressed

    def is_scroll_based(self):
        return self.__bound_scroll is not None

    @property
    def modifiers(self) -> set[Key | KeyCode]:
        return self.__modifier_keys

    @property
    def bound_key(self) -> [Key | KeyCode]:
        return self.__bound_key

    @property
    def bound_scroll(self) -> ScrollAction:
        return self.__bound_scroll


class FunctionBinding:

    def __init__(self, binding: Binding, callback: Callable):
        self.__binding = binding
        self.__callback = callback

    @property
    def binding(self) -> Binding:
        return self.__binding

    @property
    def callback(self) -> Callable:
        return self.__callback


# TODO: Reads the file ok right now.
#  Feels a bit raw atm and could probably do with some centralised ruling
def load_keybind_from_file(filename: str):
    modifiers: set[KeyCode] = set()
    key: [KeyCode | None] = None
    scroll: [ScrollAction | None] = None
    if not os.path.exists(filename):
        return
    with open(filename, 'rt') as file:
        section = ''
        for line in file:
            value = line.replace('\n', '').strip()
            if value in ('modifiers', 'key', 'scroll'):
                section = value
            else:
                if section == 'modifiers':
                    modifiers.add(KeyCode.from_vk(int(value)))
                elif section == 'key':
                    key = KeyCode.from_vk(int(value))
                elif section == 'scroll':
                    scroll = ScrollAction.for_value(value)
    return Binding(
        modifiers,
        key,
        scroll
    )


class KeybindCollector:

    def __init__(self):
        self.keybind_modifiers = set()
        self.bound_key: Key | KeyCode = None
        self.bound_scroll: ScrollAction = None
        self.keybind_complete = False
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=True
        )
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_press, on_scroll=self._on_mouse_scroll)

    def _on_mouse_press(self, _x, _y, button: Button, pressed):
        # Stops any rogue mouse release from triggering end of capture
        if pressed:
            self.bound_key = button
            self.keybind_complete = True

    def _on_mouse_scroll(self, _x, _y, _dx, dy):
        # We must have some modifiers so scrolling alone won't be bound
        if len(self.keybind_modifiers) == 0:
            return
        if dy < 0:
            self.bound_scroll = ScrollAction.DOWN
        else:
            self.bound_scroll = ScrollAction.UP
        # Scrolling is a final action like a key or mouse press
        self.keybind_complete = True

    def _on_press(self, key: Key | KeyCode):
        # print(f'Press: {key}')
        if not self.keybind_complete:
            if key in MODIFIER_KEYS:
                self.keybind_modifiers.add(key)
            else:
                self.bound_key = key
                self.keybind_complete = True

    def _on_release(self, key: Key | KeyCode):
        # print(f'Release: {key}')
        self.keybind_modifiers.discard(key)

    def _for_canonical(self, func):
        return lambda key: func(self.keyboard_listener.canonical(key))

    def _listen_for_bind(self) -> Binding:
        self.keyboard_listener.start()
        self.mouse_listener.start()
        while not self.keybind_complete:
            time.sleep(.01)
            pass
        self.keyboard_listener.stop()
        binding = Binding(self.keybind_modifiers, self.bound_key, self.bound_scroll)
        return binding

    def collect_keybind(self) -> Binding:
        """
        Thread Blocking call that returns the user-specified keybind once they have provided one
        :return: A set of Keys specifying a keybind e.g. {'G', <Key.shift: <65505>>, <Key.ctrl: <65507>>}
        FYI: Your key *codes* may differ
        """
        bind_collection_thread = ReturningThread(target=self._listen_for_bind)
        bind_collection_thread.start()
        return bind_collection_thread.join()

    def save_keybind(self, filename: str):
        with open(filename, mode="wt") as file:
            file.write('modifiers\n')
            for key in self.keybind_modifiers:
                file.write(str(_stringify_key(key)) + '\n')
            if self.bound_key is not None:
                file.write('key\n')
                file.write(str(_stringify_key(self.bound_key)))
            elif self.bound_scroll is not None:
                file.write('scroll\n')
                file.write(str(self.bound_scroll.value))


class KeybindListener:

    def __init__(self, function_bindings: list[FunctionBinding]):
        self.function_bindings = function_bindings
        self.keys_pressed: set[Key | KeyCode] = set()

    # Callback if our binding is satisfied
    def _check_and_activate_keybind(self, scroll=None):
        for function_binding in self.function_bindings:
            if function_binding.binding.is_activated(self.keys_pressed, scroll):
                function_binding.callback()

    def _key_pressed(self, key: Key | KeyCode):
        self.keys_pressed.add(key)
        self._check_and_activate_keybind()

    def _key_released(self, key: Key | KeyCode):
        self.keys_pressed.discard(key)

    def _mouse_scrolled(self, _x, _y, _dx, dy):
        mouse_scroll = ScrollAction.DOWN if dy < 0 else ScrollAction.UP
        self._check_and_activate_keybind(mouse_scroll)

    def start(self):
        keyboard.Listener(
            on_press=self._key_pressed,
            on_release=self._key_released,
            suppress=True).start()
        # Only listen for mouse events if we bound a scroll action
        if any(fb.binding.is_scroll_based() for fb in self.function_bindings):
            mouse.Listener(
                on_scroll=self._mouse_scrolled
            ).start()


DEFAULT_UP_BINDING = Binding(
    modifier_keys={Key.ctrl, Key.shift},
    bound_key=None,
    bound_scroll=ScrollAction.UP)
DEFAULT_DOWN_BINDING = Binding(
    modifier_keys={Key.ctrl, Key.shift},
    bound_key=None,
    bound_scroll=ScrollAction.DOWN)

collector = KeybindCollector()
keybind = collector.collect_keybind()
collector.save_keybind('keybind.kbd')
print(f'Collected keybind: {keybind}')

# saved_up_binding = load_keybind_from_file('volume_up.kbd')
# saved_down_binding = load_keybind_from_file('volume_down.kbd')
#
# up_binding = DEFAULT_UP_BINDING if saved_up_binding is None else saved_up_binding
# down_binding = DEFAULT_DOWN_BINDING if saved_down_binding is None else saved_down_binding
#
#
# def up():
#     print('up')
#
#
# def down():
#     print('down')
#
#
# all_bindings = [
#     FunctionBinding(up_binding, up),
#     FunctionBinding(down_binding, down),
# ]
#
# listener = KeybindListener(all_bindings)
# listener.start()
#
# while True:
#     pass
