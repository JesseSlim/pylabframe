import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class TSL(visadevice.VisaDevice):
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

    trigger_external = visa_property(":trigger:input:external", dtype=bool)
    trigger_standby = visa_property(":trigger:input:standby", dtype=bool)

    trigger_output = visa_property(":trigger:output", dtype=OutputTriggerModes)

    laser_diode_on = visa_property(":power:state", dtype=bool)
    shutter_closed = visa_property(":power:shutter", dtype=bool)

    power_unit = visa_property(":power:unit", dtype=PowerUnit)
    power = visa_property(":power:level", dtype=float)
    power_actual = visa_property(":power:actual:level", dtype=float, read_only=True)

    wavelength_display_unit = visa_property(":wavelength:unit", dtype=WavelengthUnit)
    wavelength = visa_property(":wavelength", dtype=float)
    frequency = visa_property(":wavelength:frequency", dtype=float)
