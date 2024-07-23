"""Device drivers to control Santec equipment."""

import numpy as np
from enum import Enum

from pylabframe.hw import device, visadevice
from pylabframe.hw.device import str_conv, SettingEnum, intbool_conv
from pylabframe.hw.visadevice import visa_property, visa_command
import pylabframe.data


class TSLEnums:
    """Collection of enumerations for some TSL settings."""

    class OutputTriggerModes(SettingEnum):
        """Available modes for the output trigger timing.

        .. list-table::

            * - :data:`NONE`
              - Output trigger disabled
            * - :data:`STOP`
              - Trigger at end of sweep
            * - :data:`START`
              - Trigger at start of sweep
            * - :data:`STEP`
              - Trigger at every step
        """
        NONE = "+0"
        STOP = "+1"
        START = "+2"
        STEP = "+3"

    class PowerUnit(SettingEnum):
        """Units for the power setting

        .. list-table::

            * - :data:`dBm`
            * - :data:`mW`
        """
        dBm = "0"
        mW = "1"

    class WavelengthUnit(SettingEnum):
        """Units for wavelength display

        .. list-table::

            * - :data:`nm`
            * - :data:`THz`
        """
        nm = "0"
        THz = "1"

    class SweepModes(SettingEnum):
        """Available sweep modes.

        .. list-table::

            * - :data:`STEP_ONE_WAY`
              - Step in one direction only
            * - :data:`SWEEP_ONE_WAY`
              - Sweep in one direction only
            * - :data:`STEP_TWO_WAY`
              - Step in both directions
            * - :data:`SWEEP_TWO_WAY`
              - Sweep in both direction
        """
        STEP_ONE_WAY = "+0"
        SWEEP_ONE_WAY = "+1"
        STEP_TWO_WAY = "+2"
        SWEEP_TWO_WAY = "+3"

    class SCPIModes(SettingEnum):
        """Command set options (for backward compatibility of newer lasers)

        .. list-table::

            * - :data:`TSL_550`
              - Use the SCPI command set as defined for the TSL-550. Available on TSL-550 and TSL-770.
            * - :data:`TSL_770`
              - Use the newer SCPI command set as defined for the TSL-770. Only available on TSL-770.
        """
        TSL_550 = "+0"
        TSL_770 = "+1"


class TSL_SCPICommands(visadevice.VisaDevice, TSLEnums):
    """Driver to communicate with a Santec TSL laser using the SCPI command set"""

    trigger_external = visa_property(":trigger:input:external", dtype=bool)
    """Use external trigger input channel."""
    trigger_standby = visa_property(":trigger:input:standby", dtype=bool)
    """Trigger standby mode. If False, laser operates in normal mode. If True, laser operates in trigger standby mode."""

    trigger_output = visa_property(":trigger:output", dtype=TSLEnums.OutputTriggerModes)
    """Output trigger timing mode. Options listed in :class:`TSLEnums.OutputTriggerModes`"""

    laser_diode_on = visa_property(":power:state", dtype=bool)
    """Enable/disable laser diode."""
    shutter_closed = visa_property(":power:shutter", dtype=bool)
    """Close/open shutter."""

    power_unit = visa_property(":power:unit", dtype=TSLEnums.PowerUnit)
    """Units used to get/set laser power. Options listed in :class:`TSLEnums.PowerUnit`"""
    power = visa_property(":power:level", dtype=float)
    """Laser power setpoint in the units specified by :attr:`power_unit`."""
    power_actual = visa_property(":power:actual:level", dtype=float, read_only=True)
    """Actual laser power (read-only) in the units specified by :attr:`power_unit`."""

    wavelength_display_unit = visa_property(":wavelength:unit", dtype=TSLEnums.WavelengthUnit)
    """Units used for wavelength on the laser display. Options listed in :class:`TSLEnums.WavelengthUnit`"""
    wavelength = visa_property(":wavelength", dtype=float)
    """Laser wavelength setpoint. In :data:`~TSLEnums.SCPIModes.TSL_550` mode, wavelength is in *nanometer*. In :data:`~TSLEnums.SCPIModes.TSL_770` mode, wavelength is in *meter*."""
    frequency = visa_property(":wavelength:frequency", dtype=float)
    """Laser frequency setpoint. In :data:`~TSLEnums.SCPIModes.TSL_550` mode, wavelength is in *terahertz*. In :data:`~TSLEnums.SCPIModes.TSL_770` mode, wavelength is in *hertz*."""
    fine_tuning = visa_property(":wavelength:fine", dtype=float)
    """Piezo voltage setpoint for fine wavelength tuning. Range -100 to 100."""
    disable_fine_tuning = visa_command(":wavelength:fine:disable")
    """Disable the fine-tuning piezo voltage."""

    sweep_wavelength_start = visa_property(":wavelength:sweep:start", dtype=float)
    """Sweep start wavelength. In :data:`~TSLEnums.SCPIModes.TSL_550` mode, wavelength is in *nanometer*. In :data:`~TSLEnums.SCPIModes.TSL_770` mode, wavelength is in *meter*."""
    sweep_wavelength_stop = visa_property(":wavelength:sweep:stop", dtype=float)
    """Sweep stop wavelength. In :data:`~TSLEnums.SCPIModes.TSL_550` mode, wavelength is in *nanometer*. In :data:`~TSLEnums.SCPIModes.TSL_770` mode, wavelength is in *meter*."""
    sweep_wavelength_speed = visa_property(":wavelength:sweep:speed", dtype=float)
    """Sweep start wavelength. In :data:`~TSLEnums.SCPIModes.TSL_550` mode, speed is in *nanometer/second*. In :data:`~TSLEnums.SCPIModes.TSL_770` mode, speed is in *meter/second*."""
    sweep_mode = visa_property(":wavelength:sweep:mode", dtype=TSLEnums.SweepModes)
    """Sweep mode. Options listed in :class:`TSLEnums.SweepModes` """
    sweep_single = visa_command(":wavelength:sweep:state 1")
    """Start a single sweep."""

    scpi_mode = visa_property(":system:communicate:code", dtype=TSLEnums.SCPIModes)
    """Command set to use. Only available on TSL-770. Options listed in :class:`TSLEnums.SCPIModes`."""

    ## define these function for compatibilty with the Santec command class
    def turn_diode_on(self):
        """Turn laser diode on."""
        self.laser_diode_on = True

    def turn_diode_off(self):
        """Turn laser diode off."""
        self.laser_diode_on = False

    def close_shutter(self):
        """Close shutter."""
        self.shutter_closed = True

    def open_shutter(self):
        """Open shutter."""
        self.shutter_closed = False


def santec_property(visa_cmd, dtype=None, read_only=False, **kw):
    kw.setdefault("read_suffix", "")
    kw.setdefault("read_on_write", True)
    kw.setdefault("set_cmd_delimiter", "")
    return visa_property(visa_cmd, dtype=dtype, read_only=read_only, **kw)


class TSL_SantecCommands(visadevice.VisaDevice, TSLEnums):
    """Driver to communicate with a Santec TSL laser using the non-SCPI, Santec-specific command set"""
    turn_diode_on = visa_command("LO")
    turn_diode_off = visa_command("LF")

    wavelength = santec_property("WA", dtype=float)
    frequency = santec_property("FQ", dtype=float)
    fine_tuning = santec_property("FT", dtype=float)
    disable_fine_tuning = visa_command("FTF")

    power = santec_property("LP", dtype=float)

    close_shutter = visa_command("SC")
    open_shutter = visa_command("SO")

    sweep_wavelength_start = santec_property("SS", dtype=float)
    sweep_wavelength_stop = visa_property("SE", dtype=float)
    sweep_wavelength_speed = visa_property("SN", dtype=float)
    # sweep_mode = visa_property("SM", dtype=TSLEnums.SweepModes)
    sweep_single = visa_command("SG1")

    # disable default scpi commands
    status_register = None
    status_byte = None
    clear_status = None


# expose the SCPI commands interface as a "default"
TSL = TSL_SCPICommands
