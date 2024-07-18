import numpy as np
import time

import pylabframe as lab
from pylabframe.hw import device                            # load hardware modules
from pylabframe.hw.drivers import santecvisa, tekvisa       # for type hinting

lab.config.use('experiment.toml')                           # load configuration file with device addresses

# connect to devices
laser: santecvisa.TSL = device.get_device('laser')
scope: tekvisa.TektronixScope = device.get_device('scope')

wavelengths = np.linspace(1550., 1560., num=11)

for i, wl in enumerate(wavelengths):
    # set new wavelength and wait a little
    laser.wavelength = wl
    time.sleep(0.2)

    # trigger scope and transfer trace on CH1
    scope.trigger_single_acquisition()
    scope.wait_until_done()
    tr = scope.acquire_channel_waveform(1)

    # store relevant experimental parameters for this measurement and save the trace
    tr.metadata['laser_wavelength'] = wl
    tr.save_npz(f"trace_pt{i}.npz")  # a timestamp is automatically prepended to the file name
