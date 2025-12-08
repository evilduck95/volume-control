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


with pyin.keyboard.Listener(on_press=key_pressed, on_release=key_released, suppress=True) as l:
    l.join()

# Something to try out
# 1. Grab all keys pressed as normal until something is released
# 2. Separate all known modifiers and keys with only a key code (Likely modifiers)
# 3. Start listener for input
# 4. Start input, press all modifiers in every combination
# 5. Listen for what inputs we receive, for instance, alt+shift != shift+alt (shift+<meta-l code>)
# 6. Reduce to distinct set of combinations
