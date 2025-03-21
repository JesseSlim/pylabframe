"""The ``visadevice`` module helps you  interface with VISA devices.

This module builds on top of the `PyVISA`_ package.



.. _`PyVISA`: https://github.com/pyvisa/pyvisa
"""
import copy
import time
import string

import pyvisa
from . import device

from enum import Enum, IntEnum

_visa_rm = pyvisa.ResourceManager()


class EventStatusRegister:
    class Functions(IntEnum):
        OPC = 0
        RQC = 1
        QYE = 2   # query error
        DDE = 3
        EXE = 4
        CME = 5
        URQ = 6
        PON = 7
    ERROR_MASK = 0b00111100

    def __init__(self, val):
        self.esr = int(val)

    def function_value(self, func):
        return bool(self.esr & (1 << func))

    @property
    def is_error(self):
        return bool(self.esr & self.ERROR_MASK)

    @property
    def command_error(self):
        return self.function_value(self.Functions.CME)

    @property
    def execution_error(self):
        return self.function_value(self.Functions.EXE)

    @property
    def device_error(self):
        return self.function_value(self.Functions.DDE)

    @property
    def query_error(self):
        return self.function_value(self.Functions.QYE)

    def __repr__(self):
        bits_set = []
        for i in range(8):
            if self.function_value(i):
                bits_set.append(self.Functions(i))

        bits_set = [b.name for b in bits_set]
        return f"EventStatusRegister([{', '.join(bits_set)}])"


DTYPE_CONVERTERS = {
    bool: (device.intbool_conv, int),
}


def visa_property(visa_cmd: str, dtype=None, read_only=False, read_conv=str, write_conv=str, rw_conv=None,
                  access_guard=None, read_suffix="?", read_on_write=False, set_cmd_delimiter=" ",
                  ):
    """Defines a property that reads out or sets a device parameter. Must be used within a :class:`VisaDevice`.

    For every access of the property, the command specified in ``visa_cmd`` is sent to the device. If it's a read access,
    the device's response is returned. If it's a write access, the value to be written is appended to the command before sending.

    If you're writing your own device driver for a VISA/SCPI-compatible instrument, this function will be your friend / the main workhorse.

    Example usage::

        from pylabframe.hw.visadevice import VisaDevice, visa_property, device

        class FancyLaser(VisaDevice):
            wavelength = visa_property(":wavelength")

        device.register_driver_class("FancyLaser", FancyLaser)
        device.register_device("my_laser", driver="FancyLaser", address="USB:123:456")

        laser = device.get_device('my_laser')

        print(f"Current wavelength: {laser.wavelength}")
        laser.wavelength = 1550.0

    :param visa_cmd: The command to be sent to the device to read or write the parameter. This will typically be a SCPI command listed in the instrument manual. For example: ``sense:freq:center`` to get the center frequency setting of a Keysight spectrum analyser.
    :param dtype: Data type of the parameter value, e.g. ``bool`` or ``float``.
    :param read_only: If True, this device parameter can only be read. Writing to it will raise an exception.
    :param read_conv: Function to convert the device's response into the parameter value. Useful if the device uses a nonstandard response format. Defaults to the relevant entry in :data:`DTYPE_CONVERTERS` if that exists for ``dtype``.
    :param write_conv: Function to convert the value to be written into something the instrument will understand. Defaults to the relevant entry in :data:`DTYPE_CONVERTERS` if that exists for ``dtype``.
    :param rw_conv: If specified, use this function both as ``read_conv`` and as ``write_conv``.
    :param access_guard: If specified, this function is called before the instrument is queried. Can be used to make sure that the instrument is in the right state. If it is not, the ``access_guard`` function should raise a (useful) exception.
    :param read_suffix: This suffix is appended to the ``visa_cmd`` in case of a read access. Defaults to ``?`` as is common for SCPI commands.
    :param read_on_write: If True, a VISA read is issued even after a write access. Some devices return a value upon setting, this allows to clear out the buffer. The response is discarded.
    :param set_cmd_delimiter: Delimiter between ``visa_cmd`` and the value to be set. Defaults to :literal:`\\ ` (blank space).
    :return:
    """
    if rw_conv is not None:
        read_conv = rw_conv
        write_conv = rw_conv

    if dtype is not None:
        if dtype in DTYPE_CONVERTERS:
            read_conv, write_conv = DTYPE_CONVERTERS[dtype]
        else:
            read_conv, write_conv = dtype, dtype
            if issubclass(dtype, device.SettingEnum):
                write_conv = str

    # we use this dict to pass the property object into the getter/setter functions
    # such that these functions can look up their options in self.command_options
    property_info = {}

    def visa_getter(self: "VisaDevice"):
        if access_guard is not None:
            access_guard(self)

        fmt_visa_cmd = visa_cmd
        if hasattr(self, "query_params"):
            # doing this gives us access to object properties (eg channel id) that can be put in the command string
            fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)
        # we end the command with a configurable suffix, usually ? for SCPI settings
        response = self._query(f"{fmt_visa_cmd}{read_suffix}")
        response = read_conv(response.strip())

        # apply configurable transformations
        this_prop = property_info['property_object']
        if this_prop in self.command_options:
            response = visa_read_value_transform(response, **self.command_options[this_prop])

        return response

    # set type hint so that it is picked up by Sphinx for documentation
    if dtype is not None:
        visa_getter.__annotations__['return'] = dtype

    if not read_only:
        def visa_setter(self: "VisaDevice", value):
            if access_guard is not None:
                access_guard(self)

            fmt_visa_cmd = visa_cmd
            if hasattr(self, "query_params"):
                fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)

            # apply configurable transformations
            this_prop = property_info['property_object']
            if this_prop in self.command_options:
                if self.command_options[this_prop].get("disable_write", False):
                    raise ValueError("Writing to this device property has been disabled in your config.")
                value = visa_write_value_transform(value, **self.command_options[this_prop])

            value = write_conv(value)

            # we squeeze in a configurable delimiter (default is space)
            cmd = f"{fmt_visa_cmd}{set_cmd_delimiter}{value}"
            if not read_on_write:
                self._write(cmd)
            else:
                # some devices return a value upon setting, optionally read that out to clear the buffer
                # we discard the response, nothing we can do with it here
                self._query(cmd)
    else:
        visa_setter = None

    prop = property(visa_getter, visa_setter)
    property_info['property_object'] = prop

    return prop


def visa_command(visa_cmd, wait_until_done=False, kwarg_defaults=None, wait_before=False, max_wait=False, read_on_write=False):
    if kwarg_defaults is None:
        kwarg_defaults = {}
    wait_until_done_default = wait_until_done
    wait_before_default = wait_before
    max_wait_default = max_wait
    read_on_write_default = read_on_write

    def visa_executer(self: "VisaDevice", wait_until_done=None, wait_before=None, max_wait=None, read_on_write=None, **kw):
        if wait_until_done is None:
            wait_until_done = wait_until_done_default
        if wait_before is None:
            wait_before = wait_before_default
        if max_wait is None:
            max_wait = max_wait_default
        if read_on_write is None:
            read_on_write = read_on_write_default
        if hasattr(self, "query_params"):
            kw.update(self.query_params)

        kw_plus_defaults = {
            **kwarg_defaults,
            **kw
        }
        try:
            fmt_visa_cmd = visa_cmd.format(**kw_plus_defaults)
        except KeyError as e:
            # TODO: raise an error as well for unused arguments (using string.Formatter & check_unused_args)
            raise ValueError(f"Missing argument {e.args[0]} in VISA command '{visa_cmd}'")
        if wait_before:
            fmt_visa_cmd = "*WAI;" + fmt_visa_cmd
        if wait_until_done:
            return self.wait_until_done(fmt_visa_cmd, max_wait=max_wait)
        else:
            if not read_on_write:
                return self._write(fmt_visa_cmd)
            else:
                # some devices return a value upon setting, optionally read that out to clear the buffer
                # return the response
                return self._query(fmt_visa_cmd)

    return visa_executer


def visa_query(visa_cmd, kwarg_defaults=None, binary=False, **query_kw):
    if kwarg_defaults is None:
        kwarg_defaults = {}
    def visa_executer(self: "VisaDevice", **kw):
        if hasattr(self, "query_params"):
            kw.update(self.query_params)

        kw_plus_defaults = {
            **kwarg_defaults,
            **kw
        }
        try:
            fmt_visa_cmd = visa_cmd.format(**kw_plus_defaults)
        except KeyError as e:
            # TODO: raise an error as well for unused arguments (using string.Formatter & check_unused_args)
            raise ValueError(f"Missing argument {e.args[0]} in VISA command '{visa_cmd}'")

        if not binary:
            return self._query(fmt_visa_cmd, **query_kw)
        else:
            return self._query_binary_values(fmt_visa_cmd, datatype='s', container=bytes, **query_kw)

    return visa_executer


def visa_read_value_transform(val, value_multiplier=None, round_on_read_digits=None, **kw):
    if value_multiplier is not None:
        # upon read, multiply
        val = val * value_multiplier
    if round_on_read_digits is not None:
        val = round(val, round_on_read_digits)
    return val


def visa_write_value_transform(val, value_multiplier=None, round_on_write_digits=None, **kw):
    if value_multiplier is not None:
        # upon write, divide
        val = val / value_multiplier
    if round_on_write_digits is not None:
        val = round(val, round_on_write_digits)
    return val


def debug_wrapper_method(func_name):
    def _method(self, *args, **kw):
        if self._debug_on:
            event = {'type': func_name, 'args': args, 'kw': kw}
            self.debug_log.append(event)
        inner_func = eval(f'self.{func_name}')
        rval = inner_func(*args, **kw)
        if self._debug_on:
            event = {'type': f'{func_name}_rval', 'rval': rval}
            self.debug_log.append(event)
        return rval
    return _method


class VisaDevice(device.Device):
    def __init__(self, id, address, error_on_double_connect=True, settings=None, command_options=None, **kw):
        super().__init__(id, error_on_double_connect=error_on_double_connect, settings=settings)
        self.address = address
        self.instr: pyvisa.resources.messagebased.MessageBasedResource = _visa_rm.open_resource(address, **kw)

        # construct command options
        self.command_options = {}
        if command_options is not None:
            for k,v in command_options.items():
                cmd_obj = self.look_up_command_object(k)
                self.command_options[cmd_obj] = v

    def __del__(self):
        if self.instr:
            self.instr.close()
            del self.instr

    def setup(self, *args, **kw):
        pass

    @classmethod
    def list_available(cls):
        return list(_visa_rm.list_resources())

    def get_identifier(self, sanitize=True):
        response = self._query("*IDN?")
        if sanitize:
            response = response.strip()
        return response

    def wait_until_done(self, visa_cmd=None, max_wait=False):
        if visa_cmd is not None:
            cmd_string = f"{visa_cmd};*OPC?"
        else:
            cmd_string = "*OPC?"
        start_time = time.perf_counter()
        self._write(cmd_string)
        is_done = False
        while not is_done:
            if max_wait is not False and time.perf_counter() - start_time > max_wait:
                raise TimeoutError(f"Exceeded the maximum waiting time of {max_wait} s")
            try:
                result_code = self._read()
                is_done = True
            except pyvisa.VisaIOError as e:
                if e.error_code != pyvisa.constants.StatusCode.error_timeout:
                    # re-raise anything other than a time-out
                    raise e
        return result_code

    def look_up_command_object(self, cmd):
        if isinstance(cmd, str):
            if not hasattr(type(self), cmd):
                raise ValueError(f"Visa command '{cmd}' cannot be found.")
            cmd = getattr(type(self), cmd)
        if not isinstance(cmd, property) and not callable(cmd):
            raise ValueError(f"Invalid command object '{cmd}'. Hint: don't supply <device>.<command> (e.g. my_laser.wavelength), which references the value of the property, not the command object itself. Supply either 'type(<device>).<command>' (e.g. type(my_laser).wavelength) or the name of the command (e.g. 'wavelength')")

        return cmd

    def set_command_option(self, cmd, value_multiplier=None, **kw):
        cmd = self.look_up_command_object(cmd)
        if cmd not in self.command_options:
            self.command_options[cmd] = {}

        if value_multiplier is not None:
            kw['value_multiplier'] = value_multiplier

        for k,v in kw.items():
            self.command_options[cmd][k] = v

    def remove_command_option(self, cmd, value_multiplier=False, **kw):
        cmd = self.look_up_command_object(cmd)
        if cmd not in self.command_options:
            return

        if value_multiplier:
            kw['value_multiplier'] = True

        for k,v in kw.items():
            if v and k in self.command_options[cmd]:
                del self.command_options[cmd][k]

    ## standard SCPI commands
    clear_status = visa_command("*CLS")
    status_register = visa_property("*ESR", dtype=EventStatusRegister, read_only=True)
    # status_byte = visa_property("*STB", dtype=int, read_only=True)
    @property
    def status_byte(self):
        return self._read_stb()  # seems to be the more specific way of reading status byte?

    _write = debug_wrapper_method('instr.write')
    _read = debug_wrapper_method('instr.read')
    _query = debug_wrapper_method('instr.query')
    _query_binary_values = debug_wrapper_method('instr.query_binary_values')
    _read_stb = debug_wrapper_method('instr.read_stb')
