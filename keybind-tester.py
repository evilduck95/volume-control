from pynput.keyboard import Key, Listener
import sys

print("\nPress Esc to exit\n")
print(f'{"form":<10}{"char":<10}{"val":>4}{"code":>8}')
print(f'{"----":<10}{"----":<10}{"---":>4}{"----":>8}')

lastkey = ""
def on_press(key):
    global lastkey
    if hasattr(key, 'char'):
        form = "char"
        char = key.char
        if char is None:
            char = val = ""
        else:
            val = ord(char)
        code = key.vk
        lastkey = ""
    else:
        form = "other"
        char = key.name
        val = ""
        code = key.value.vk
    if lastkey != key:
        print(f"{form:<10}{char:<10}{val:>4}{code:>8}")
    lastkey = key
    if key == Key.esc:
        sys.exit()

with Listener(on_press=on_press, suppress=True) as listener:
    listener.join()