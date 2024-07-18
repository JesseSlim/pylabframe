import numpy as np
import matplotlib.pyplot as plt
import time

import pylabframe as lab
from pylabframe.hw import device                            # load hardware modules
from pylabframe.hw.drivers import santecvisa, keysightvisa  # for type hinting
from pylabframe.data import fitters

lab.config.use('experiment.toml')                           # load configuration file with hw addresses

# connect to devices
# type hints give us auto-complete in most IDEs
laser: santecvisa.TSL = device.get_device('laser')
esa: keysightvisa.KeysightESA = device.get_device('esa')

# set up the spectrum analyser
esa.instrument_mode = esa.InstrumentModes.SPECTRUM_ANALYZER
esa.detector = esa.DetectorModes.AVERAGE
esa.center_frequency = 2e6
esa.span = 200e3
esa.rbw = 100.
esa.run_mode = esa.RunModes.SINGLE

wavelengths = np.linspace(1550., 1560., num=11)

for i, wl in enumerate(wavelengths):
    print(f"Starting measurement {i}. Moving laser to wavelength {wl:.1f} nm.")
    # set new wavelength and wait a little
    laser.wavelength = wl
    time.sleep(0.2)

    # trigger spectrum analyser and transfer trace
    trace = esa.acquire_trace(restart=True, wait_until_done=True)

    # store relevant experimental parameters for this measurement and save the trace
    # instrument settings (e.g. resolution bandwidth for a spectrum analyser) are automatically saved
    trace.metadata['laser_wavelength'] = wl
    saved_file = trace.save_npz(f"trace_pt{i}.npz")  # a timestamp is automatically prepended to the file name

    # fit the trace with a log(lorentzian) function
    # initial parameter values for the fit are guessed automatically
    trace_fit = trace.fit(fitters.LogLorentzian)
    trace_fit.summary()  # print a summary of the fit parameters

    # plot the data with the fit and save it along with the data file
    plt.figure()
    trace.plot()
    trace_fit.plot()
    plt.savefig(saved_file[:-3] + ".png")
    plt.close()
