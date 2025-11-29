import time
from typing import MutableSet

from pynput import keyboard
from pynput.keyboard import KeyCode, Key

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


# Need to rewrite this to only allow canonical keys to be pressed, remove all modifiers
# With thanks to:
# https://medium.com/@birenmer/threading-the-needle-returning-values-from-python-threads-with-ease-ace21193c148
class KeybindCollector:

    def __init__(self):
        self.keybind = set()
        self.keybind_complete = False

    def _on_press(self, key: Key | KeyCode):
        print(f'Press: {key}')
        if not self.keybind_complete:
            if key in MODIFIER_KEYS:
                self.keybind.add(key)
            else:
                self.keybind.add(key)
                self.keybind_complete = True

    def _on_release(self, key: Key | KeyCode):
        print(f'Release: {key}')
        self.keybind.discard(key)

    def _listen_for_keybind(self):
        listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, suppress=True)
        listener.start()
        while not self.keybind_complete:
            time.sleep(.01)
            pass
        listener.stop()
        return self.keybind

    def _get_vk(self, key: Key | KeyCode):
        return key.vk if hasattr(key, 'vk') else key.value.vk

    def collect_keybind(self) -> MutableSet[Key | KeyCode]:
        """
        Thread Blocking call that returns the user-specified keybind once they have provided one
        :return: A set of Keys specifying a keybind (e.g. {'G', <Key.shift: <65505>>, <Key.ctrl: <65507>>})
        """
        keybind_collection_thread = ReturningThread(target=self._listen_for_keybind)
        keybind_collection_thread.start()
        return keybind_collection_thread.join()

    def save_keybind(self, filename: str):
        with open(filename, mode="wt") as file:
            for key in self.keybind:
                file.write(str(self._get_vk(key)) + '\n')


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
