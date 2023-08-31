import numpy as np
from enum import Enum
import os
import warnings
import time

import pylabframe as lab

from pylabframe import config
from pylabframe.hw import device
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv, Device
import pylabframe.data

if lab.config.get("drivers.pyrpl.user_dir", False) is not False:
    os.environ["PYRPL_USER_DIR"] = lab.config.get("drivers.pyrpl.user_dir")
else:
    warnings.warn(
        "No configuration directory for PyRPL specified. Note that you need to load your config file before importing the RedPitaya driver if you want to set it."
    )

# we're now ready to import pyrpl
from pyrpl import Pyrpl
import pyrpl

class RedPitaya(Device):
    def __init__(self, id, hostname, port=None, config_file=None, error_on_double_connect=True, **config_args):
        super().__init__(id, error_on_double_connect=error_on_double_connect)
        config_args["hostname"] = hostname
        if port is not None:
            config_args["port"] = port

        if "gui" not in config_args:
            # disable gui by default
            config_args["gui"] = False

        if config_file is not None:
            config_args["config"] = config_file

        self.instr = Pyrpl(**config_args)

    def get_voltage(self, channel=1, direction="in"):
        prop_name = f"voltage_{direction}{channel}"

        return getattr(self.instr.rp.scope, prop_name)

    def set_led(self, led_int):
        self.instr.rp.hk.led = led_int

    def set_iq(self, iq_id, **settings):
        """Parameters:
        frequency, bandwidth, gain, phase, acbandwidth, amplitude,
        input, output_direct, output_signal, quadrature_factor + more?
        """
        iq_propname = f"iq{iq_id}"
        iq = getattr(self.instr.rp, iq_propname)
        iq.setup(**settings)

    def list_iq_bandwidths(self, iq_id=0):
        iq_propname = f"iq{iq_id}"
        iq = getattr(self.instr.rp, iq_propname)

        return iq.bandwidths

    def measure_iq_sample(self, iq_id, avg_tcs=1.0, settling_tcs=1.0, rbw=None, iq_setup=True):
        if iq_setup == True:
            if rbw is not None:
                self.set_iq(iq_id, bandwidth=rbw)

        # get IQ module
        iq_propname = f"iq{iq_id}"
        iq: pyrpl.Iq = getattr(self.instr.rp, iq_propname)

        # the following is all stolen from pyrpl.Iq.na_trace(...)
        # NA meaning network analyzer. Here I copy the code to measure
        # a single point
        rbw = iq.bandwidth[0]
        # setup averaging
        iq._na_averages = np.int(np.round(125e6 / rbw * avg_tcs))
        iq._na_sleepcycles = np.int(np.round(125e6 / rbw * settling_tcs))
        # compute rescaling factor
        rescale = 2.0 ** (-iq._LPFBITS) * 4.0  # 4 is artefact of fpga code

        # apparently this triggers "NA" acquisition
        iq.frequency = iq.frequency
        time.sleep(1.0 / rbw * (avg_tcs + settling_tcs))

        sample = iq._nadata * rescale

        return sample

    def show_gui(self):
        """Open the Pyrpl GUI"""
        self.instr.show_gui()
