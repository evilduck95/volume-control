from pynput import keyboard
from pynput.keyboard import Key, KeyCode


pressed_vks = set()


def get_vk(key: Key | KeyCode):
    return key.vk if hasattr(key, 'vk') else key.value.vk


def on_press(key: Key | KeyCode):
    vk = get_vk(key)
    pressed_vks.add(vk)
    print(str(pressed_vks))


def on_release(key: Key | KeyCode):
    vk = get_vk(key)
    pressed_vks.remove(vk)
    print(str(pressed_vks))


with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
