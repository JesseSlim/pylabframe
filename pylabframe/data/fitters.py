import numpy as np
import scipy
from .core import NumericalData


class FitResult:
    def __init__(self, popt, pcov, fit_def, infodict):
        self.popt = popt
        self.pcov = pcov
        self.fit_def = fit_def
        self.infodict = infodict


class FitterDefinition:
    param_names = None

    @classmethod
    def func(cls):
        raise None

    @classmethod
    def guess_func(cls, data: NumericalData):
        return None


def fit_def(func, guess_func=None, param_names=None):
    if guess_func is None:
        guess_func = classmethod(guess_func)
    class CustomFitter(FitterDefinition):
        param_names = param_names

        func = func
        guess_func = guess_func


# ================
# helper functions
# ================

def estimate_offset(ydata, n_bins=10, n_avg_lowest=1):
    """Quasi-sophisticated method to estimate the offset on a Trace

    We divide the data up in n_bins (default 10) bins. We calculate the average of every bin,
    and take as our offset estimate, the average of the lowest n_avg_lowest (default 1) bins.

    The idea is that if the peak is narrow compared to the whole span, it will only appear in
    a few of these bins. The high-valued bins containing the peak will be rejected, and the
    rest of the bins can be used as a more reliable way to estimate the offset instead of taking
    the minimum value
    """

    bins = np.array_split(ydata, n_bins)
    avgs = sorted(np.mean(bin_) for bin_ in bins)

    return np.mean(avgs[:n_avg_lowest])


def complex_savgol_filter(x, *args, **kw):
    if np.iscomplexobj(x):
        smooth_real = scipy.signal.savgol_filter(x.real, *args, **kw)
        smooth_imag = scipy.signal.savgol_filter(x.imag, *args, **kw)
        return smooth_real + 1j*smooth_imag
    else:
        return scipy.signal.savgol_filter(x, *args, **kw)


# ===================
# common fit function
# ===================

class PeakedFunction(FitterDefinition):
    @classmethod
    def guess_func(cls, data: NumericalData=None, x=None, y=None, offset=None, smoothing_window=1, smoothing_order=0, closely_spaced=False,
                  halfmax_thrs=0.5, binned_offset_estimation=False, smooth_postprocess=lambda x: x, take_abs=True,
                  smooth_preprocess=lambda x: x):
        """Guess parameters for a single peak"""
        if data is not None:
            x = data.x_axis
            y = data.data_array

        if len(x) != len(y):
            raise ValueError("x and y should have the same number of elements!")

        if smoothing_window > 1:
            smoothed_data = smooth_postprocess(
                complex_savgol_filter(smooth_preprocess(y), smoothing_window, smoothing_order)
            )
        else:
            smoothed_data = y

        if take_abs:
            smoothed_data_abs = np.abs(smoothed_data)
        else:
            smoothed_data_abs = smoothed_data.copy()

        idx_max = np.argmax(smoothed_data_abs)
        x0 = x[idx_max]

        if offset is None:
            if not binned_offset_estimation:
                offset = np.min(smoothed_data_abs)
            else:
                if binned_offset_estimation is True:
                    binned_offset_estimation = {}
                offset = estimate_offset(smoothed_data_abs, **binned_offset_estimation)

        peaked_signal = smoothed_data_abs - offset
        peak_height = peaked_signal[idx_max]

        # we have already smoothed the signal,
        # so, let's find the closest points left and right with half the amplitude
        below_halfmax = peaked_signal < halfmax_thrs * peak_height

        l_halfmax_idx = idx_max - np.argmax(below_halfmax[:idx_max + 1][::-1])
        r_halfmax_idx = idx_max + np.argmax(below_halfmax[idx_max:])

        if l_halfmax_idx == idx_max and r_halfmax_idx == idx_max:
            # this should not occur, because we have subtracted the minimum value already,
            # so there is guaranteed to be a point where signal = 0 < 0.5*max (unless the input is identically zero)
            raise ValueError("Could not find any half-max points")

        # positive x-distances between halfmax points and peak
        dx_l_halfmax = x0 - x[l_halfmax_idx]
        dx_r_halfmax = x[r_halfmax_idx] - x0

        # if there is no half-max point on one side (e.g. the peak is too close to the edge of the sampled data),
        # mirror the half-max point on the other side.
        if np.isclose(dx_l_halfmax, 0.0):
            dx_l_halfmax = dx_r_halfmax
        elif np.isclose(dx_r_halfmax, 0.0):
            dx_r_halfmax = dx_l_halfmax

        # for closely spaced peaks, one of the halfmax points might be obscured by another peak
        # so we take the closest halfmax point. The better solution would be to increase the halfmax threshold
        if closely_spaced:
            hwhm = np.min([dx_l_halfmax, dx_r_halfmax])
        else:
            hwhm = np.mean([dx_l_halfmax, dx_r_halfmax])

        # correct for thresholds that are different than 0.5
        single_peak_y0 = cls.single_peak_func(0.0)
        dx_0_5 = scipy.optimize.minimize_scalar(lambda s: (cls.single_peak_func(s) / single_peak_y0 - 0.5) ** 2,
                                                bounds=(0, 1e3), method='bounded').x
        dx_thrs = scipy.optimize.minimize_scalar(lambda s: (cls.single_peak_func(s) / single_peak_y0 - halfmax_thrs) ** 2,
                                                 bounds=(0, 1e3), method='bounded').x

        hwhm = hwhm / dx_thrs * dx_0_5

        # convert the guessed peak values to function parameters
        func_params = cls.peak_guess_to_func_params(peak_height, hwhm)

        if np.iscomplexobj(y):
            peak_phase = np.angle(smoothed_data[idx_max])
            func_params["peak_phase"] = peak_phase

        return dict(**func_params, center=x0, offset=offset)

    @staticmethod
    def single_peak_func(*args, **kwargs):
        raise NotImplementedError("Peak function not defined")

    @staticmethod
    def peak_guess_to_func_params(*args, **kwargs):
        raise NotImplementedError("Peak function not defined")


class Lorentzian(PeakedFunction):
    param_names = ["area", "linewidth", "center", "offset"]

    @staticmethod
    def single_peak_func(x, area=1., linewidth=1., center=0., offset=0.):
        return offset + (2/np.pi) * area * linewidth / (4*(x-center)**2 + linewidth**2)

    @staticmethod
    def peak_guess_to_func_params(peak_height, hwhm):
        """Convert guessed peak values to function parameters"""
        return {
            "area": peak_height * np.pi * hwhm,
            "linewidth": 2 * hwhm
        }
