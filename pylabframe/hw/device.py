"""The ``device`` module provides basic infrastructure for device drivers.

It provides two major components: the function :func:`~get_device` to open or retrieve a connection to a device and
the base class :class:`~Device` that all device drivers should inherit.

It also provides a few convenience functions to deal with typical device response formats.
"""

import copy

from .. import config
from enum import Enum

_connected_devices = {}


def get_device(id, driver=None, **extra_settings):
    """Connect to a device, or retrieve an existing connection.

    :param id: Identifier of the device, as specified in the configuration file.
    :param driver: If specified, use this driver to connect rather than the driver specified in the configuration.
    :param extra_settings: Keyword arguments are passed on the device constructor to specify extra settings.
    :return: The device object. If the device is already connected, returns the existing device object.
    """
    if id in _connected_devices:
        return _connected_devices[id]
    else:
        dev = _connect_device(id, driver=driver, **extra_settings)
        _connected_devices[id] = dev
        return dev


def _connect_device(id, driver=None, **extra_settings):
    from . import drivers
    hw_conf = config.get('devices')
    device_settings = copy.deepcopy(hw_conf[id])

    if driver is None:
        driver = device_settings['driver']

    # remove driver from the device settings dict -- the remaining parameters are fed to the constructor
    if "driver" in device_settings:
        del device_settings['driver']

    if isinstance(driver, str):
        # check if the driver is registered as a custom driver class
        if driver in config.get("drivers.classes", {}):
            driver = config.get(f"drivers.classes.{driver}")
        else:
            if not "." in driver:
                raise RuntimeError("Device driver class object not registered directly. Device driver strings should include the module from which the driver class should be imported.")

            # work out the module from which the driver should be imported
            # e.g. if driver == "my.custom.module.FancyLaser", then driver_module == "my.custom.module"
            split_class = driver.split(".")
            driver_module = split_class[:-1]
            driver_module = ".".join(driver_module)

            # check if the driver is specified as a custom driver
            is_custom_driver = False
            for m in config.get("drivers.modules", []):
                if driver_module == m or driver_module.startswith(m + "."):
                    is_custom_driver = True
                    break

            if is_custom_driver:
                exec(f"import {driver_module}")
                driver = eval(f"{driver}")
            else:
                exec(f"from .drivers import {driver_module}")
                driver = eval(f"drivers.{driver}")

    device_settings.update(extra_settings)

    dev = driver(id, **device_settings)

    return dev


def register_device(id, driver, **settings):
    if "." in id:
        raise ValueError(f"Device ids cannot have a . (dot). Got: {id}")

    config.set(f"devices.{id}.driver", driver)
    for k, v in settings.items():
        config.set(f"devices.{id}.{k}", v)


def register_driver_module(module):
    config.list_append("drivers.modules", module)


def register_driver_class(name, class_object):
    if "." in name:
        raise ValueError(f"Directly registered driver classes cannot have a . (dot) in their name. Got: {name}")
    config.set(f"drivers.classes.{name}", class_object)


class Device:
    """A Device object represents a generic lab instrument.

    This class provides some basic infrastructure. It keeps track of device settings and registers which fields should
    be automatically included in the metadata for each measurement.

    This class should be subclassed to implement an actual device -- it should not be constructed directly.
    """

    DEFAULT_SETTINGS = {}
    """Extensible dict that holds the default settings for a particular type of device.
    
    Device subclasses may define their own ``DEFAULT_SETTINGS`` attribute -- these will be collected automatically."""

    METADATA_FIELDS = []
    """Extensible list of the fields that should be auto-included as metadata for every measurement.
    
    Device subclasses may define their own ``METADATA_FIELDS`` attribute -- these will be collected automatically.
    """

    def __init__(self, id, error_on_double_connect=True, settings=None):
        """Construct a new device. Should only be called from the constructor of a subclass implementing an actual device.

        The constructor collects all :attr:`~pylabframe.hw.device.Device.DEFAULT_SETTINGS` and :attr:`~pylabframe.hw.device.Device.METADATA_FIELDS` from this device's subclasses.

        :param id: the identifier of the device, as specified in the configuration file.
        :param error_on_double_connect: if True, raises an error if the device specified by ``id`` is already connected.
        :param settings: dict of device settings. Settings supplied here override :attr:`~pylabframe.hw.device.Device.DEFAULT_SETTINGS`.
        """
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

        if settings is None:
            settings = {}

        self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)
        self.settings.update(settings)

    @classmethod
    def list_available(cls):
        """List available devices. In the generic ``Device`` class, this returns an empty list."""
        return []

    def collect_metadata(self) -> dict:
        """Collect the values for all device parameters specified in :attr:`~pylabframe.hw.device.Device.METADATA_FIELDS`

        :return: dict of parameter names and values
        """
        metadata_collection = {}
        for k, v in self.metadata_registry.items():
            value = v()
            if isinstance(value, SettingEnum):
                value = value.name
            metadata_collection[k] = value

        return metadata_collection


## Functions and classes that facilitate data conversion to and from SCPI strings

def str_conv(s):
    """Removes double-quotes from a string (e.g. received as SCPI response)"""
    return s.replace('"', '')


def intbool_conv(s):
    """Converts a numerical string to a bool: return bool(int(s))"""
    return bool(int(s))


class SettingEnum(Enum):
    """Base class for enumerations of device settings.

    Can be used to map convenient names to specific strings that indicate a setting. For example::

        class DetectorModes(SettingEnum):
            NORMAL = "NORM"
            AVERAGE = "AVER"
            SAMPLE = "SAMP"

    The ``__str__`` function of ``SettingEnum`` is specified such that it just returns the (string) value of the enum member,
    so that e.g. :code:`str(DetectorModes.NORMAL) == "NORMAL"` rather than :code:`str(DetectorModes.NORMAL) == "DetectorModes.NORMAL"`
    (the default behaviour for :external:class:`enum.Enum`). This ensures that :code:`str(DetectorModes.NORMAL)` can be
    plugged directly into a device control command.
    """
    def __str__(self):
        return self.value
