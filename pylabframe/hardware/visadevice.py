import pyvisa
from . import device

_visa_rm = pyvisa.ResourceManager()

class VisaDevice(device.Device):
    def __init__(self, id, address, **kw):
        super().__init__(id, **kw)
        self.address = address
        self.visa_instr: pyvisa.resources.messagebased.MessageBasedResource = _visa_rm.open_resource(address)

    def __del__(self):
        self.visa_instr.close()
        del self.visa_instr

    @classmethod
    def list_available(cls):
        return list(_visa_rm.list_resources())

    def get_identifier(self, sanitize=True):
        response = self.visa_instr.query("*IDN?")
        if sanitize:
            response = response.strip()
        return response

    def wait_until_done(self, visa_cmd=None):
        if visa_cmd is not None:
            cmd_string = f"{visa_cmd};*OPC?"
        else:
            cmd_string = "*OPC?"
        self.visa_instr.write(cmd_string)
        is_done = False
        while not is_done:
            try:
                result_code = self.visa_instr.read()
                is_done = True
            except pyvisa.VisaIOError as e:
                if e.error_code != pyvisa.constants.StatusCode.error_timeout:
                    # re-raise anything other than a time-out
                    raise e
        return result_code

    @classmethod
    def visa_property(cls, visa_cmd: str, read_only=False, read_conv=str, write_conv=str, rw_conv=None):
        if rw_conv is not None:
            read_conv = rw_conv
            write_conv = rw_conv

        def visa_getter(self: VisaDevice):
            # doing this gives us access to object properties (eg channel id) that can be put in the command string
            fmt_visa_cmd = visa_cmd
            if hasattr(self, "query_params"):
                fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)
            response = self.visa_instr.query(f"{fmt_visa_cmd}?")
            response = read_conv(response.strip())
            return response

        if not read_only:
            def visa_setter(self: VisaDevice, value):
                fmt_visa_cmd = visa_cmd
                if hasattr(self, "query_params"):
                    fmt_visa_cmd = fmt_visa_cmd.format(**self.query_params)
                cmd = f"{fmt_visa_cmd} {write_conv(value)}"
                self.visa_instr.write(cmd)
        else:
            visa_setter = None

        prop = property(visa_getter, visa_setter)

        return prop

    @classmethod
    def visa_command(cls, visa_cmd, wait_until_done=False):
        def visa_executer(self: VisaDevice, **kw):
            if hasattr(self, "query_params"):
                kw.update(self.query_params)

            fmt_visa_cmd = visa_cmd.format(**kw)
            if wait_until_done:
                return self.wait_until_done(fmt_visa_cmd)
            else:
                return self.visa_instr.write(fmt_visa_cmd)

        return visa_executer