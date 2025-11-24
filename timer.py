import threading
import time
from collections.abc import Callable


class DelayedAction:

    _min_delay: float = -1
    _start_time: float = 0
    _action: Callable
    _action_timer_thread: threading.Thread
    _running: bool = False
    _killed: bool = False

    def __init__(self, min_delay, action: Callable):
        self._min_delay = min_delay
        self._action = action

    def _action_thread(self):
        while True:
            if self._killed:
                return
            time.sleep(.5)
            if time.time() - self._start_time >= self._min_delay:
                self._action()
                self._running = False
                return

    def run(self):
        if not self._running:
            self._action_timer_thread = threading.Thread(target=self._action_thread)
            self._action_timer_thread.start()
            self._running = True
        self._start_time = time.time()

    def cancel(self):
        if self._running:
            self._killed = True
