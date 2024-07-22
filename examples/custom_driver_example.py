from pylabframe.hw.visadevice import VisaDevice, visa_property, device

class FancyLaser(VisaDevice):
    wavelength = visa_property(":wavelength")

device.register_driver_class("FancyLaser", FancyLaser)
device.register_device("my_laser", driver="FancyLaser", address="USB:123:456")

laser = device.get_device('my_laser')

print(f"Current wavelength: {laser.wavelength}")
laser.wavelength = 1550.0
