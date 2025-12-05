import os

from typing import TextIO

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def open_resource(file: str, mode='r') -> TextIO:
    file_path = os.path.join(__location__, file)
    print(f'Opening: {file_path} in mode: {mode}')
    return open(file_path, mode=mode)


def does_resource_exist(file: str) -> bool:
    file_path = os.path.join(__location__, file)
    return os.path.exists(file_path)


def get_full_resource_path(file: str) -> str:
    return os.path.join(__location__, file)
