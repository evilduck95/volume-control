from xdo import Xdo


def get_active_window_pid() -> int:
    xdo = Xdo()
    # Get the Process ID of the current focused window
    active_window = xdo.get_active_window()
    active_pid = xdo.get_pid_window(active_window)
    # print('Focused Window: ' + str(active_pid))
    return active_pid
