import numpy as np
from enum import Enum, auto


class SpectrumUnits(Enum):
    LOG_POWER = auto()
    LINEAR_POWER = auto()
    LINEAR_AMPLITUDE = auto()

    def is_log(self):
        return (self == self.LOG_POWER)

    def is_lin(self):
        return (self == self.LINEAR_POWER or self == self.LINEAR_AMPLITUDE)


def convert_spectrum_unit(data, from_: SpectrumUnits, to: SpectrumUnits):
    if from_ == to:
        return data

    # first convert to linear power
    if from_ == SpectrumUnits.LINEAR_AMPLITUDE:
        data_linpwr = data**2.
    elif from_ == SpectrumUnits.LOG_POWER:
        data_linpwr = 10.**(data/10.)
    # elif from_ == SpectrumUnits.LOG_AMPLITUDE:
    #     # TODO: check if this is correct?
    #     data_linpwr = 10.**(data/10.)
    elif from_ == SpectrumUnits.LINEAR_POWER:
        data_linpwr = data
    else:
        NotImplementedError(from_)

    if to == SpectrumUnits.LINEAR_POWER:
        return data_linpwr
    elif to == SpectrumUnits.LOG_POWER:
        return 10. * np.log10(data_linpwr)
    elif to == SpectrumUnits.LINEAR_AMPLITUDE:
        return np.sqrt(data_linpwr)
    else:
        NotImplementedError(to)

