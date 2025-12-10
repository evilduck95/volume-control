from xdo import Xdo


def get_active_window_info() -> int:
    xdo = Xdo()
    # Get the Process ID of the current focused window
    active_window = xdo.get_active_window()
    active_pid = xdo.get_pid_window(active_window)
    focused = xdo.get_focused_window()
    window_name = xdo.get_window_name(active_window)
    sane_window = xdo.get_focused_window_sane()
    # print('Focused Window: ' + str(active_pid))
    # TODO: Use psutil (or similar) to get child processes of active window
    #  Possibly might have to get parent first and then children
    return active_pid, window_name
