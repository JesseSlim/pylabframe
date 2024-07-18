pyLabFrame
==========

pyLabFrame is a Python package to help you interact with laboratory instruments and measurement data.

Description
-----------

The goal of pyLabFrame is to provide a coherent framework to help (physics) researchers do their work in the lab.
In essence, it allows you to control your `lab frame`_ in just a few lines of Python!

For example, with the following code, we can step the wavelength of our laser while saving an oscilloscope trace for every point:

.. code:: python

    import numpy as np
    import time

    import pylabframe as lab
    from pylabframe.hw import device                        # load hardware modules
    from pylabframe.hw.drivers import santecvisa, tekvisa   # for type hinting

    lab.config.use('experiment.toml')                       # load configuration file with device addresses

    # connect to devices
    # type hints give us auto-complete in most IDEs
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

That's all the code you need! The only thing still left is to specify the connection addresses of our instruments in the file ``experiment.toml``:

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
- device-specific modules
    * pyrpl (RedPitaya)

Installation
------------

Installation is easy! pyLabFrame is available on PyPI, the Python package repository.
First, make sure that the packages pyLabFrame needs are installed.
In particular, if you want to control lab instruments, make sure that ``pyvisa`` and any other relevant packages for your devices are installed using your favourite package manager (e.g. ``pip`` or ``conda``).

Install pyLabFrame using pip:

    $ pip install pylabframe
