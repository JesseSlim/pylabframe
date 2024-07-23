"""Device drivers to control Keysight (formerly Agilent) equipment."""
import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class KeysightESA(visadevice.VisaDevice):
    class RunModes(SettingEnum):
        """Available run modes.

        .. list-table::

            * - :data:`CONTINUOUS`
              - Continuous
            * - :data:`SINGLE`
              - Single
        """
        CONTINUOUS = "1"
        SINGLE = "0"

    class InstrumentModes(SettingEnum):
        """Available instrument modes.

        .. list-table::

            * - :data:`SPECTRUM_ANALYZER`
              - Spectrum analyzer
            * - :data:`IQ_ANALYZER`
              - IQ analyzer
        """

        SPECTRUM_ANALYZER = "SA"
        IQ_ANALYZER = "BASIC"

    class DetectorModes(SettingEnum):
        """Available detector modes.

        See page 1000 of the EXA Signal Analyzer manual to find out what these modes mean.

        .. list-table::

            * - :data:`NORMAL`
              - Normal
            * - :data:`AVERAGE`
              - Average
            * - :data:`SAMPLE`
              - Sample
            * - :data:`POSITIVE_PEAK`
              - Positive peak
            * - :data:`NEGATIVE_PEAK`
              - Negative peak
            * - :data:`QUASI_PEAK`
              - Quasi peak
            * - :data:`EMI_AVERAGE`
              - EMI average
            * - :data:`RMS_AVERAGE`
              - Root-mean-square (RMS) average
        """
        NORMAL = "NORM"
        AVERAGE = "AVER"
        POSITIVE_PEAK = "POS"
        SAMPLE = "SAMP"
        NEGATIVE_PEAK = "NEG"
        QUASI_PEAK = "QPE"
        EMI_AVERAGE = "EAV"
        RMS_AVERAGE = "RA"

    class YUnits(SettingEnum):
        """Available units for the signal analyser's y-axis.

        .. list-table::

            * - :data:`dBm`
            * - :data:`dBmV`
            * - :data:`dBmA`
            * - :data:`V`
            * - :data:`W`
            * - :data:`A`
            * - :data:`dBuV`
            * - :data:`dBuA`
            * - :data:`dBpW`
            * - :data:`dBuVm`
            * - :data:`dBuAm`
            * - :data:`dBPT`
            * - :data:`dBG`
        """
        dBm = "DBM"
        dBmV = "DBMV"
        dBmA = "DBMA"
        V = "V"
        W = "W"
        A = "A"
        dBuV = "DBUV"
        dBuA = "DBUA"
        dBpW = "DBPW"
        dBuVm = "DBUVM"
        dBuAm = "DBUAM"
        dBPT = "DBPT"
        dBG = "DBG"

    class ScaleType(SettingEnum):
        """Available scale types for the y-axis

        .. list-table::

            * - :data:`LOG`
              - Logarithmic
            * - :data:`LINEAR`
              - Linear
        """
        LOG = "LOG"
        LINEAR = "LIN"

    class TraceAverageModes(SettingEnum):
        """Available modes for trace averaging

        .. list-table::

            * - :data:`RMS`
              - Root-mean-square avaraging
            * - :data:`LOG_POWER`
              - Log(power) averaging
            * - :data:`VOLTAGE`
              - Voltage (linear) averaging
        """
        RMS = "RMS"
        LOG_POWER = "LOG"
        VOLTAGE = "SCAL"

    METADATA_FIELDS = [
        "center_frequency",
        "span",
        "start_frequency",
        "stop_frequency",
        "rbw",
        "vbw",
        "detector",
        "sweep_time",
        "trace_points",
        "trace_averaging",
        "trace_average_count",
        "trace_average_mode",
        "y_unit"
    ]
    """""" # remove superclass docstring

    def __init__(self, *args, read_termination='\n', write_termination='\n', **kwargs):
        super().__init__(*args, read_termination=read_termination, write_termination=write_termination, **kwargs)

    # access guard methods
    def require_iq_mode(self):
        """Access guard to check if instrument is in IQ mode. Raises :external:exc:`RuntimeError` if it's not."""
        if self.instrument_mode != self.InstrumentModes.IQ_ANALYZER:
            raise RuntimeError("Instrument is not in IQ mode")

    def require_sa_mode(self):
        """Access guard to check if instrument is in Spectrum Analyser mode. Raises :external:exc:`RuntimeError` if it's not."""
        if self.instrument_mode != self.InstrumentModes.SPECTRUM_ANALYZER:
            raise RuntimeError("Instrument is not in spectrum analyzer mode")

    # access guard shorthands
    SA_visa_property = lambda *args, access_guard=require_sa_mode, **kw: visa_property(*args, **kw,
                                                                                       access_guard=access_guard)
    """Define VISA property that is only accessible in Spectrum Analyser mode."""
    IQ_visa_property = lambda *args, access_guard=require_iq_mode, **kw: visa_property(*args, **kw,
                                                                                       access_guard=access_guard)
    """Define VISA property that is only accessible in IQ mode."""

    instrument_mode = visa_property("inst:sel", dtype=InstrumentModes)
    """Instrument mode. Options listed in :class:`~InstrumentModes`."""
    run_mode = visa_property("initiate:continuous", dtype=RunModes)
    """Run mode. Options listed in :class:`~RunModes`"""

    center_frequency = visa_property("sense:freq:center", dtype=float)
    """Center frequency (Hz) for signal analysis. Available in both SA and IQ mode."""

    span = SA_visa_property("sense:freq:span", dtype=float)
    """Frequency span (Hz) for spectrum analysis. Alternatively, frequency range can be set using :attr:`~start_frequency` and :attr:`~stop_frequency`."""
    start_frequency = SA_visa_property("sense:freq:start", dtype=float)
    """Start frequency (Hz) for spectrum analysis. Alternatively, frequency range can be set using :attr:`~center_frequency` and :attr:`~span`."""
    stop_frequency = SA_visa_property("sense:freq:stop", dtype=float)
    """Stop frequency (Hz) for spectrum analysis. Alternatively, frequency range can be set using :attr:`~center_frequency` and :attr:`~span`."""
    rbw = SA_visa_property("sense:band", dtype=float)
    """Resolution bandwidth (Hz)."""
    vbw = SA_visa_property("sense:band:video", dtype=float)
    """Video bandwidth (Hz)."""
    auto_vbw = SA_visa_property("sense:band:video:auto", dtype=bool)
    """Enable automatic selection of video bandwidth."""

    detector = SA_visa_property("sense:detector:trace", dtype=DetectorModes)
    """Detector mode to be used for spectrum analysis. Options listed in :class:`~DetectorModes`."""

    sweep_time = SA_visa_property("sense:sweep:time", dtype=float)
    """(Estimated) sweep time."""
    trace_points = SA_visa_property("sense:sweep:points", dtype=int)
    """Number of points to be taken during a sweep."""
    trace_average_count = SA_visa_property("sense:average:count", dtype=int)
    """Number of traces to average."""
    trace_averaging = SA_visa_property("sense:average:state", dtype=bool)
    """Enable trace averaging."""
    trace_average_mode = SA_visa_property("sense:average:type", dtype=TraceAverageModes)
    """Mode to be used for trace averaging. Options listed in :class:`~TraceAverageModes`."""
    auto_trace_average_mode = SA_visa_property("sense:average:type:auto", dtype=bool)
    """Enable automatic selection of trace averaging mode."""

    y_unit = SA_visa_property("unit:power", dtype=YUnits)
    """Unit to be used for y-axis of trace. Options listed in :class:`~YUnits`."""
    y_scale = SA_visa_property("display:window:trace:y:spacing", dtype=ScaleType)
    """Scale type to be used for y-axis of trace (linear, logarthmic). Options listed in :class:`~ScaleType`."""

    start_trace = visa_command("initiate:immediate")
    """Start the acquisition of a trace."""
    # start_measurement_and_wait = visa_command("initiate:immediate", wait_until_done=True)

    def initialize_trace_transfer(self):
        """Set the instrument up to transfer trace data. No need to call directly -- automatically called by :meth:`~acquire_trace`."""
        self.instr.write("format:data real,64")
        self.instr.write("format:border norm")

    def start_single_trace(self):
        """Start the acquistion of a single trace."""
        self.run_mode = self.RunModes.SINGLE
        self.start_trace()

    # TODO: is this the best name for this function?
    def acquire_trace(self, trace_num=1, collect_metadata=True, psd=False, restart=True, wait_until_done=True) -> pylabframe.data.NumericalData:
        """Transfer a spectrum trace to the PC. Optionally starts a new acquisition.

        :param trace_num: Index of the trace to transfer, defaults to 1.
        :type trace_num: int, optional
        :param collect_metadata: If True (default), collect and store the current acquisition parameters.
        :type collect_metadata: bool, optional
        :param psd: If True, convert spectrum to power spectral density, by converting to a linear scale and dividing by the :attr:`~rbw`. Defaults to `False`.
        :type psd: bool, optional
        :param restart: If True (default), start a new acquisition.
        :type restart: bool, optional
        :param wait_until_done: If True (default), wait for acquistion to be finished.
        :type wait_until_done: bool, optional
        :return: A :class:`~pylabframe.data.NumericalData` object holding the spectrum data, frequency axis (Hz) and metadata.
                 If ``psd`` is False, the returned data is a spectrum on a logarithmic scale (dBm).
                 If ``psd`` is True, the returned data is a spectral density on a linear scale (W/Hz).
        """
        self.initialize_trace_transfer()
        if restart:
            self.start_single_trace()
        if wait_until_done:
            self.wait_until_done()
        raw_data = self.instr.query_binary_values(f"trace:data? trace{trace_num}", datatype="d", is_big_endian=True, container=np.array)

        if collect_metadata:
            metadata = self.collect_metadata()
        else:
            metadata = {}

        if self.span == 0.0:
            # we're zero-spanning, x-axis is time axis
            x_axis = np.linspace(0.0, self.sweep_time, num=self.trace_points)
            metadata["x_unit"] = 's'
            metadata['x_label'] = 'time'
        else:
            x_axis = np.linspace(self.start_frequency, self.stop_frequency, num=self.trace_points)
            metadata["x_unit"] = 'Hz'
            metadata["x_label"] = "frequency"

        metadata["y_label"] = 'signal'

        if psd:
            sig_power = 1e3 * np.power(10., raw_data / 10.0)
            sig_psd = sig_power / self.rbw
            trace_sig = sig_psd
            metadata["y_unit"] = 'W/Hz'
        else:
            trace_sig = raw_data
            metadata["y_unit"] = 'dBm'

        data_obj = pylabframe.data.NumericalData(trace_sig, x_axis=x_axis, metadata=metadata)
        return data_obj

    ## IQ MODE SETTINGS
    configure_iq_waveform = visa_command("configure:waveform")
    """Configure the instrument in IQ waveform mode."""
    iq_bw = IQ_visa_property("waveform:dif:bandwidth", dtype=float)
    """Analysis bandwidth (Hz) in IQ mode."""
    iq_acquisition_time = IQ_visa_property("sense:waveform:sweep:time", dtype=float)
    """Acquisition time (s) for acquiring a trace in IQ mode."""

    def enable_iq_waveform_mode(self):
        """Switch the instrument to IQ waveform mode."""
        self.instrument_mode = self.InstrumentModes.IQ_ANALYZER
        self.configure_iq_waveform()

    def acquire_iq_waveform(self, return_complex=False, restart=True, wait_until_done=True):
        """Transfer an IQ trace to the PC. Optionally starts a new acquisition.

        :param return_complex: If True, returns the IQ data as complex numbers. If False (default), return I, Q and log(envelope) as real numbers.
        :type return_complex: bool, optional
        :param restart: If True (default), start a new acquisition.
        :type restart: bool, optional
        :param wait_until_done: If True (default), wait for acquistion to be finished.
        :type wait_until_done: bool, optional
        :return: A :class:`~pylabframe.data.NumericalData` object holding the IQ trace data, time axis (s) and metadata.
                 If ``return_complex`` is False, the returned data is 2-dimensional, with time (s) on the first axis and [I (linear), Q (linear), envelope (log)] data on the second axis.
                 If ``return_complex`` is True, the returned data is a 1-dimensional array of complex amplitudes :code:`I + 1j*Q` with time (s) on the first axis.
        """
        self.initialize_trace_transfer()
        if restart:
            self.start_single_trace()
        if wait_until_done:
            self.wait_until_done()
        raw_data = self.instr.query_binary_values(f"fetch:waveform0?", datatype="d", is_big_endian=True,
                                                  container=np.array)
        envelope_data = self.instr.query_binary_values(f"fetch:waveform2?", datatype="d", is_big_endian=True,
                                                  container=np.array)
        statistics_data = self.instr.query_binary_values(f"fetch:waveform1?", datatype="d", is_big_endian=True,
                                                  container=np.array)
        i_data = raw_data[::2]
        q_data = raw_data[1::2]

        time_axis = np.linspace(0, self.iq_acquisition_time, len(i_data))

        metadata = {
            "center_frequency": self.center_frequency,
            "iq_bw": self.iq_bw,
            "envelope_data": envelope_data,
            "statistics_data": statistics_data,
            "raw_data": raw_data
        }

        if return_complex:
            c_data = i_data + 1j * q_data
            data_obj = pylabframe.data.NumericalData(c_data, x_axis=time_axis, axes_names=['time'], metadata=metadata)
        else:
            data_obj = pylabframe.data.NumericalData([i_data, q_data, envelope_data], transpose=True, x_axis=time_axis, y_axis=['i', 'q', 'log_envelope'], axes_names=['time', 'quadrature'], metadata=metadata)

        return data_obj

    ## COMPLETE MEASUREMENT FUNCTIONS
    # ===============================

    def measure_spectrum(
            self, spectrum_center_freq, spectrum_span, points, avgs=100, rbw=None, vbw=None, average_mode=TraceAverageModes.RMS,
            esa_detector=DetectorModes.AVERAGE
    ):
        """Convenience function to do a spectrum measurement. Sets all relevant parameters, starts the acquisition and transfers the trace.

        :param float spectrum_center_freq: Center frequency (Hz).
        :param float spectrum_span: Frequency span (Hz).
        :param int points: Number of sweep points.
        :param avgs: Number of trace averages, defaults to 100.
        :type avgs: int, optional
        :param rbw: Resolution bandwidth (Hz). If None (default), no change. If True, ``rbw`` is set to ``spectrum_span / points``.
        :type rbw: float, True or None
        :param vbw: Video bandwidth (Hz). If None (default), no change. If True, ``rbw`` is set to ``spectrum_span / points``.
        :type vbw: float, True or None
        :param average_mode: Mode for trace averaging, defaults to :data:`~TraceAverageModes.RMS`.
        :type average_mode: :class:`TraceAverageModes`
        :param esa_detector: Detector mode, defaults to :data:`~DetectorModes.AVERAGE`.
        :type esa_detector: :class:`DetectorModes`
        :return: A :class:`~pylabframe.data.NumericalData` object holding the spectrum data, frequency axis (Hz) and metadata.
        """
        self.instrument_mode = self.InstrumentModes.SPECTRUM_ANALYZER
        self.span = spectrum_span
        self.center_frequency = spectrum_center_freq
        self.trace_points = points
        self.trace_average_mode = average_mode
        self.trace_average_count = avgs
        self.trace_averaging = True
        self.detector = esa_detector
        if rbw is not None:
            if rbw is True:
                self.rbw = spectrum_span / points
            else:
                self.rbw = rbw
        if vbw is not None:
            if vbw is True:
                self.vbw = spectrum_span / points
            else:
                self.vbw = vbw

        return self.acquire_trace()
