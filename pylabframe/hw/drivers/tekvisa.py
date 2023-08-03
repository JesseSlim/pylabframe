import os.path

import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command, visa_query
import pylabframe.data


class TektronixScope(visadevice.VisaDevice):
    NUM_CHANNELS = 2

    class RunModes(SettingEnum):
        CONTINUOUS = "RUNST"
        SINGLE = "SEQ"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set up data transferring already
        self.initialize_waveform_transfer(1)

        # initialize channels
        self.channels: list[TektronixScope.Channel] = [self.Channel(i+1, self) for i in range(self.NUM_CHANNELS)]

        self.setup()

    def setup(self, *args, **kw):
        self.instr.write("header 0")

    # global scpi properties
    trace_points = visa_property("horizontal:recordlength", rw_conv=int)
    run_mode = visa_property("acquire:stopafter", read_conv=RunModes)
    running = visa_property("acquire:state", read_conv=intbool_conv, write_conv=int)
    x_scale = visa_property("horizontal:scale", rw_conv=float)

    # (I think there are better/more specific commands to do this, but it works)
    initiate_single_acquisition = visa_command("fpanel:press single")
    force_trigger = visa_command("fpanel:press forcetrig")

    def trigger_single_acquisition(self):
        self.initiate_single_acquisition()
        self.force_trigger()

    # waveform transfer properties
    waveform_points = visa_property("wfmoutpre:nr_pt", read_only=True, read_conv=int)
    waveform_y_multiplier = visa_property("wfmoutpre:ymult", read_only=True, read_conv=float)
    waveform_y_offset_levels = visa_property("wfmoutpre:yoff", read_only=True, read_conv=float)
    waveform_y_zero = visa_property("wfmoutpre:yzero", read_only=True, read_conv=float)
    waveform_y_unit = visa_property("wfmoutpre:yunit", read_only=True, read_conv=str_conv)

    waveform_x_increment = visa_property("wfmoutpre:xincr", read_only=True, read_conv=float)
    waveform_x_zero = visa_property("wfmoutpre:xzero", read_only=True, read_conv=float)
    waveform_x_unit = visa_property("wfmoutpre:xunit", read_only=True, read_conv=str_conv)

    def initialize_waveform_transfer(self, channel_id, start=1, stop=None):
        self.instr.write(f"data:source ch{channel_id}")
        self.instr.write(f"data:start {start}")
        if stop is None:
            # default to full waveform
            stop = self.trace_points
        self.instr.write(f"data:stop {stop}")
        self.instr.write("data:encdg fast")
        self.instr.write("data:width 2")
        self.instr.write("header 0")

    def do_waveform_transfer(self):
        wfm_raw = self.instr.query_binary_values("curve?", datatype='h', is_big_endian=True, container=np.array)
        wfm_converted = ((wfm_raw - self.waveform_y_offset_levels) * self.waveform_y_multiplier) + self.waveform_y_zero
        time_axis = (np.arange(self.waveform_points) * self.waveform_x_increment) + self.waveform_x_zero

        metadata = {
            "x_unit": self.waveform_x_unit,
            "x_label": f"time",
            "y_unit": self.waveform_y_unit,
            "y_label": f"signal",
        }
        data_obj = pylabframe.data.NumericalData(wfm_converted, x_axis=time_axis, metadata=metadata)
        return data_obj

    def acquire_channel_waveform(self, channel_id, start=1, stop=None):
        self.initialize_waveform_transfer(channel_id, start=start, stop=stop)
        wfm = self.do_waveform_transfer()
        return wfm

    # channel properties
    class Channel:
        def __init__(self, channel, device):
            self.channel_id = channel
            self.query_params = {'channel_id':  channel}
            self.device: "TektronixScope" = device
            self.instr = self.device.instr

        y_scale = visa_property("ch{channel_id}:scale", rw_conv=float)
        offset = visa_property("ch{channel_id}:offset", rw_conv=float)
        termination = visa_property("ch{channel_id}:termination", rw_conv=float)
        inverted = visa_property("ch{channel_id}:invert", read_conv=intbool_conv, write_conv=int)

        mean = visa_property("measu:meas{channel_id}:mean", read_only=True, read_conv=float)

        def acquire_waveform(self, start=1, stop=None):
            return self.device.acquire_channel_waveform(self.channel_id, start=start, stop=stop)

    # trace saving to file and file handling
    save_trace_to_file = visa_command('save:waveform ch{channel_id},"{file_name}"')
    save_setup_to_file = visa_command('save:setup "{file_name}"')
    transfer_file_content = visa_query('filesystem:readfile "{file_name}"', binary=True)

    def save_file_content(self, source_file_name, dest_file_name, dest_exist_ok=False):
        if not dest_exist_ok and os.path.exists(dest_file_name):
            raise FileExistsError(dest_file_name)
        with open(dest_file_name, "wb") as dest_f:
            file_data = self.transfer_file_content(file_name=source_file_name)
            dest_f.write(file_data)
