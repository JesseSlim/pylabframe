"""Utility functions to work with data originating from Tektronix equipment."""

import numpy as np

def osc_convert_levels_to_voltages(wfm_raw, metadata: dict):
    """Convert the raw level data (16-bit signed ints) returned by the oscilloscope to voltages (64-bit doubles)

    :param wfm_raw: Raw level data
    :param dict metadata: Metadata containing conversion parameters, as set by :meth:`~pylabframe.hw.drivers.tekvisa.acquire_channel_waveform`
    :return: Converted voltage data
    """
    if metadata.get('data_converted', False):
        raise UserWarning("Data seems to have been converted already.")

    wfm_converted = ((wfm_raw - metadata["_wfm_y_offset_levels"]) * metadata["_wfm_y_multiplier"]) + metadata["_wfm_y_zero"]

    return wfm_converted

def osc_construct_time_axis(metadata: dict):
    """Construct the time axis for an oscilloscope trace acquired using :meth:`~pylabframe.hw.drivers.tekvisa.acquire_channel_waveform`.

    :param dict metadata: Metadata containing trace parameters, as set by :meth:`~pylabframe.hw.drivers.tekvisa.acquire_channel_waveform`
    :return: Trace time axis, as a :class:`~numpy.ndarray`
    """
    time_axis = (np.arange(metadata["_wfm_points"]) * metadata["_wfm_x_increment"]) + metadata["_wfm_x_zero"]
    return time_axis
