Instrument control
==================

Functions to manage and control instruments can be found under :mod:`pylabframe.hw`.
The main, general-purpose modules are :mod:`pylabframe.hw.device` and :mod:`pylabframe.hw.visadevice`.
Reference documentation for these modules can be found below in `Generic interfaces`_.

Device drivers
--------------

.. toctree::
   :hidden:

   drivers/tekvisa
   drivers/keysightvisa
   drivers/siglentvisa
   drivers/rigolvisa
   drivers/redpitaya
   drivers/santecvisa
   drivers/thorlabsvisa

Drivers for specific instruments can be found under :mod:`pylabframe.hw.drivers`.
Currently, pyLabFrame has built-in support for the following devices (coincidentally the ones that I use in the lab).
Click on the links in the table below for driver documentation:

.. currentmodule:: pylabframe.hw.drivers

.. list-table::
    :widths: 25 25
    :header-rows: 1

    * - Instrument
      - pyLabFrame class
    * - **Oscilloscopes**
      -
    * - Tektronix (multiple models)
      - :class:`tekvisa.TektronixScope`
    * - **Electronic signal analysers**
      -
    * - Keysight ESA (e.g. N9010A)
      - :class:`keysightvisa.KeysightESA`
    * - **Signal generators**
      -
    * - Siglent SDG
      - :class:`siglentvisa.SDG`
    * - Rigol DG1022
      - :class:`rigolvisa.RigolDG1022` (incomplete)
    * - **Digital signal processors**
      -
    * - RedPitaya STEMlab
      - :class:`redpitaya.RedPitaya`
    * - **Lasers**
      -
    * - Santec TSL
      - | :class:`santecvisa.TSL` --> alias for :class:`santecvisa.TSL_SCPICommands`
        |
        | Santec lasers can be controlled by two command sets.
        | Industry-standard SCPI: :class:`santecvisa.TSL_SCPICommands`
        | Santec's own commands: :class:`santecvisa.TSL_SantecCommands` (for older lasers)
    * - **Power meters**
      -
    * - Thorlabs PM100D
      - :class:`thorlabsvisa.ThorlabsPM100D`

If your equipment is not on the list, do not worry -- it's easy to make your own device drivers.

Generic interfaces
------------------

All ``pylabframe`` device drivers should inherit the class :class:`~pylabframe.hw.device.Device` in module :mod:`pylabframe.hw.device`.
This module also contains the central function :func:`~pylabframe.hw.device.get_device` that opens a connection to any device
specified in the current configuration.

hw.device
^^^^^^^^^

.. automodule:: pylabframe.hw.device
   :special-members: __init__

hw.visadevice
^^^^^^^^^^^^^

.. automodule:: pylabframe.hw.visadevice
   :special-members: __init__
