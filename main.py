import sys

import yaml
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from pynput import keyboard

import fileutils
import keybindhandlersv2 as kb2
import ui
import volumeutils
from keybindhandlers import load_keybind_from_file, DEFAULT_UP_BINDING, DEFAULT_DOWN_BINDING, FunctionBinding, \
    KeybindListener

config_filename = 'config.yml'


def load_configs(filename: str):
    with fileutils.open_resource(filename) as config_file:
        config = yaml.safe_load(config_file)
        volume = config['volume']
        control = config['control']
        ui = config['ui']
    return volume, control, ui


def update_volume_config(tick_value: float):
    with fileutils.open_resource(config_filename) as config_file:
        config = yaml.safe_load(config_file)
        config['volume']['delta'] = tick_value
    with fileutils.open_resource(config_filename, "w") as config_file:
        yaml.safe_dump(config, config_file)
        print(f'Update volume tick to: {config["volume"]["delta"]}')
    refresh_config()


# Constants
idle_time = 3

# Configs, flags and trackers
modifier_key = keyboard.Key.shift
modifier_key_pressed = False
terminate_application = False
(volume_config, control_config, ui_config) = load_configs(config_filename)


def refresh_config():
    global volume_config, control_config, ui_config
    (volume_config, control_config, ui_config) = load_configs(config_filename)


# Bindings
volume_up_keybind_name = 'volume_up'
volume_down_keybind_name = 'volume_down'

saved_up_binding = load_keybind_from_file(volume_up_keybind_name)
saved_down_binding = load_keybind_from_file(volume_down_keybind_name)

initial_up_binding = DEFAULT_UP_BINDING if saved_up_binding is None else saved_up_binding
initial_down_binding = DEFAULT_DOWN_BINDING if saved_down_binding is None else saved_down_binding

listener: KeybindListener


# Change the volume of a target. Not sure if more targets might be available in future (e.g. Comms only)
def volume_change(delta: float):
    control_target = control_config['target']
    if control_target == 'current_application':
        updated_volume, media_name = volumeutils.change_active_window_volume(delta)
    elif control_target == 'system':
        updated_volume, media_name = volumeutils.change_system_volume(delta)
    else:
        # TODO: What should we do?
        #  Call itself again and provide a better config? Set the config in the file to a default? Nothing and break?
        raise ValueError(f'Unknown Control Target Configuration: {control_target}')
    # print('Updated volume: ' + str(updated_volume))
    if updated_volume is not None:
        volume_bar.set_percentage(round(updated_volume * 100), media_name)
        gui_app.processEvents()


def volume_up():
    print('Volume Up')
    delta = float(volume_config['delta'])
    volume_change(delta)


def volume_down():
    print('Volume Down')
    delta = float(volume_config['delta'])
    volume_change(-delta)


def volume_bar_alert(text: str):
    volume_bar.set_error(text)


def startup_keybind_listener():
    global listener
    up_binding = load_keybind_from_file(volume_up_keybind_name)
    down_binding = load_keybind_from_file(volume_down_keybind_name)

    if up_binding is None:
        up_binding = DEFAULT_UP_BINDING
    if down_binding is None:
        down_binding = DEFAULT_DOWN_BINDING

    volume_up_binding = FunctionBinding(up_binding, volume_up)
    volume_down_binding = FunctionBinding(down_binding, volume_down)

    listener = KeybindListener([
        volume_up_binding,
        volume_down_binding
    ], volume_bar_alert)
    listener.start()


def startup_keybind_listener_v2():
    global listener_v2
    up_bindings = kb2.load_bind('volume_up')
    down_bindings = kb2.load_bind('volume_down')



def restart_keybind_listener():
    listener.stop()
    startup_keybind_listener()


def stop_keybind_listener():
    listener.stop()


startup_keybind_listener()

# GUI Setup
gui_app = QApplication(sys.argv)
gui_app.setQuitOnLastWindowClosed(False)
volume_bar = ui.VolumeBar(10)
volume_bar.hide()
options_menu = ui.OptionsWindow(
    volume_up_keybind_name,
    volume_down_keybind_name,
    restart_listeners_callback=restart_keybind_listener,
    volume_tick_change_callback=update_volume_config,
    volume_tick=int(float(volume_config['delta']) * 100)
)

tray = QSystemTrayIcon()
tray_icon = QIcon(fileutils.get_full_resource_path('volume_white.png'))
tray.setIcon(tray_icon)
tray.setVisible(True)

menu = QMenu()
open_action = QAction('Open')
open_action.triggered.connect(options_menu.show)
open_action.triggered.connect(stop_keybind_listener)
menu.addAction(open_action)

quit_action = QAction('Quit')
quit_action.triggered.connect(gui_app.quit)
menu.addAction(quit_action)

tray.setContextMenu(menu)

options_menu.show()

gui_app.exec()
