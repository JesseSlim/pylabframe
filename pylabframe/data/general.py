import numpy as np

class NumericalData:
    def __init__(self, data_array=None, x_axis=None, y_axis=None, axes=None, metadata=None, convert_to_numpy=True):
        if convert_to_numpy:
            data_array = np.asarray(data_array)
        self.data_array = data_array
        self.axes = axes if axes is not None else []
        self.metadata = metadata if metadata is not None else {}
        if x_axis is not None:
            self.set_axis(0, x_axis, convert_to_numpy=convert_to_numpy)
        if y_axis is not None:
            self.set_axis(1, y_axis, convert_to_numpy=convert_to_numpy)

    def set_axis(self, ax_index, ax_values, convert_to_numpy=True):
        if len(self.axes) < ax_index + 1:
            self.axes = self.axes + [None] * (ax_index + 1 - len(self.axes))
        if convert_to_numpy:
            ax_values = np.asarray(ax_values)
        self.axes[ax_index] = ax_values

    @property
    def x_axis(self):
        return self.axes[0]
    @x_axis.setter
    def x_axis(self, ax_values):
        self.set_axis(0, ax_values)

    @property
    def y_axis(self):
        return self.axes[1]
    @y_axis.setter
    def y_axis(self, ax_values):
        self.set_axis(1, ax_values)

    @property
    def z_axis(self):
        return self.axes[2]
    @z_axis.setter
    def z_axis(self, ax_values):
        self.set_axis(2, ax_values)

    # patch all calls that don't work on the NumericalData object directly through to the underlying data_array
    def __getattr__(self, item):
        return getattr(self.data_array, item)

    # @property
    # def ndim(self):
    #     return self.data_array.ndim
    #
    # @property
    # def shape(self):
    #     return self.data_array.shape

    def plot(self, plot_axis=None, x_label=None, y_label=None, auto_label=True, **kw):
        if self.ndim == 1:
            return self.plot_1d(plot_axis, x_label=None, y_label=None, auto_label=auto_label, **kw)
        elif self.ndim == 2:
            return self.plot_2d(plot_axis, x_label=None, y_label=None, auto_label=auto_label, **kw)
        else:
            raise NotImplementedError(f"No plotting method available for {self.ndim}-dimensional data")

    def plot_1d(self, plot_axis=None, x_label=None, y_label=None, auto_label=True, **kw):
        # set some defaults
        if 'm' not in kw and 'marker' not in kw:
            kw['marker'] = '.'

        if plot_axis is None:
            import matplotlib.pyplot as plt
            plot_axis = plt.gca()

        plot_axis.plot(self.x_axis, self.data_array, **kw)
        if x_label is None and auto_label and "x_label" in self.metadata:
            x_label = self.metadata["x_label"]
            if "x_unit" in self.metadata:
                x_label += f" ({self.metadata['x_unit']})"
        if x_label is not None:
            plot_axis.set_xlabel(x_label)
        if y_label is None and auto_label and "y_label" in self.metadata:
            y_label = self.metadata["y_label"]
            if "y_unit" in self.metadata:
                y_label += f" ({self.metadata['y_unit']})"
        if y_label is not None:
            plot_axis.set_ylabel(y_label)

