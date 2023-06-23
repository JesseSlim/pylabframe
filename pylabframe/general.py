import sys
from . import config


def get_computer_name():
    return config.get('computer_name')
