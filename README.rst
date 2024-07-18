pyLabFrame
==========

pyLabFrame is a Python package to help you interact with laboratory instruments and measurement data.

Description
-----------

The goal of pyLabFrame is to provide a coherent framework to help (physics) researchers do their work in the lab.
In essence, it allows you to control your `lab frame`_ in just a few lines of Python!

Let's go through an example. We are going to 1) step the wavelength of our laser, and for every point 2) save a trace from our spectrum analyser, 3) fit the data with a Lorentzian, and 4) save a plot of the data and fit.

First, we'll import and set up pyLabFrame.

.. code:: python

    import numpy as np
    import matplotlib.pyplot as plt
    import time

    import pylabframe as lab
    from pylabframe.hw import device                            # load hardware modules
    from pylabframe.hw.drivers import santecvisa, keysightvisa  # for type hinting
    from pylabframe.data import fitters

    lab.config.use('experiment.toml')                           # load configuration file with hw addresses

Next, we'll connect to our instruments and set them up for our experiment

.. code:: python

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

Now we're ready to rumble!

.. code:: python

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

That's all the code you need! Pretty neat, right?

But how does pyLabFrame know how to connect to our instruments? The only thing still left is to specify the connection addresses of our instruments in the file ``experiment.toml``:

.. code:: toml

    [devices]
        [devices.scope]
        driver = "tekvisa.TektronixScope"
        address = "USB0::0x0699::0x0413::C012345::INSTR"

        [devices.laser]
        driver = "santecvisa.TSL"
        address = "GPIB0::1::INSTR"

Easy, right?

pyLabFrame stands on the shoulders of giants: it is built on top of some awesome scientific packages available in the Python ecosystem.
All of the heavy lifting is done by packages such as ``numpy``, ``scipy`` and ``pyvisa``.
pyLabFrame just provides a coherent interface, as well as easy-to-use *device drivers*.

.. _`lab frame`: https://en.wikipedia.org/wiki/Local_reference_frame#Laboratory_frame

Requirements
------------

Basic requirements to work with, analyse and visualise data:

- Python
- numpy
- scipy
- matplotlib

Additional requirements to interface with lab devices:

- pyvisa
- device-specific modules, such as
    * pyrpl (RedPitaya)

Installation
------------

Installation is easy! pyLabFrame is available on PyPI, the Python package repository.
First, make sure that the packages pyLabFrame needs are installed.
In particular, if you want to control lab instruments, make sure that ``pyvisa`` and any other relevant packages for your devices are installed using your favourite package manager (e.g. ``pip`` or ``conda``).

Install pyLabFrame using pip:

    $ pip install pylabframe
