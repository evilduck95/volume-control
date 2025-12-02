import sys
import threading

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from pynput import keyboard, mouse

import ui
import volumeutils
from keybindhandlers import load_keybind_from_file, DEFAULT_UP_BINDING, DEFAULT_DOWN_BINDING

# Constants
idle_time = 3

# Configs, flags and trackers
modifier_key = keyboard.Key.shift
modifier_key_pressed = False
terminate_application = False

# Bindings
volume_up_keybind_file = 'volume_up.kbd'
volume_down_keybind_file = 'volume_down.kbd'

saved_up_binding = load_keybind_from_file('volume_up.kbd')
saved_down_binding = load_keybind_from_file('volume_down.kbd')

up_binding = DEFAULT_UP_BINDING if saved_up_binding is None else saved_up_binding
down_binding = DEFAULT_DOWN_BINDING if saved_down_binding is None else saved_down_binding

# GUI Setup
gui_app = QApplication(sys.argv)
gui_app.setQuitOnLastWindowClosed(False)
volume_bar = ui.VolumeBar(2)
# TODO: Provide filenames and current bindings so options displays current state to user
options_menu = ui.OptionsWindow(
    volume_up_keybind_file,
    volume_down_keybind_file,
    up_binding,
    down_binding
)

# TODO: Add a keybind listener in that immediately starts listening for binds
#  The listener should be updatable on the fly with new keybindings just in case we change our options
#  The files take care of persisting these between restarts

def on_key_pressed(key):
    global modifier_key_pressed, terminate_application
    # Our wanted modifier has been pressed
    if key == modifier_key:
        modifier_key_pressed = True
    elif modifier_key_pressed and key == keyboard.KeyCode(char='x'):
        terminate_application = True


def on_key_released(key):
    global modifier_key_pressed
    # The wanted modifier has been un-pressed
    if key == modifier_key:
        modifier_key_pressed = False


def on_mouse_scroll(_x, _y, _dx, dy):
    # Only allowed to listen to mouse events if we have pressed the correct modifier
    if modifier_key_pressed:
        scroll_direction = 'down' if dy < 0 else 'up'
        updated_volume = volumeutils.change_active_window_volume(-.05 if scroll_direction == 'down' else +.05)
        print('Updated volume: ' + str(updated_volume))
        if updated_volume is None:
            return
        volume_bar.set_percentage(round(updated_volume * 100))
        gui_app.processEvents()


def active_app_volume_change(delta):
    updated_volume = volumeutils.change_active_window_volume(delta)
    print('Updated volume: ' + str(updated_volume))
    if updated_volume is not None:
        volume_bar.set_percentage(round(updated_volume * 100))
        gui_app.processEvents()


# def volume_controller():
#     global volume_bar_ui
#     # Input Event Listeners
#     keyboard_listener = keyboard.Listener(on_press=on_key_pressed, on_release=on_key_released)
#     mouse_listener = mouse.Listener(on_scroll=on_mouse_scroll)
#
#     keyboard_listener.start()
#     mouse_listener.start()
#
#     # Custom loop. Don't run any blocking functions in here, so it can continuously pick up events and control the GUI.
#     print('Press ctrl + x to exit')
#     while True:
#         # Slow down updates
#         time.sleep(.1)
#         # gui_visible = ui.winfo_viewable()
#         if update_gui:
#             # if not gui_visible:
#             volume_bar_ui.event_generate("<<Show>>", when="tail")
#                 # ui.deiconify()
#             volume_bar_ui.event_generate("<<UpdateValue>>", when="tail")
#             # bar_value.set(last_set_volume)
#             # volume_bar_ui.update()
#         if time.time() - idle_instant > idle_time:
#             volume_bar_ui.event_generate("<<Hide>>", when="tail")
#             # ui.withdraw()
#         if terminate_application:
#             exit(0)

# keyboard_listener: keyboard.Listener
# mouse_listener: mouse.Listener
#
#
# def start_input_listeners():
#     global keyboard_listener, mouse_listener
#     keyboard_listener = keyboard.Listener(on_press=on_key_pressed, on_release=on_key_released)
#     mouse_listener = mouse.Listener(on_scroll=on_mouse_scroll)
#
#     keyboard_listener.start()
#     mouse_listener.start()
#
#
# threading.Thread(target=start_input_listeners).start()

tray = QSystemTrayIcon()
tray_icon = QIcon("volume_white.png")
tray.setIcon(tray_icon)
tray.setVisible(True)

menu = QMenu()
open_action = QAction("Open")
open_action.triggered.connect(options_menu.show)
menu.addAction(open_action)

quit_action = QAction("Quit")
quit_action.triggered.connect(gui_app.quit)
menu.addAction(quit_action)

tray.setContextMenu(menu)

options_menu.show()

gui_app.exec()
