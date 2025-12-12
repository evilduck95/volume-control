import time

import psutil
from xdo import Xdo

from loggingutils import get_logger

logger = get_logger(__file__)


def get_active_window_info() -> tuple[int, str]:
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


def find_process_info(active_pid: int) -> psutil.Process:
    for proc in psutil.process_iter():
        if proc.pid == active_pid:
            return proc


def get_all_related_processes(proc: psutil.Process) -> tuple[psutil.Process, list[psutil.Process]]:
    parent = proc.parent()
    # Get the parent only if it's there and is from the same program
    if parent is None or parent.exe() != proc.exe():
        parent = proc
    return parent, proc.children(recursive=True)


def find_focused_app_process_ids() -> tuple[psutil.Process, list[psutil.Process]]:
    active_pid, _name = get_active_window_info()
    focussed_proc = find_process_info(active_pid)
    parent, children = get_all_related_processes(focussed_proc)
    logger.debug(f'Process: [{focussed_proc.pid}:{focussed_proc.name()}] has {len(children)} children: {children}')
    return parent, children
