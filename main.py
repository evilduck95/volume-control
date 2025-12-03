import sys

import yaml
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from pynput import keyboard

import ui
import volumeutils
from keybindhandlers import load_keybind_from_file, DEFAULT_UP_BINDING, DEFAULT_DOWN_BINDING, FunctionBinding, \
    KeybindListener


def load_configs(filename: str):
    with open(filename) as config_file:
        config = yaml.safe_load(config_file)
        volume = config['volume']
        control = config['control']
        ui = config['ui']
    return volume, control, ui


# Constants
idle_time = 3

# Configs, flags and trackers
modifier_key = keyboard.Key.shift
modifier_key_pressed = False
terminate_application = False
(volume_config, control_config, ui_config) = load_configs('config.yml')

# Bindings
volume_up_keybind_file = 'volume_up.kbd'
volume_down_keybind_file = 'volume_down.kbd'

saved_up_binding = load_keybind_from_file(volume_up_keybind_file)
saved_down_binding = load_keybind_from_file(volume_down_keybind_file)

initial_up_binding = DEFAULT_UP_BINDING if saved_up_binding is None else saved_up_binding
initial_down_binding = DEFAULT_DOWN_BINDING if saved_down_binding is None else saved_down_binding

listener: KeybindListener


def active_app_volume_change(delta: float):
    updated_volume = volumeutils.change_active_window_volume(delta)
    # print('Updated volume: ' + str(updated_volume))
    if updated_volume is not None:
        volume_bar.set_percentage(round(updated_volume * 100))
        gui_app.processEvents()


def active_app_volume_up():
    print('Vol UP')
    delta = float(volume_config['delta'])
    active_app_volume_change(delta)


def active_app_volume_down():
    print('Vol DOWN')
    delta = float(volume_config['delta'])
    active_app_volume_change(-delta)


def startup_keybind_listener():
    global listener
    up_binding = load_keybind_from_file(volume_up_keybind_file)
    down_binding = load_keybind_from_file(volume_down_keybind_file)
    volume_up_binding = FunctionBinding(up_binding, active_app_volume_up)
    volume_down_binding = FunctionBinding(down_binding, active_app_volume_down)

    listener = KeybindListener([
        volume_up_binding,
        volume_down_binding
    ])
    listener.start()


def restart_keybind_listener():
    listener.stop()
    startup_keybind_listener()


startup_keybind_listener()

# GUI Setup
gui_app = QApplication(sys.argv)
gui_app.setQuitOnLastWindowClosed(False)
volume_bar = ui.VolumeBar(2)
volume_bar.hide()
options_menu = ui.OptionsWindow(
    volume_up_keybind_file,
    volume_down_keybind_file,
    initial_up_binding,
    initial_down_binding,
    restart_keybind_listener
)

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
