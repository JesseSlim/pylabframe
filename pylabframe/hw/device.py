import copy

import pylabframe
from enum import Enum

_connected_devices = {}


def get_device(id):
    if id in _connected_devices:
        return _connected_devices[id]
    else:
        dev = _connect_device(id)
        _connected_devices[id] = dev
        return dev


def _connect_device(id):
    from . import drivers
    hw_conf = pylabframe.config.get('devices')
    device_settings = copy.deepcopy(hw_conf[id])
    device_class = device_settings['driver']

    # remove driver from the device settings dict -- the remaining parameters are fed to the constructor
    del device_settings['driver']

    # import from sub-file
    if "." in device_class:
        split_class = device_class.split(".")
        driver_file = split_class[:-1]
        driver_file = ".".join(driver_file)
        exec(f"from .drivers import {driver_file}")

    device_class = eval(f"drivers.{device_class}")

    dev = device_class(id, **device_settings)

    return dev


class Device:
    def __init__(self, id, error_on_double_connect=True):
        if id in _connected_devices and error_on_double_connect:
            raise RuntimeError(f"Device {id} already connected")

        metadata_fields = []

        # combine all default parameters from subclasses
        # process bottom to top (so subclasses can override params)
        subclasses = self.__class__.__mro__[::-1]
        for subcl in subclasses:
            if hasattr(subcl, "METADATA_FIELDS"):
                metadata_fields += subcl.METADATA_FIELDS

        # get unique fields
        metadata_fields = list(dict.fromkeys(metadata_fields))

        self.metadata_registry = {}
        for mf in metadata_fields:
            self.metadata_registry[mf] = lambda self=self, mf=mf: getattr(self, mf)

    @classmethod
    def list_available(cls):
        return []

    def collect_metadata(self):
        metadata_collection = {}
        for k, v in self.metadata_registry.items():
            value = v()
            if isinstance(value, SettingEnum):
                value = value.name
            metadata_collection[k] = value

        return metadata_collection


## Functions and classes that facilitate data conversion to and from SCPI strings

def str_conv(s):
    return s.replace('"', '')


def intbool_conv(s):
    return bool(int(s))


class SettingEnum(Enum):
    def __str__(self):
        return self.value
