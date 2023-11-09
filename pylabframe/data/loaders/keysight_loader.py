import numpy as np
from pylabframe.data import NumericalData

def lines_to_array(lines, delim=','):
    return list(map(lambda s: s.split(delim), lines))


def load_esa_spectrum_csv(fname, num_conv_func=float):
    with open(fname) as f:
        csv_lines = f.read().strip().split("\n")

    data_marker_idx = csv_lines.index("DATA")

    state_array = dict(lines_to_array(csv_lines[2:data_marker_idx]))
    data_array = lines_to_array(csv_lines[data_marker_idx + 1:])

    data_array = np.vectorize(num_conv_func)(data_array)

    data_dict = {
        "data_type": csv_lines[0],
        "esa_mode": csv_lines[1],
        "state": state_array,
        "spectrum_x": data_array[:, 0],
        "spectrum_dBm": data_array[:, 1]
    }

    data = NumericalData(data_dict['spectrum_dBm'])

    return data_dict


_alphabet_minus_e = list(range(ord('a'), ord('z') + 1))
_alphabet_minus_e.remove(ord('e'))
_alphabet_minus_e = list(map(chr, _alphabet_minus_e))


def load_esa_iq_csv(fname, num_conv_func=float):
    with open(fname) as f:
        csv_lines = f.read().strip().split("\n")

    # first line that only contains numbers (and the letter e) is the start of the actual data
    # this can probably be optimized by putting it in a regex or so but this'll do for now
    for data_start_idx, line in enumerate(csv_lines):
        if any((c in _alphabet_minus_e) for c in line.lower()):
            continue
        break

    state_array = dict(lines_to_array(csv_lines[2:data_start_idx - 1]))
    data_array = lines_to_array(csv_lines[data_start_idx:])

    data_array = np.array(data_array)

    # the data format for IQ measurement files can be found on page 625 of the IQ mode manual
    # that's because the format seems to match the result format of the SCPI fetch commands
    data_values = data_array[:, 0]
    aux_values = data_array[:, 1]
    envelope_values = data_array[:, 2]

    aux_values = aux_values[aux_values != '']
    envelope_values = envelope_values[envelope_values != '']

    data_values = np.vectorize(num_conv_func)(data_values)
    aux_values = np.vectorize(num_conv_func)(aux_values)
    envelope_values = np.vectorize(num_conv_func)(envelope_values)

    aux_labels = ['sample_dt', 'mean_power', 'mean_power_avg', 'sample_n', 'peak_to_mean_dB', 'max_dBm', 'min_dBm']

    I_volt = data_values[::2]
    Q_volt = data_values[1::2]

    data_dict = {
        "data_type": csv_lines[0],
        "esa_mode": csv_lines[1],
        "state": state_array,
        "I_volt": I_volt,
        "Q_volt": Q_volt,
        "c_volt": I_volt + 1j * Q_volt,
        "envelope_dBm": envelope_values,
    }

    data_dict.update(dict(zip(aux_labels, aux_values)))

    data_dict['sample_n'] = int(data_dict['sample_n'])

    data_dict['sample_ts'] = data_dict['sample_dt'] * np.arange(data_dict['sample_n'])

    return data_dict
