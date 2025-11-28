import threading
import time

from pynput import keyboard
from pynput.keyboard import KeyCode, Key

MODIFIER_KEYS = (
    # Key.ctrl_l,
    # Key.ctrl_r,
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


class KeybindCollector:

    def __init__(self):
        self.keybind = set()
        self.keybind_complete = False

    def on_press(self, key: Key | KeyCode):
        if not self.keybind_complete:
            if key in MODIFIER_KEYS:
                self.keybind.add(key)
            else:
                self.keybind.add(key)
                self.keybind_complete = True

    def _listen_for_keybind(self):
        listener = keyboard.Listener(on_press=self.on_press).start()
        while not self.keybind_complete:
            time.sleep(.1)
            pass
        return self.keybind

    def collect_keybind(self):
        return threading.Thread(target=self._listen_for_keybind).start().join()


collector = KeybindCollector()
collector.collect_keybind()
print(f'Collected keybind: {collector.keybind}')


