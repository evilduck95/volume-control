from threading import Thread
from typing import Generic, T


class ReturningThread(Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super().__init__(group, target, name, args, kwargs)
        self._target = target
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, **kwargs) -> Generic[T]:
        super().join()
        return self._return
