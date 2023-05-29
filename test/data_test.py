import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


import pylabframe as lab
import pylabframe.data
from pylabframe.hardware.drivers import tekvisa

test = lab.data.NumericalData(
    [np.sin(np.linspace(0,20)),np.sin(np.linspace(0,20))*1.5, np.sin(np.linspace(0,20))*2.],
    transpose=True,
    x_axis=np.linspace(0,20), y_axis=[20.0,30.0,40.0],
    axes_names=["time", "wavelength"]
)

t3 = test.iloc[2]

tt1 = test.iloc[:,0]
tt2 = test.iloc[:,1]
tt3 = test.iloc[:,2]

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