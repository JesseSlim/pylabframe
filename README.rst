pyLabFrame
==========

..
    .. image:: https://github.com/JesseSlim/pylabframe/blob/main/docs/source/_static/pylabframe-v1.png?raw=true
           :width: 25%


pyLabFrame is a Python package to help you interact with laboratory instruments and measurement data.

Description
-----------

pyLabFrame provides a coherent framework to help (physics) researchers do their work in the lab.
In essence, it allows you to control your `lab frame`_ in just a few lines of Python!

pyLabFrame stands on the shoulders of giants: it is built on top of some of the awesome scientific packages available in the Python ecosystem.
All of the heavy lifting is done by packages such as ``numpy``, ``scipy`` and ``pyvisa``.
pyLabFrame just provides a coherent interface, as well as easy-to-use *device drivers*.

pyLabFrame includes components to help you with the following tasks:

* Instrument control
* Data acquisition
* Data storage and retrieval
* Fitting
* Visualisation

.. _`lab frame`: https://en.wikipedia.org/wiki/Local_reference_frame#Laboratory_frame

Design philosophy
^^^^^^^^^^^^^^^^^
pyLabFrame is designed to be clean, consistent and helpful. It follows a few design principles:

* **Modular**. pyLabFrame offers a lot of options, but you don't have to use all of them. Already have some code to plot your data? Great! No need to throw that out.
* **Lightweight**. pyLabFrame is a thin wrapper on top of widely-used packages such as ``numpy`` and ``pyvisa``. You can easily access the underlying objects if you want to
* **Unobtrusive**. pyLabFrame will only do what you tell it to do. No secret shenanigans behind the scenes.
* **Extensible**. Everyone's needs are different. pyLabFrame tries to be clean, uncomplicated and thus easily extensible -- even if you're not a coder at heart. In terms of advanced programming concepts, pyLabFrame strives to use *just the right amount of magic*. Enough to enable elegant code, but not too much for a nonprofessional coder to understand.

Example
-------

To showcase pyLabFrame's potential, let's go through an example. Imagine an experiment where we want to 1) step the wavelength of our laser, and for every point 2) save a trace from our spectrum analyser, 3) fit the data with a Lorentzian, and 4) save a plot of the data and fit. We can do all of that with just a few lines of code.

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

Next, we'll connect to our instruments and set them up for the experiment.

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

That's all the code you need!

How does pyLabFrame know to connect to our instruments? The only thing still left is to specify the connection info of our instruments in the file ``experiment.toml``:

.. code:: toml

    [devices]
        [devices.scope]
        driver = "tekvisa.TektronixScope"
        address = "USB0::0x0699::0x0413::C012345::INSTR"

        [devices.laser]
        driver = "santecvisa.TSL"
        address = "GPIB0::1::INSTR"

In this example, our instruments are VISA devices that we connect to using `PyVISA`_. If you're using `NI-VISA`_, you can find these addresses in the `NI MAX`_ software.

.. _`PyVISA`: https://github.com/pyvisa/pyvisa
.. _`NI-VISA`: https://pyvisa.readthedocs.io/en/latest/faq/getting_nivisa.html
.. _`NI MAX`: https://www.ni.com/en/support/documentation/supplemental/21/what-is-ni-measurement---automation-explorer--ni-max--.html

Requirements
------------

Basic requirements to work with, analyse and visualise data:

* ``Python``
* ``numpy``
* ``scipy``
* ``matplotlib``

Additional requirements to interface with lab devices:

* ``pyvisa``
* device-specific modules, such as

  * ``pyrpl`` (RedPitaya)

Installation
------------

Installation is easy! pyLabFrame is available on PyPI, the Python package repository.

First, make sure that the packages pyLabFrame needs are installed.
In particular, if you want to control lab instruments, make sure that ``pyvisa`` and any other relevant packages for your devices are installed using your favourite package manager (e.g. ``pip`` or ``conda``).

Then, install pyLabFrame using pip:

    $ pip install pylabframe
