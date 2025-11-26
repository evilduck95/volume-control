import math
import sys
import threading
import time

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from pynput import keyboard, mouse

import ui
import volumeutils

# Constants
idle_time = 3

# Configs, flags and trackers
modifier_key = keyboard.Key.ctrl
modifier_key_pressed = False
terminate_application = False

# GUI Setup
gui_app = QApplication(sys.argv)
gui_app.setQuitOnLastWindowClosed(False)
volume_bar = ui.VolumeBar(2)
options_menu = ui.OptionsWindow()


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

keyboard_listener: keyboard.Listener
mouse_listener: mouse.Listener


def start_input_listeners():
    global keyboard_listener, mouse_listener
    keyboard_listener = keyboard.Listener(on_press=on_key_pressed, on_release=on_key_released)
    mouse_listener = mouse.Listener(on_scroll=on_mouse_scroll)

    keyboard_listener.start()
    mouse_listener.start()


threading.Thread(target=start_input_listeners).start()

tray = QSystemTrayIcon()
tray_icon = QIcon("volume.png")
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


gui_app.exec()
