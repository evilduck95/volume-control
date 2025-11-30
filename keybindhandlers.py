import time
from enum import Enum

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
    # Key.cmd_l,
    # Key.cmd_r,
    # Key.cmd,
    Key.menu
)

noop = lambda *a, **k: None


class ScrollAction(Enum):
    UP = '<ScrollUp>'
    DOWN = '<ScrollDown>'


class Binding:

    def __init__(self, modifiers: set[Key | KeyCode],
                 bound_key: [Key | KeyCode | None],
                 bound_scroll: [ScrollAction | None]):
        self.__modifiers = modifiers
        self.__bound_key = bound_key
        self.__bound_scroll = bound_scroll

    @property
    def modifiers(self):
        return self.__modifiers

    @property
    def bound_key(self):
        return self.__bound_key

    @property
    def bound_scroll(self) -> ScrollAction:
        return self.__bound_scroll


class KeybindListener:

    def __init__(self, keybind: list[KeyCode], callback=noop):
        self.keys_pressed = set()
        self.keybind = set([self._get_vk(k) for k in keybind])
        self.callback = callback

    def _check_keybind(self):
        return self.keybind.issubset(self.keys_pressed)

    def _get_vk(self, key: Key | KeyCode):
        return key.vk if hasattr(key, 'vk') else key.value.vk

    def _key_pressed(self, key):
        self.keys_pressed.add(self._get_vk(key))
        if self._check_keybind():
            self.callback()

    def _key_released(self, key):
        self.keys_pressed.discard(self._get_vk(key))

    def start(self):
        keyboard.Listener(
            on_press=self._key_pressed,
            on_release=self._key_released,
            suppress=False).start()


# With thanks to:
# https://medium.com/@birenmer/threading-the-needle-returning-values-from-python-threads-with-ease-ace21193c148
class KeybindCollector:

    def __init__(self):
        self.keybind_modifiers = set()
        self.bound_key: Key | KeyCode = None
        self.bound_scroll: ScrollAction = None
        self.keybind_complete = False
        self.keyboard_listener = keyboard.Listener(
            on_press=self._for_canonical(self._on_press),
            on_release=self._for_canonical(self._on_release),
            suppress=False
        )
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_press, on_scroll=self._on_mouse_scroll)

    # Func looked cute, might delete later
    def _valid_key(self, key: Key | KeyCode):
        return (hasattr(key, 'name') and key.name is not None) or (hasattr(key, 'char') and key.char is not None)

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
        print(f'Press: {key}')
        if not self.keybind_complete:
            if key in MODIFIER_KEYS:
                self.keybind_modifiers.add(key)
            else:
                self.bound_key = key
                self.keybind_complete = True

    def _on_release(self, key: Key | KeyCode):
        print(f'Release: {key}')
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

    def _get_vk(self, key: Key | KeyCode):
        return key.vk if hasattr(key, 'vk') else key.value.vk

    def collect_keybind(self) -> Binding:
        """
        Thread Blocking call that returns the user-specified keybind once they have provided one
        :return: A set of Keys specifying a keybind (e.g. {'G', <Key.shift: <65505>>, <Key.ctrl: <65507>>})
        """
        bind_collection_thread = ReturningThread(target=self._listen_for_bind)
        bind_collection_thread.start()
        return bind_collection_thread.join()

    def save_keybind(self, filename: str):
        with open(filename, mode="wt") as file:
            for key in self.keybind_modifiers:
                file.write(str(self._get_vk(key)) + '\n')
            if self.bound_key is not None:
                file.write(str(self._get_vk(self.bound_key)))
            elif self.bound_scroll is not None:
                file.write(str(self.bound_scroll.value))

# collector = KeybindCollector()
# keybind = collector.collect_keybind()
# collector.save_keybind('keybind')
# print(f'Collected keybind: {keybind}')
#
# keys = []
# with open('keybind', 'rt') as file:
#     for line in file:
#         key_code = line.replace('\n', '')
#         keys.append(keyboard.KeyCode.from_vk(int(key_code)))
#     print(keys)
#
#
# def woo():
#     print('woohoo')
#
#
# listener = KeybindListener(keys, woo)
# listener.start()
#
# while True:
#     pass
