import numpy as np


class FitResult:
    def __init__(self, popt, pcov, func, infodict):
        self.popt = popt
        self.pcov = pcov
        self.func = func
        self.infodict = infodict


class FitterDefinition:
    param_names = None

    @classmethod
    def func(cls):
        raise None

    @classmethod
    def guesser(cls, data):
        return None

class Lorentzian(FitterDefinition):
    param_names = ["area", "linewidth", "center", "offset"]

    @classmethod
    def func(cls, x, area=1., linewidth=1., center=0., offset=0.):
        return offset + (2/np.pi) * area * linewidth / (4*(x-center)**2 + linewidth**2)
