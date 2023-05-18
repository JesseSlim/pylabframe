import numpy as np
from enum import Enum

from pylabframe.hardware import device, visadevice
from pylabframe.hardware.device import str_conv, SettingEnum, intbool_conv
import pylabframe.data

# helper definition
visa_property = device.VisaDevice.visa_property
visa_command = device.VisaDevice.visa_command


class KeysightESA(visadevice.VisaDevice):
    class RunModes(SettingEnum):
        CONTINUOUS = "1"
        SINGLE = "0"

    class InstrumentModes(SettingEnum):
        SPECTRUM_ANALYZER = "SA"
        IQ_ANALYZER = "BASIC"

    # see page 1000 of the EXA SA manual to find what these modes mean
    class DetectorModes(SettingEnum):
        NORMAL = "NORM"
        AVERAGE = "AVER"
        POSITIVE_PEAK = "POS"
        SAMPLE = "SAMP"
        NEGATIVE_PEAK = "NEG"
        QUASI_PEAK = "QPE"
        EMI_AVERAGE = "EAV"
        RMS_AVERAGE = "RA"

    class YUnits(SettingEnum):
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
        LOG = "LOG"
        LINEAR = "LIN"

    class TraceAverageModes(SettingEnum):
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
        "record_length",
        "trace_averaging",
        "trace_average_count",
        "trace_average_mode",
        "y_unit"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visa_instr.write_termination = '\n'
        self.visa_instr.read_termination = '\n'

    instrument_mode = visa_property("inst:sel", read_conv=InstrumentModes)
    run_mode = visa_property("initiate:continuous", read_conv=RunModes)

    center_frequency = visa_property("sense:freq:center", rw_conv=float)
    span = visa_property("sense:freq:span", rw_conv=float)
    start_frequency = visa_property("sense:freq:start", rw_conv=float)
    stop_frequency = visa_property("sense:freq:stop", rw_conv=float)
    rbw = visa_property("sense:band", rw_conv=float)
    vbw = visa_property("sense:band:video", rw_conv=float)
    auto_vbw = visa_property("sense:band:video:auto", read_conv=intbool_conv, write_conv=int)

    detector = visa_property("sense:detector:trace", read_conv=DetectorModes)

    # acquisition_time = visa_property("sense:acquisition:time", rw_conv=float)
    # record_length = visa_property("sense:acquisition:points", rw_conv=int)
    sweep_time = visa_property("sense:sweep:time", rw_conv=float)
    record_length = visa_property("sense:sweep:points", rw_conv=int)
    trace_average_count = visa_property("sense:average:count", rw_conv=int)
    trace_averaging = visa_property("sense:average:state", read_conv=intbool_conv, write_conv=int)
    trace_average_mode = visa_property("sense:average:type", read_conv=TraceAverageModes)
    auto_trace_average_mode = visa_property("sense:average:type:auto", read_conv=intbool_conv, write_conv=int)

    y_unit = visa_property("unit:power", read_conv=YUnits)
    y_scale = visa_property("display:window:trace:y:spacing", read_conv=ScaleType)

    start_measurement = visa_command("initiate:immediate")
    # start_measurement_and_wait = visa_command("initiate:immediate", wait_until_done=True)

    def initialize_trace_transfer(self):
        self.visa_instr.write("format:data real,64")
        self.visa_instr.write("format:border norm")

    def start_trace(self):
        self.run_mode = self.RunModes.SINGLE
        self.start_measurement()

    def acquire_trace(self, trace_num=1, collect_metadata=True):
        self.initialize_trace_transfer()
        self.start_trace()
        self.wait_until_done()
        raw_data = self.visa_instr.query_binary_values(f"trace:data? trace{trace_num}", datatype="d", is_big_endian=True, container=np.array)

        if collect_metadata:
            metadata = self.collect_metadata()
        else:
            metadata = {}

        if self.span == 0.0:
            # we're zero-spanning, x-axis is time axis
            x_axis = np.linspace(0.0, self.sweep_time, num=self.record_length)
            metadata["x_unit"] = 's'
            metadata['x_label'] = 'time'
        else:
            x_axis = np.linspace(self.start_frequency, self.stop_frequency, num=self.record_length)
            metadata["x_unit"] = 'Hz'
            metadata["x_label"] = "frequency"

        metadata["y_label"] = 'signal'

        data_obj = pylabframe.data.NumericalData(raw_data, x_axis=x_axis, metadata=metadata)
        return data_obj

        return raw_data