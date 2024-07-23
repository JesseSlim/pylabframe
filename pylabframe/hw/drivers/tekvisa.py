"""Device drivers to control Tektronix equipment."""
import os.path

import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command, visa_query
import pylabframe.data


class TektronixScope(visadevice.VisaDevice):
    """Device driver for Tektronix oscilloscopes.

    Tested with: DPO3034, MSO64"""
    NUM_CHANNELS = 2

    DEFAULT_SETTINGS = {
        "trace_data_encoding": "ribinary",
        "trace_data_width": 2,
        "math_data_encoding": "fpbinary",
        "math_data_width": 4,
    }
    """"""

    class RunModes(SettingEnum):
        """Available run modes.

        .. list-table::

            * - :data:`CONTINUOUS`
              - Continuous
            * - :data:`SINGLE`
              - Single
        """
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
    trace_points = visa_property("horizontal:recordlength", dtype=int, rw_conv=int)
    """Number of trace points"""
    run_mode = visa_property("acquire:stopafter", dtype=RunModes)
    """Run mode. Options listed in :class:`~InstrumentModes`."""
    running = visa_property("acquire:state", dtype=bool)
    """Enable acquisition."""
    x_scale = visa_property("horizontal:scale", dtype=float)
    """X axis scale (s/div)"""
    sample_rate = visa_property("horizontal:mode:samplerate", dtype=float)
    """Sample rate (Hz)"""

    # (I think there are better/more specific commands to do this, but it works)
    initiate_single_acquisition = visa_command("fpanel:press single")
    """Initiate a single acquisition. Equivalent to pressing the 'Single' button."""
    force_trigger = visa_command("fpanel:press forcetrig")
    """Force a trigger event. Equivalent to pressing the 'Force Trigger' button."""

    def trigger_single_acquisition(self):
        """Initiate and force trigger a single acquistion"""
        self.initiate_single_acquisition()
        self.force_trigger()

    # waveform transfer properties
    waveform_points = visa_property("wfmoutpre:nr_pt", read_only=True, read_conv=int)
    """Number of points in the current waveform."""
    waveform_y_multiplier = visa_property("wfmoutpre:ymult", read_only=True, read_conv=float)
    """Y multiplier for the current waveform."""
    waveform_y_offset_levels = visa_property("wfmoutpre:yoff", read_only=True, read_conv=float)
    """Y offset (in levels) for the current waveform."""
    waveform_y_zero = visa_property("wfmoutpre:yzero", read_only=True, read_conv=float)
    """Y zero setting for the current waveform"""
    waveform_y_unit = visa_property("wfmoutpre:yunit", read_only=True, read_conv=str_conv)
    """Y units for the current waveform."""

    waveform_x_increment = visa_property("wfmoutpre:xincr", read_only=True, read_conv=float)
    """X increment size for the current waveform."""
    waveform_x_zero = visa_property("wfmoutpre:xzero", read_only=True, read_conv=float)
    """X zero settings for the current waveform."""
    waveform_x_unit = visa_property("wfmoutpre:xunit", read_only=True, read_conv=str_conv)
    """X units for the current waveform"""


    def acquire_channel_waveform(self, channel_id, start=1, stop=None, math_channel=False):
        """Transfer waveform data to PC.

        :param int channel_id: Index of the channel to be transferred
        :param start: First data point to transfer, defaults to 1.
        :type start: int, optional
        :param stop: Last data point to transfer, defaults to the waveform end.
        :type stop: int or None, optional
        :param bool math_channel: If True, transfer channel MATH<#> rather than voltage channel CH<#>, defaults to `False`.
        :return: A :class:`~pylabframe.data.NumericalData` object holding the waveform data, time axis (s) and metadata.
        """
        self.initialize_waveform_transfer(channel_id, start=start, stop=stop, math_channel=math_channel)
        wfm = self.do_waveform_transfer(math_channel=math_channel)
        return wfm


    def initialize_waveform_transfer(self, channel_id, start=1, stop=None, math_channel=False, encoding=None, data_width=None):
        """Set up the instrument for waveform transfer. Usually no need to call directly -- is called automatically by :meth:`acquire_channel_waveform`

        :param int channel_id: Index of the channel to be transferred
        :param start: First data point to transfer, defaults to 1.
        :type start: int, optional
        :param stop: Last data point to transfer, defaults to the waveform end.
        :type stop: int or None, optional
        :param bool math_channel: If True, transfer channel MATH<#> rather than voltage channel CH<#>, defaults to `False`.
        :param encoding: Data encoding (see Tektronix manual entry for ``data:encdg`` SCPI command), default taken from :attr:`DEFAULT_SETTINGS`
        :type encoding: str or None, optional
        :param data_width: Data width in bytes (see Tektronix manual entry for ``data:width`` SCPI command), default taken from :attr:`DEFAULT_SETTINGS`
        :type data_width: int or None, optional
        """
        if not math_channel:
            self.instr.write(f"data:source ch{channel_id}")
        else:
            self.instr.write(f"data:source math{channel_id}")
        self.instr.write(f"data:start {start}")
        if stop is None:
            # default to full waveform
            stop = self.trace_points
        self.instr.write(f"data:stop {stop}")

        if encoding is None:
            encoding = self.settings['trace_data_encoding'] if not math_channel else self.settings['math_data_encoding']
        if data_width is None:
            data_width = self.settings['trace_data_width'] if not math_channel else self.settings['math_data_width']

        self.instr.write(f"data:encdg {encoding}")
        self.instr.write(f"data:width {data_width}")

        self.instr.write("header 0")

    def do_waveform_transfer(self, math_channel=False):
        """Do the waveform data transfer and convert to the right units. Usually no need to call directly -- is called automatically by :meth:`acquire_channel_waveform`

        :param math_channel: If True, transfer a MATH channel rather than a (voltage) CH channel.
        :return: A :class:`~pylabframe.data.NumericalData` object holding the waveform data, time axis (s) and metadata.
        """
        if not math_channel:
            wfm_raw = self.instr.query_binary_values("curve?", datatype='h', is_big_endian=True, container=np.array)
        else:
            wfm_raw = self.instr.query_binary_values("curve?", datatype="f", is_big_endian=True, container=np.array)

        wfm_converted = ((wfm_raw - self.waveform_y_offset_levels) * self.waveform_y_multiplier) + self.waveform_y_zero
        x_axis = (np.arange(self.waveform_points) * self.waveform_x_increment) + self.waveform_x_zero

        metadata = {
            "x_unit": self.waveform_x_unit,
            "x_label": f"time",
            "y_unit": self.waveform_y_unit,
            "y_label": f"signal",
        }
        data_obj = pylabframe.data.NumericalData(wfm_converted, x_axis=x_axis, metadata=metadata)
        return data_obj

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
    """Save waveform trace to file on the oscilloscope file system.
    
    :keyword channel_id: Index of the voltage channel to save.
    :type channel_id: int
    :keyword file_name: File name on the oscilloscope file system.
    :type file_name: str
    """
    save_setup_to_file = visa_command('save:setup "{file_name}"')
    """Save the current oscilloscope configuration to file on the oscilloscope file system.

    :keyword str file_name: File name on the oscilloscope file system.
    """
    transfer_file_content = visa_query('filesystem:readfile "{file_name}"', binary=True)
    """Transfer a file from the oscilloscope file system to the PC.
    
    :keyword str file_name: File name on the oscilloscope file system.
    :return: A :external:class:`bytes` object containing the binary file contents.
    """

    def save_file_content(self, source_file_name, dest_file_name, dest_exist_ok=False):
        """Transfer a file from the oscilloscope file system and save it to a file on the PC.

        :param str source_file_name: File name on the oscilloscope file system.
        :param str dest_file_name: Destination file name on the PC. Used as-is, no further expanding done by :mod:`pylabframe.data.path`.
        :param bool dest_exist_ok: If False (default), raise :external:exc:`FileExistsError` if file already exists on PC. If True, overwrite the file.
        """
        if not dest_exist_ok and os.path.exists(dest_file_name):
            raise FileExistsError(dest_file_name)
        with open(dest_file_name, "wb") as dest_f:
            file_data = self.transfer_file_content(file_name=source_file_name)
            dest_f.write(file_data)
