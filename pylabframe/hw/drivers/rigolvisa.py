"""Device drivers to control Rigol equipment."""

import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class RigolDG1022(visadevice.VisaDevice):
    """Driver to communicate with a Rigol function generator"""

    def __init__(self, *args, query_delay=0.01, **kwargs):
        super().__init__(*args, query_delay=query_delay, **kwargs)

    offset = visa_property("voltage:offset", dtype=float)
    status_register = None  # device does not seem to support reading *ESR?
