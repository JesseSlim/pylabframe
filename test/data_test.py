import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


import pylabframe as lab
import pylabframe.data

test = lab.data.NumericalData(
    [np.sin(np.linspace(0,20,51)),np.sin(np.linspace(0,20,51))*1.5, np.sin(np.linspace(0,20,51))*2.],
    transpose=True,
    x_axis=np.linspace(0,20,51), y_axis=[20.0,30.0,40.0],
    axes_names=["time", "wavelength"]
)

t3 = test.iloc[2]

tt1 = test.iloc[:,0]
tt2 = test.iloc[:,1]
tt3 = test.iloc[:,2]

tb1 = tt1.vloc[5.:6.]
tb2 = tt1.vloc[5.:]

tt1.plot()
tt2.plot()
tt3.plot()

from pylabframe.data import NumericalData
restack = NumericalData.stack([tt1, tt2, tt3], new_axis=[6,7,8], new_axis_name="new_wavelength")

restack.metadata['setting1'] = 42.6
restack.metadata['setting2'] = 'volt'
restack.metadata['settings444'] = {'eggd': 5, 'cool': {
    'very': tekvisa.TektronixScope.RunModes.CONTINUOUS
}}


restack.save_npz("test/restack.npz")
restack_loaded = lab.data.NumericalData.load_npz('test/restack.npz')

fit_x = np.linspace(-10,10)
lor_data = fitters.Lorentzian.func(fit_x, 2., 0.5, 1.3, 0.9) + np.random.normal(0, 0.05, fit_x.shape)

plt.figure()
lor_obj = NumericalData(lor_data, x_axis=fit_x)
lor_obj.plot()

fr = lor_obj.fit(fitters.Lorentzian)

import scipy.optimize
aa = scipy.optimize.curve_fit(fitters.Lorentzian.func, lor_obj.x_axis, lor_obj.data_array, p0=None, full_output=True)

