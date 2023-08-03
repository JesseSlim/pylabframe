import pyvisa
from . import device

from enum import Enum, IntEnum

_visa_rm = pyvisa.ResourceManager()


class EventStatusRegister:
    class Functions(IntEnum):
        OPC = 0
        RQC = 1
        QYE = 2
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


def visa_property(visa_cmd: str, dtype=None, read_only=False, read_conv=str, write_conv=str, rw_conv=None, access_guard=None):
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

    def visa_getter(self: "VisaDevice"):
        if access_guard is not None:
            access_guard(self)

        fmt_visa_cmd = visa_cmd
        if hasattr(self, "query_params"):
            # doing this gives us access to object properties (eg channel id) that can be put in the command string
            fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)
        response = self.instr.query(f"{fmt_visa_cmd}?")
        response = read_conv(response.strip())
        return response

    if not read_only:
        def visa_setter(self: "VisaDevice", value):
            if access_guard is not None:
                access_guard(self)

            fmt_visa_cmd = visa_cmd
            if hasattr(self, "query_params"):
                fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)
            cmd = f"{fmt_visa_cmd} {write_conv(value)}"
            self.instr.write(cmd)
    else:
        visa_setter = None

    prop = property(visa_getter, visa_setter)

    return prop


def visa_command(visa_cmd, wait_until_done=False, kwarg_defaults=None):
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
            raise ValueError(f"Missing argument {e.args[0]} in VISA command {visa_cmd}")
        if wait_until_done:
            return self.wait_until_done(fmt_visa_cmd)
        else:
            return self.instr.write(fmt_visa_cmd)

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
            raise ValueError(f"Missing argument {e.args[0]} in VISA command {visa_cmd}")

        if not binary:
            return self.instr.query(fmt_visa_cmd, **query_kw)
        else:
            return self.instr.query_binary_values(fmt_visa_cmd, datatype='s', container=bytes, **query_kw)

    return visa_executer


class VisaDevice(device.Device):
    def __init__(self, id, address, error_on_double_connect=True, **kw):
        super().__init__(id, error_on_double_connect=error_on_double_connect)
        self.address = address
        self.instr: pyvisa.resources.messagebased.MessageBasedResource = _visa_rm.open_resource(address, **kw)

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
        response = self.instr.query("*IDN?")
        if sanitize:
            response = response.strip()
        return response

    def wait_until_done(self, visa_cmd=None):
        if visa_cmd is not None:
            cmd_string = f"{visa_cmd};*OPC?"
        else:
            cmd_string = "*OPC?"
        self.instr.write(cmd_string)
        is_done = False
        while not is_done:
            try:
                result_code = self.instr.read()
                is_done = True
            except pyvisa.VisaIOError as e:
                if e.error_code != pyvisa.constants.StatusCode.error_timeout:
                    # re-raise anything other than a time-out
                    raise e
        return result_code

    ## standard SCPI commands
    clear_status_register = visa_command("*cls")
    status_register = visa_property("*esr", dtype=EventStatusRegister, read_only=True)
