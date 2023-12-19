import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class ThorlabsPM100D(visadevice.VisaDevice):
    """Driver to communicate with a PM100D/PM200D power meter"""

    average_count = visa_property("sense:average:count", dtype=int)
    wavelength = visa_property("sense:correction:wavelength", dtype=float)
    auto_range = visa_property("sense:power:range:auto", dtype=bool)
    power = visa_property("read", read_only=True, dtype=float)

    adjust_zero = visa_command("sense:correction:collect:zero:initiate")

    configure_power = visa_command("configure:power")