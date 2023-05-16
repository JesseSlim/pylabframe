import numpy as np

import pylabframe as lab
import pylabframe.data

test = lab.data.NumericalData([np.sin(np.linspace(0,20)),np.sin(np.linspace(0,20))*1.5], x_axis=np.linspace(0,20), y_axis=[20.0,30.0])
