import pynput as pyin
from pynput.keyboard import KeyCode, Key, Controller

keyboard = Controller()


def key_pressed(event: Key | KeyCode):
    print(f'Pressed: {event}')
    if event == Key.esc:
        keyboard.press(Key.shift)
        keyboard.press(Key.alt)
        keyboard.release(Key.shift)
        keyboard.release(Key.alt)


def key_released(event):
    print(f'Released: {event}')


def mouse_pressed(x, y, button, pressed):
    print(f'Pressed: {button}')


with pyin.mouse.Listener(on_click=mouse_pressed) as l:
    l.join()

with pyin.keyboard.Listener(on_press=key_pressed, on_release=key_released, suppress=True) as l:
    l.join()
