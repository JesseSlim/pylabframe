"""Device drivers to control Thorlabs equipment."""

import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class ThorlabsPM100D(visadevice.VisaDevice):
    """Driver to communicate with a Thorlabs PM100D/PM200D power meter"""

    average_count = visa_property("sense:average:count", dtype=int)
    """Number of averages used for power reading."""

    wavelength = visa_property("sense:correction:wavelength", dtype=float)
    """Power correction wavelength (nm)."""

    auto_range = visa_property("sense:power:range:auto", dtype=bool)
    """Enable power auto range."""
    power = visa_property("read", read_only=True, dtype=float)
    """Current power reading (read-only)."""

    adjust_zero = visa_command("sense:correction:collect:zero:initiate")
    """Adjust power zero offset."""

    configure_power = visa_command("configure:power")
    """Set up instrument for power measurement."""
