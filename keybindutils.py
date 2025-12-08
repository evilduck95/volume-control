from typing import Iterable

from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

MODIFIER_KEYS = {
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
    Key.cmd
}


def get_virtual_key_code(key: Key | KeyCode | Button):
    if type(key) is Button:
        return key.value
    else:
        return key.vk if hasattr(key, 'vk') else key.value.vk


MODIFIER_KEY_CODES = set(get_virtual_key_code(key) for key in Key)


def convert_to_vks(keys: Iterable[Key | KeyCode]):
    return set([get_virtual_key_code(key) for key in keys])


def get_key_name(key: Key | KeyCode):
    name = key.name if hasattr(key, 'name') else key.char
    return name.capitalize()


def is_modifier_key(key: [Key | KeyCode]):
    if get_virtual_key_code(key) in MODIFIER_KEY_CODES:
        return True
    elif not hasattr(key, 'name') and key.char is None:
        return True


def is_default_keybind(keys_pressed):
    return {Key.shift, Key.ctrl}.issubset(keys_pressed)


def key_is_mouse_button(key: [Key | KeyCode]) -> bool:
    if type(key) is Button:
        return True
    else:
        if hasattr(key, 'char') and key.char is not None:
            return key.char.startswith('mouse')
        else:
            return False


def stringify_key(key: Key | KeyCode | Button) -> str:
    key_string: str
    if type(key) is Button:
        name = key.name
        key_string = str(key.value) if name is None else name
    else:
        if hasattr(key, 'char'):
            char = key.char
            key_string = str(key.vk) if char is None else char
        else:
            key_name = key.name
            key_string = str(key.value.vk) if key_name is None else key_name
    return key_string


def are_same_keys(
        key_a: [Key | KeyCode | Button],
        key_b: [Key | KeyCode | Button]) -> bool:
    # Both are Mouse Buttons
    if type(key_a) is Button and type(key_b) is Button:
        return compare_non_null(key_a.name, key_b.name) or compare_non_null(key_a.value, key_b.value)
    else:
        # Get virtual key to best of ability and compare the value
        key_a_vk = key_a.vk if hasattr(key_a, 'vk') else key_a.value.vk
        key_b_vk = key_b.vk if hasattr(key_b, 'vk') else key_b.value.vk
        return compare_non_null(key_a_vk, key_b_vk)
