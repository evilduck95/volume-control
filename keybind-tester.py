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


def on_press_2(key):
    global last_key
    if key == last_key:
        print(f'Key: {key} is the same as last:  {last_key}')
    else:
        print(f'Key: {key}')
    last_key = KeyCode.from_vk(key.vk)


with Listener(on_press=on_press_2, suppress=True) as listener:
    listener.join()
