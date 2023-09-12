import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class TSLEnums:
    class OutputTriggerModes(SettingEnum):
        NONE = "0"
        STOP = "1"
        START = "2"
        STEP = "3"

    class PowerUnit(SettingEnum):
        dBm = "0"
        mW = "1"

    class WavelengthUnit(SettingEnum):
        nm = "0"
        THz = "1"

    class SweepModes(SettingEnum):
        STEP_ONE_WAY = "0"
        SWEEP_ONE_WAY = "1"
        STEP_TWO_WAY = "2"
        SWEEP_TWO_WAY = "3"


class TSL_SCPICommands(visadevice.VisaDevice, TSLEnums):
    """Driver to communicate with a Santec TSL laser using the SCPI command set"""

    trigger_external = visa_property(":trigger:input:external", dtype=bool)
    trigger_standby = visa_property(":trigger:input:standby", dtype=bool)

    trigger_output = visa_property(":trigger:output", dtype=TSLEnums.OutputTriggerModes)

    laser_diode_on = visa_property(":power:state", dtype=bool)
    shutter_closed = visa_property(":power:shutter", dtype=bool)

    power_unit = visa_property(":power:unit", dtype=TSLEnums.PowerUnit)
    power = visa_property(":power:level", dtype=float)
    power_actual = visa_property(":power:actual:level", dtype=float, read_only=True)

    wavelength_display_unit = visa_property(":wavelength:unit", dtype=TSLEnums.WavelengthUnit)
    wavelength = visa_property(":wavelength", dtype=float)
    frequency = visa_property(":wavelength:frequency", dtype=float)
    fine_tuning = visa_property(":wavelength:fine", dtype=float)
    disable_fine_tuning = visa_command(":wavelength:fine:disable")

    sweep_wavelength_start = visa_property(":wavelength:sweep:start", dtype=float)
    sweep_wavelength_stop = visa_property(":wavelength:sweep:stop", dtype=float)
    sweep_wavelength_speed = visa_property(":wavelength:sweep:speed", dtype=float)
    sweep_mode = visa_property(":wavelength:sweep:mode", dtype=TSLEnums.SweepModes)
    sweep_single = visa_command(":wavelength:sweep:state 1")

    ## define these function for compatibilty with the Santec command class
    def turn_diode_on(self):
        self.laser_diode_on = True

    def turn_diode_off(self):
        self.laser_diode_on = False

    def close_shutter(self):
        self.shutter_closed = True

    def open_shutter(self):
        self.shutter_closed = False


def santec_property(visa_cmd, dtype=None, read_only=False, **kw):
    kw.setdefault("read_suffix", "")
    kw.setdefault("read_on_write", True)
    kw.setdefault("write_cmd_delimiter", "")
    return visa_property(visa_cmd, dtype=dtype, read_only=read_only, **kw)


class TSL_SantecCommands(visadevice.VisaDevice, TSLEnums):
    """Driver to communicate with a Santec TSL laser using the non-SCPI, Santec-specific command set"""
    turn_diode_on = visa_command("LO")
    turn_diode_off = visa_command("LF")

    wavelength = santec_property("WA", dtype=float)
    frequency = santec_property("FQ", dtype=float)
    fine_tuning = santec_property("FT", dtype=float)
    disable_fine_tuning = visa_command("FTF")

    power = santec_property("LP", dtype=float)

    close_shutter = visa_command("SC")
    open_shutter = visa_command("SO")

    sweep_wavelength_start = santec_property("SS", dtype=float)
    sweep_wavelength_stop = visa_property("SE", dtype=float)
    sweep_wavelength_speed = visa_property("SN", dtype=float)
    # sweep_mode = visa_property("SM", dtype=TSLEnums.SweepModes)
    sweep_single = visa_command("SG1")
