import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


import pylabframe as lab
import pylabframe.data, pylabframe.data.fitters

test_x = np.linspace(0, 10)
test_y = test_x*0.4 + 1.7 + np.random.normal(0, 0.2, len(test_x))

data_tr = lab.data.NumericalData(test_x, test_y)
data_tr.plot(ls='none')

data_fit = data_tr.fit(lab.data.fitters.Line, pfix_dict={"a": 0.5})
data_fit.plot()
