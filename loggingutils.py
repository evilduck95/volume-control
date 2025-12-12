import logging
import os


def get_logger(py_file):
    logger = logging.getLogger(os.path.basename(py_file).replace('.py', ''))
    return logger
