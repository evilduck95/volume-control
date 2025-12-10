import enum
from typing import Callable, TypeVar, Any, Generic

noop_func = lambda *a, **k: None

T = TypeVar("T")


# Allows calling a bunch of connected functions when emit is called
class Signal(Generic[T]):

    def __init__(self, name: str):
        self.name = name
        self.func_bindings = []

    def connect(self, func: Callable):
        self.func_bindings.append(func)

    def emit(self, arg: T = None):
        for func in self.func_bindings:
            func(arg)


class ControlTarget(enum.Enum):
    SYSTEM = 'system'
    CURRENT_APPLICATION = 'current_application'
