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
    hw_conf = read_hw_config()
    device_parts = hw_conf[id].split("@")
    device_class = device_parts[0]
    device_address = "@".join(device_parts[1:])

    if "." in device_class:
        split_class = device_class.split(".")
        device_inner_class = split_class[-1]
        driver_file = split_class[:-1]
        driver_file = ".".join(driver_file)
        eval(f"from .drivers.{driver_file} import {device_inner_class}")

    device_class = eval(f"drivers.{device_class}")

    dev = device_class(id, device_address)

    return dev


def read_hw_config(computer_name=None):
    if computer_name is None:
        computer_name = pylabframe.general.get_computer_name()

    return pylabframe.general.load_config_file(f"hardware/{computer_name}")


class Device:
    def __init__(self, id, error_on_double_connect=True, **kw):
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


def str_conv(s):
    return s.replace('"', '')


def intbool_conv(s):
    return bool(int(s))


class SettingEnum(Enum):
    def __str__(self):
        return self.value
