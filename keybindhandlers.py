import time
from enum import Enum
from typing import Iterable, Callable

from pynput import keyboard, mouse
from pynput.keyboard import KeyCode, Key
from pynput.mouse import Button

import fileutils
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
    Key.cmd_l,
    Key.cmd_r,
    Key.cmd,
    Key.menu
)

noop = lambda *a, **k: None


def get_virtual_key_code(key: Key | KeyCode | Button):
    if type(key) is Button:
        return key.value
    else:
        return key.vk if hasattr(key, 'vk') else key.value.vk


def convert_to_vks(keys: Iterable[Key | KeyCode]):
    return set([get_virtual_key_code(key) for key in keys])


def get_key_name(key: Key | KeyCode):
    name = key.name if hasattr(key, 'name') else key.char
    return name.capitalize()


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


def compare_non_null(a, b):
    return a is not None and a == b


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


class ScrollAction(Enum):
    UP = '<ScrollUp>'

    DOWN = '<ScrollDown>'

    NONE = '<None>'

    @staticmethod
    def for_value(value):
        if value == ScrollAction.UP.value:
            return ScrollAction.UP
        else:
            return ScrollAction.DOWN


class Binding:

    def __init__(self, modifier_keys: set[Key | KeyCode],
                 bound_key: [Key | KeyCode | None],
                 bound_scroll: [ScrollAction] = ScrollAction.NONE):
        # Raw Keys
        self.__modifier_keys: set[Key | KeyCode] = modifier_keys
        self.__bound_key: [Key | KeyCode] = bound_key

        # Key Codes only for logic
        self.__modifier_codes: set[int] = convert_to_vks(modifier_keys)
        self.__bound_key_code: int = get_virtual_key_code(bound_key) if bound_key is not None else None

        # Scroll Value
        self.__bound_scroll: ScrollAction = bound_scroll

        # Internal State
        self.__key_codes_missing: bool = (any(get_virtual_key_code(key) in [None, 0] for key in modifier_keys) or
                                          bound_key is None or
                                          get_virtual_key_code(bound_key) in [None, 0])

    def is_activated(self, keys_pressed: set[Key | KeyCode | Button], scroll_action=None):
        # Check if all of our wanted modifiers are a part of the set of pressed keys
        pressed_codes = convert_to_vks(keys_pressed)
        modifiers_pressed = self.__modifier_codes.issubset(pressed_codes)
        # Check if we're using a mouse scroll wheel based bind
        action_binding_pressed: bool
        if self.is_scroll_based():
            action_binding_pressed = scroll_action == self.__bound_scroll
            return modifiers_pressed and action_binding_pressed and len(keys_pressed) == len(self.__modifier_codes)
        else:
            action_binding_pressed = self.__bound_key_code in pressed_codes
            return modifiers_pressed and action_binding_pressed and len(keys_pressed) == len(self.__modifier_codes) + 1

    def is_scroll_based(self):
        return self.__bound_scroll is not None

    def has_mouse_buttons(self):
        return key_is_mouse_button(self.__bound_key) or any(key_is_mouse_button(k) for k in self.__modifier_keys)

    @property
    def modifiers(self) -> set[Key | KeyCode]:
        return self.__modifier_keys

    @property
    def bound_key(self) -> [Key | KeyCode]:
        return self.__bound_key

    @property
    def bound_scroll(self) -> ScrollAction:
        return self.__bound_scroll


class FunctionBinding:

    def __init__(self, binding: Binding, callback: Callable):
        self.__binding = binding
        self.__callback = callback

    @property
    def binding(self) -> Binding:
        return self.__binding

    @property
    def callback(self) -> Callable:
        return self.__callback


class SavedKey:

    def __init__(self, vk: int, name: str):
        self.__vk = vk
        self.__name = name

    @property
    def vk(self):
        return self.__vk

    @property
    def name(self):
        return self.__name


class SavedKeybind(Binding):

    def __init__(self, modifier_keys: set[SavedKey],
                 bound_key: [SavedKey | None],
                 bound_scroll: [ScrollAction] = ScrollAction.NONE):
        raw_bound_key: [KeyCode | None] = None
        if bound_key is not None:
            raw_bound_key = KeyCode(vk=bound_key.vk, char=bound_key.name)
        super().__init__(
            set([KeyCode.from_vk(key.vk) for key in modifier_keys]),
            raw_bound_key,
            bound_scroll
        )
        self.__saved_modifier_names = [key.name for key in modifier_keys]
        self.__saved_bound_key_name = None if bound_key is None else bound_key.name

    @property
    def saved_modifiers(self):
        return self.__saved_modifier_names

    @property
    def saved_bound_key(self):
        return self.__saved_bound_key_name


# TODO: Reads the file ok right now.
#  Feels a bit raw atm and could probably do with some centralised ruling
def load_keybind_from_file(filename: str):
    modifiers: set[SavedKey] = set()
    key: [SavedKey | None] = None
    scroll: [ScrollAction | None] = None
    if not fileutils.does_resource_exist(filename):
        print(f'Keybind file: {filename} not found, skipping...')
        return
    try:
        with fileutils.open_resource(filename, 'rt') as file:
            section = ''
            for line in file:
                value = line.replace('\n', '').strip().split(':')
                if value[0] in ('modifiers', 'key', 'mouse_button', 'scroll'):
                    section = value[0]
                else:
                    if section == 'modifiers':
                        modifiers.add(SavedKey(int(value[0]), value[1]))
                        # modifiers.add(KeyCode.from_vk(int(value[0])))
                    elif section == 'key':
                        key = SavedKey(int(value[0]), value[1])
                        # key = KeyCode.from_vk(int(value[0]))
                    elif section == 'mouse_button':
                        key = SavedKey(int(value[0]), f'mouse_{value[1]}')
                    elif section == 'scroll':
                        scroll = ScrollAction.for_value(value[0])
        return SavedKeybind(
            modifiers,
            key,
            scroll
        )
    except FileNotFoundError:
        return None


class KeybindCollector:

    def __init__(self):
        self.keybind_modifiers = set()
        self.bound_key: Key | KeyCode | Button = None
        self.bound_scroll: ScrollAction = None
        self.keybind_complete = False
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=True
        )
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_press,
            on_scroll=self._on_mouse_scroll
        )

    def _on_mouse_press(self, _x, _y, button: Button, pressed):
        # Don't allow binding normal mouse buttons (Pure madness)
        if button in [Button.left, Button.right]:
            return
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
        # print(f'Press: {key}')
        if not self.keybind_complete:
            if key in MODIFIER_KEYS:
                self.keybind_modifiers.add(key)
            else:
                self.bound_key = key
                self.keybind_complete = True

    def _on_release(self, key: Key | KeyCode):
        # print(f'Release: {key}')
        self.keybind_modifiers.discard(key)

    # TODO: This might make the keybind files juuuust a little bit clearer if we use it
    #  I haven't decided if I think it's worth it yet
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

    def collect_keybind(self) -> Binding:
        """
        Thread Blocking call that returns the user-specified keybind once they have provided one
        :return: A set of Keys specifying a keybind e.g. {'G', <Key.shift: <65505>>, <Key.ctrl: <65507>>}
        FYI: Your key *codes* may differ
        """
        bind_collection_thread = ReturningThread(target=self._listen_for_bind)
        bind_collection_thread.start()
        return bind_collection_thread.join()

    def save_keybind(self, filename: str):
        print(f'Saving bind to file: {filename}')
        with fileutils.open_resource(filename, mode="w+") as file:
            file.write('modifiers\n')
            for key in self.keybind_modifiers:
                file.write(f'{str(get_virtual_key_code(key))}:{stringify_key(key)}\n')
            if self.bound_key is not None:
                if type(self.bound_key) is Button:
                    file.write('mouse_button\n')
                else:
                    file.write('key\n')
                file.write(f'{str(get_virtual_key_code(self.bound_key))}:{stringify_key(self.bound_key)}')
            elif self.bound_scroll is not None:
                file.write('scroll\n')
                file.write(str(self.bound_scroll.value))


class KeybindListener:

    def __init__(self, function_bindings: list[FunctionBinding]):
        self.function_bindings = function_bindings
        self.keys_pressed: set[Key | KeyCode] = set()
        self.keyboard_listener: keyboard.Listener = keyboard.Listener(
            on_press=self._for_canonical(self._key_pressed),
            on_release=self._for_canonical(
                self._key_released),
            daemon=True)
        self.mouse_listener: mouse.Listener = mouse.Listener(
            on_scroll=self._mouse_scrolled,
            on_click=self._mouse_clicked,
            daemon=True)
        for binding in [fb.binding for fb in function_bindings]:
            if hasattr(binding, 'saved_modifiers'):
                print(f'Loaded keybind: {binding.saved_modifiers}, {binding.saved_bound_key}, {binding.bound_scroll}')

    # Callback if our binding is satisfied
    def _check_and_activate_keybind(self, scroll=None):
        for function_binding in self.function_bindings:
            if function_binding.binding.is_activated(self.keys_pressed, scroll):
                print('Keybind activated')
                function_binding.callback()
                return

    def _for_canonical(self, func):
        return lambda key: func(self.keyboard_listener.canonical(key))

    def _key_pressed(self, key: Key | KeyCode):
        print(f'Key: {key}')
        self.keys_pressed.add(key)
        self._check_and_activate_keybind()

    def _key_released(self, key: Key | KeyCode):
        print(f'Released: {key}\n')
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
        else:
            # TODO: Need to notify the user of when this happens until I get a better Keyboard listener library
            print(f'Unknown key: {key} lifted, releasing all modifiers')
            self.keys_pressed.clear()

    def _mouse_scrolled(self, _x, _y, _dx, dy):
        mouse_scroll = ScrollAction.DOWN if dy < 0 else ScrollAction.UP
        print(f'Mouse Scrolled: {mouse_scroll}, {dy}')
        self._check_and_activate_keybind(mouse_scroll)

    def _mouse_clicked(self, _x, _y, button, pressed):
        if button not in (Button.left, Button.right):
            if pressed:
                self.keys_pressed.add(button)
                self._check_and_activate_keybind()
            else:
                self.keys_pressed.discard(button)

    def start(self):
        print('Starting Keyboard listener')
        self.keyboard_listener.start()
        # Only listen for mouse events if we bound a scroll action or mouse button
        all_bindings = [fb.binding for fb in self.function_bindings]
        if any(binding.is_scroll_based() or binding.has_mouse_buttons() for binding in all_bindings):
            print('Starting Mouse listener')
            self.mouse_listener.start()

    def stop(self):
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        print('Stopped Keybind listener')


MOCK_CTRL = SavedKey(vk=0, name='ctrl')
MOCK_SHIFT = SavedKey(vk=0, name='shift')

DEFAULT_UP_BINDING = SavedKeybind(
    modifier_keys={MOCK_CTRL, MOCK_SHIFT},
    bound_key=None,
    bound_scroll=ScrollAction.UP)
DEFAULT_DOWN_BINDING = SavedKeybind(
    modifier_keys={MOCK_CTRL, MOCK_SHIFT},
    bound_key=None,
    bound_scroll=ScrollAction.DOWN)

# collector = KeybindCollector()
# keybind = collector.collect_keybind()
# collector.save_keybind('keybind.kbd')
# print(f'Collected keybind: {keybind}')

# saved_up_binding = load_keybind_from_file('volume_up.kbd')
# saved_down_binding = load_keybind_from_file('volume_down.kbd')
#
# up_binding = DEFAULT_UP_BINDING if saved_up_binding is None else saved_up_binding
# down_binding = DEFAULT_DOWN_BINDING if saved_down_binding is None else saved_down_binding
#
#
# def up():
#     print('up')
#
#
# def down():
#     print('down')
#
#
# all_bindings = [
#     FunctionBinding(up_binding, up),
#     FunctionBinding(down_binding, down),
# ]
#
# listener = KeybindListener(all_bindings)
# listener.start()
#
# while True:
#     pass
