from pynput.keyboard import Key, Listener, KeyCode
import sys

print("\nPress Esc to exit\n")
print(f'{"form":<10}{"char":<10}{"val":>4}{"code":>8}')
print(f'{"----":<10}{"----":<10}{"---":>4}{"----":>8}')

last_key = None


def on_press(key):
    global last_key
    if hasattr(key, 'char'):
        form = "char"
        char = key.char
        if char is None:
            char = val = ""
        else:
            val = ord(char)
        code = key.vk
        last_key = ""
    else:
        form = "other"
        char = key.name
        val = ""
        code = key.value.vk
    if last_key != key:
        print(f"{form:<10}{char:<10}{val:>4}{code:>8}")
    last_key = key
    if key == Key.esc:
        sys.exit()


def _stringify_key(key: Key | KeyCode):
    key_string: str
    if hasattr(key, 'char'):
        char = key.char
        key_string = str(key.vk) if char is None else char
    else:
        key_name = key.name
        key_string = key.value.vk if key_name is None else key_name
    print(f'Key String: {key_string}')


def on_press_2(key):
    _stringify_key(key)


with Listener(on_press=on_press_2, suppress=True) as listener:
    listener.join()
