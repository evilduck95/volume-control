import sys
import threading
import time
import tkinter
from tkinter import ttk

import pystray
from PIL import Image
from pynput import keyboard, mouse
from screeninfo import screeninfo

import volumeutils
from timer import DelayedAction

# Constants
idle_time = 3

# Configs, flags and trackers
modifier_key = keyboard.Key.ctrl
modifier_key_pressed = False
update_gui = False
terminate_application = False
last_set_volume = 0
idle_instant = 0


def hide_volume_bar_delayed():
    volume_bar_ui.event_generate("<<Hide>>", when="tail")


volume_bar_hide_timer = DelayedAction(3, action=hide_volume_bar_delayed)


def on_key_pressed(key):
    global modifier_key_pressed, terminate_application
    # Our wanted modifier has been pressed
    if key == modifier_key:
        modifier_key_pressed = True
    elif modifier_key_pressed and key == keyboard.KeyCode(char='x'):
        terminate_application = True


def on_key_released(key):
    global modifier_key_pressed, update_gui
    # The wanted modifier has been un-pressed
    if key == modifier_key:
        modifier_key_pressed = False
        update_gui = False


def on_mouse_scroll(_x, _y, _dx, dy):
    global last_set_volume, idle_instant, update_gui
    # Only allowed to listen to mouse events if we have pressed the correct modifier
    if modifier_key_pressed:
        scroll_direction = 'down' if dy < 0 else 'up'
        update_gui = True
        updated_volume = volumeutils.change_active_window_volume(-.05 if scroll_direction == 'down' else +.05)
        # print('Updated volume: ' + str(updated_volume))
        last_set_volume = updated_volume
        idle_instant = time.time()
        # volume_bar_ui.event_generate("<<Show>>", when="tail")
        volume_bar_ui.event_generate("<<UpdateValue>>", when="tail")
        volume_bar_hide_timer.run()


# Everything from here onwards may have to be put on a separate thread so the tray icon and options
# window can always be on the main thread. The tray MUST be on the main thread (I'm told)

def render_volume_bar_ui(root_volume_ui, progress_bar):
    root_volume_ui.title('Volume Control')
    root_volume_ui.resizable(False, False)

    # Find primary monitor, or fallback to first. Idk if this ever fails, but it will be configured by user anyway.
    primary_monitor = next(
        filter(lambda monitor: monitor.is_primary, screeninfo.get_monitors()),
        screeninfo.get_monitors()[0]
    )
    display_monitor = primary_monitor

    # Display window in center of screen. (This will be configurable also)
    width = 400
    height = 50
    screen_width = display_monitor.width
    screen_height = display_monitor.height

    # Offset by all monitors taken as a single, large space
    x_coord = display_monitor.x + (screen_width / 2) - (width / 2)
    y_coord = display_monitor.y + (screen_height / 2) - (height / 2)

    # Place window across all monitors
    root_volume_ui.geometry('%dx%d+%d+%d' % (width, height, x_coord, y_coord))

    # Always on top
    root_volume_ui.attributes('-topmost', True)
    root_volume_ui.wm_attributes('-topmost', True)
    # Frameless window (Linux solution)
    root_volume_ui.wm_attributes('-type', 'splash')
    # Transparent display
    root_volume_ui.attributes('-alpha', .3)
    root_volume_ui.wm_attributes('-alpha', .3)

    # Frameless
    root_volume_ui.overrideredirect(True)

    # Randomly settable "Volume Bar"
    progress_bar.place(x=10, y=10, width=380)


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

# Volume events control
def disable_volume_control():
    print('Disabled volume control')
    volume_bar_hide_timer.cancel()
    volume_bar_ui.withdraw()
    keyboard_listener.stop()
    mouse_listener.stop()


def restore_volume_control():
    print('Restore volume control')
    start_input_listeners()
    volume_bar_ui.deiconify()


# Volume Control Bar
def show_volume_bar(_event):
    volume_bar_ui.deiconify()


def hide_volume_bar(_event):
    volume_bar_ui.withdraw()


def update_volume_bar_value(event):
    if event.widget.winfo_viewable() == 0:
        volume_bar_ui.deiconify()
    volume_bar_value.set(last_set_volume)


volume_bar_ui = tkinter.Tk()
# "Volume" bar
volume_bar_value = tkinter.DoubleVar()
volume_bar = ttk.Progressbar(master=volume_bar_ui, variable=volume_bar_value, maximum=1)
# Event Bindings
volume_bar_ui.bind("<<Show>>", show_volume_bar)
volume_bar_ui.bind("<<Hide>>", hide_volume_bar)
volume_bar_ui.bind("<<UpdateValue>>", update_volume_bar_value)

render_volume_bar_ui(volume_bar_ui, volume_bar)

keyboard_listener: keyboard.Listener
mouse_listener: mouse.Listener


def start_input_listeners():
    global keyboard_listener, mouse_listener
    keyboard_listener = keyboard.Listener(on_press=on_key_pressed, on_release=on_key_released)
    mouse_listener = mouse.Listener(on_scroll=on_mouse_scroll)

    keyboard_listener.start()
    mouse_listener.start()


start_input_listeners()


# def volume_bar_runtime():
#     # Custom loop. Don't run any blocking functions in here, so it can continuously pick up events and control the GUI.
#     print('Press ctrl + x to exit')
#     while True:
#         # Slow down updates
#         time.sleep(.1)
#         gui_visible = volume_bar_ui.winfo_viewable()
#         if update_gui:
#             # if not gui_visible:
#             #     # volume_bar_ui.deiconify()
#             #     volume_bar_ui.event_generate("<<Show>>", when="tail")
#             volume_bar_ui.event_generate("<<UpdateValue>>", when="tail")
#             # volume_bar_value.set(last_set_volume)
#             volume_bar_ui.update()
#         if time.time() - idle_instant > idle_time:
#             volume_bar_ui.event_generate("<<Hide>>", when="tail")
#             # volume_bar_ui.withdraw()
#         if terminate_application:
#             exit(0)


# Options Menu
def restore_from_tray():
    global options_ui
    disable_volume_control()
    options_ui.deiconify()


def minimise_to_tray():
    global options_ui
    options_ui.withdraw()
    restore_volume_control()


def exit_app():
    print('(Sarcastically)" Exit "')


options_ui = tkinter.Toplevel(volume_bar_ui)
options_ui.geometry('400x200')
options_ui.protocol('WM_DELETE_WINDOW', minimise_to_tray)

# Tray Icon
image = Image.open('volume.png')
tray_menu = (pystray.MenuItem('Quit', exit_app), pystray.MenuItem('Show', restore_from_tray))
tray_icon = pystray.Icon('name', image, 'title', tray_menu)
threading.Thread(daemon=True, target=lambda: tray_icon.run()).start()

volume_bar_ui.withdraw()
volume_bar_ui.mainloop()
