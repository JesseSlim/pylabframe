import string
import numpy as np

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


def to_onoff(value, none_is_off=False):
    if value is not None:
        if value:
            return "ON"
        else:
            return "OFF"
    if none_is_off:
        return "OFF"
    return None


def remove_units(val):
    return float(val.rstrip(string.ascii_letters))


def from_onoff(val):
    return True if val == "ON" else False


def str_or_none(val):
    return str(val) if val is not None else None


def params_dict_to_str(params_dict):
    params = []
    for k, v in params_dict.items():
        if v is not None:
            params += [k, v]

    params_str = ",".join(map(str, params))
    return params_str


class SDG(visadevice.VisaDevice):
    """
    Device driver Siglent SDG series signal generators.

    WARNING: the frequencies as returned by the signal generator to SCPI queries have a lower precision than how they
    are displayed on the device screen and set internally. It seems that setting them via SCPI does work with the same precision
    """
    def __init__(self, *args, read_termination='\n', write_termination='\n', **kwargs):
        super().__init__(*args, read_termination=read_termination, write_termination=write_termination, **kwargs)

    class WaveTypes(SettingEnum):
        SINE = "SINE"
        SQUARE = "SQUARE"
        RAMP = "RAMP"
        PULSE = "PULSE"
        NOISE = "NOISE"
        ARBITRARY = "ARB"
        DC = "DC"
        PRBS = "PRBS"
        IQ = "IQ"

    class BurstModes(SettingEnum):
        GATED = "GATE"
        N_CYCLES = "NCYC"

    class TriggerSources(SettingEnum):
        EXTERNAL = "EXT"
        INTERNAL = "INT"
        MANUAL = "MAN"

    class Polarities(SettingEnum):
        NEGATIVE = "NEG"
        POSITIVE = "POS"

    class TriggerModes(SettingEnum):
        RISE = "RISE"
        FALL = "FALL"
        OFF = "OFF"

    def set_output(self, ch, on=None, load=None, invert_polarity=None):
        params = []
        if on is not None:
            params.append(to_onoff(on))
        if load is not None:
            params.append("LOAD")
            if load == "HZ" or load is False:
                params.append("HZ")
            else:
                params.append(f"{load:d}")
        if invert_polarity is not None:
            params.append("PLRT")
            params.append("INVT" if invert_polarity else "NOR")

        self.instr.write(f"C{ch}:OUTP " + ",".join(map(str, params)))

    def get_output(self, ch):
        res = self.instr.query(f"C{ch}:OUTP?")
        res = res.split(" ")[1]
        res = res.split(",")

        state = {
            "on": None,
            "load": None,
            "invert_polarity": None
        }

        # process the returned string piece by piece
        while len(res) > 0:
            next = res.pop(0)
            if next == "ON":
                state["on"] = True
            elif next == "OFF":
                state["on"] = False
            elif next == "LOAD":
                load = res.pop(0)
                if load == "HZ":
                    state["load"] = False
                else:
                    state["load"] = int(load)
            elif next == "PLRT":
                plrt = res.pop(0)
                if plrt == "INVT":
                    state["invert_polarity"] = True
                elif plrt == "NOR":
                    state["invert_polarity"] = False
            else:
                # for now, we ignore parameters that we don't understand
                pass

        return state

    def set_wave(self, ch,
                 wave_type: WaveTypes = None, freq=None, period=None, amplitude_Vpp=None, offset=None,
                 ramp_symmetry=None, duty_cycle=None, phase=None, noise_stddev=None,
                 noise_mean=None, width=None, rise_time=None, fall_time=None, delay=None,
                 high_level=None, low_level=None, noise_band_filter=None, noise_bandwidth=None,
                 amplitude_Vrms=None, amplitude_dBm=None, max_output_amplitude=None
                 ):
        params_dict = {
            "WVTP": str_or_none(wave_type),
            "FRQ": freq,
            "PERI": period,
            "AMP": amplitude_Vpp,
            "OFST": offset,
            "SYM": ramp_symmetry,
            "DUTY": duty_cycle,
            "PHSE": phase,
            "STDEV": noise_stddev,
            "MEAN": noise_mean,
            "WIDTH": width,
            "RISE": rise_time,
            "FALL": fall_time,
            "DLY": delay,
            "HLEV": high_level,
            "LLEV": low_level,
            "BANDSTATE": to_onoff(noise_band_filter),
            "BANDWIDTH": noise_bandwidth,
            "AMPVRMS": amplitude_Vrms,
            "AMPDBM": amplitude_dBm,
            "MAX_OUTPUT_AMP": max_output_amplitude
        }

        params_str = params_dict_to_str(params_dict)

        self.instr.write(f"C{ch}:BSWV " + params_str)

    def get_wave(self, ch):
        res_str = self.instr.query(f"C{ch}:BSWV?")
        return self._interpret_wave_params(res_str)

    @classmethod
    def _interpret_wave_params(cls, res_str):
        params_dict = {
            "WVTP": ("wave_type", cls.WaveTypes),
            "FRQ": ("freq", remove_units),
            "PERI": ("period", remove_units),
            "AMP": ("amplitude_Vpp", remove_units),
            "OFST": ("offset", remove_units),
            "SYM": ("ramp_symmetry", remove_units),
            "DUTY": ("duty_cycle", remove_units),
            "PHSE": ("phase", remove_units),
            "STDEV": ("noise_stddev", remove_units),
            "MEAN": ("noise_mean", remove_units),
            "WIDTH": ("width", remove_units),
            "RISE": ("rise_time", remove_units),
            "FALL": ("fall_time", remove_units),
            "DLY": ("delay", remove_units),
            "HLEV": ("high_level", remove_units),
            "LLEV": ("low_level", remove_units),
            "BANDSTATE": ("noise_band_filter", from_onoff),
            "BANDWIDTH": ("noise_bandwidth", remove_units),
            "AMPVRMS": ("amplitude_Vrms", remove_units),
            "AMPDBM": ("amplitude_dBm", remove_units),
            "MAX_OUTPUT_AMP": ("max_output_amplitude", remove_units)
        }

        res = res_str.split(" ")[-1]
        res = res.split(",")

        wave_params = {}

        while len(res) > 0:
            key = res.pop(0)
            val = res.pop(0)

            # apply specified conversion function
            if key in params_dict:
                param_name, conv_func = params_dict[key]
                wave_params[param_name] = conv_func(val)

        return wave_params

    def get_burst(self, ch):
        params_dict = {
            "STATE": ("state", from_onoff),
            "PRD": ("burst_period", remove_units),
            "STPS": ("start_phase", remove_units),
            "GATE_NCYC": ("burst_mode", self.BurstModes),
            "TRSR": ("trigger_source", self.TriggerSources),
            "DLAY": ("burst_delay", remove_units),
            "PLRT": ("gate_polarity", self.Polarities),
            "TRMD": ("trigger_mode", self.TriggerModes),
            "EDGE": ("trigger_edge", self.TriggerModes)
        }

        res_str = self.instr.query(f"C{ch}:BTWV?")

        res = res_str.split(" ")[1]
        res = res.split(",")

        burst_params = {}

        while len(res) > 0:
            key = res.pop(0)
            val = res.pop(0)

            # apply specified conversion function
            if key in params_dict:
                param_name, conv_func = params_dict[key]
                burst_params[param_name] = conv_func(val)
            elif key == 'CARR':
                carrier_str = ",".join([val] + res)
                burst_params["carrier_wave"] = self._interpret_wave_params(carrier_str)
                res = []

        return burst_params

    def set_burst(self, ch, state=None, burst_mode=None,
                  trigger_source=None, gate_polarity=None, start_phase=None,
                  burst_period=None, burst_delay=None, trigger_mode=None, trigger_edge=None,
                  # carrier wave parameters
                  wave_type: WaveTypes = None, freq=None, period=None, amplitude_Vpp=None, offset=None,
                  ramp_symmetry=None, duty_cycle=None, phase=None, noise_stddev=None,
                  noise_mean=None, width=None, rise_time=None, fall_time=None, delay=None
                  ):
        params_dict = {
            "STATE": to_onoff(state),
            "PRD": burst_period,
            "STPS": start_phase,
            "GATE_NCYC": str_or_none(burst_mode),
            "TRSR": str_or_none(trigger_source),
            "DLAY": burst_delay,
            "PLRT": str_or_none(gate_polarity),
            "TRMD": str_or_none(trigger_mode),
            "EDGE": str_or_none(trigger_edge)
        }

        carrier_params = {
            "WVTP": str_or_none(wave_type),
            "FRQ": freq,
            "PERI": period,
            "AMP": amplitude_Vpp,
            "OFST": offset,
            "SYM": ramp_symmetry,
            "DUTY": duty_cycle,
            "PHSE": phase,
            "STDEV": noise_stddev,
            "MEAN": noise_mean,
            "WIDTH": width,
            "RISE": rise_time,
            "FALL": fall_time,
            "DLY": delay,
        }

        params_str = params_dict_to_str(params_dict)
        carrier_str = params_dict_to_str(carrier_params)
        if len(carrier_str) > 0:
            carrier_str = "CARR,"+carrier_str

        self.instr.write(f"C{ch}:BTWV " + params_str + carrier_str)
