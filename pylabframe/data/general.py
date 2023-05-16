import numpy as np

class NumericalData:
    """
    Holds numerical data in data_array. The last axis is understood to be the x-axis, the y-axis is the second to last axis and so forth.
    """

    class IndexLocator:
        def __init__(self, parent):
            self.parent: "NumericalData" = parent

        def __getitem__(self, item):
            sub_array = self.parent.data_array.__getitem__(item)

            # calculate the new axes
            # start by regularizing the list of the requested slices/indices
            if isinstance(item, tuple):
                slice_list = list(item)
            else:
                slice_list = [item]

            if len(slice_list) < self.parent.data_array.ndim and Ellipsis not in slice_list:
                slice_list += [Ellipsis]

            if slice_list.count(Ellipsis) > 1:
                raise ValueError(f"Multiple ellipses specified in {item} (expanded to {slice_list})")
            # expand the ellipses
            if Ellipsis in slice_list:
                e_idx = slice_list.index(Ellipsis)
                n_expanded_slices = len(slice_list) - 1 - self.parent.data_array.ndim
                slice_list = slice_list[:e_idx] + [slice(None)]*(n_expanded_slices) + slice_list[e_idx+1:]

            if len(slice_list) != self.parent.data_array.ndim:
                raise ValueError(f"Incorrect number of indices in {item} (expanded to {slice_list}), expected {self.parent.data_array.ndim}")

            parent_indices = self.parent.parent_indices
            sub_axes = []
            sub_axes_names = []

            for i in range(len(slice_list)):
                if i < len(self.parent.axes) and self.parent.axes[i] is not None:
                    new_axis = self.parent.axes[i][slice_list[i]]
                else:
                    new_axis = None

                if isinstance(slice_list[i], slice):
                    sub_axes.append(new_axis)
                    if i < len(self.parent.axes_names):
                        sub_axes_names.append(self.parent.axes_names[i])
                else:
                    if i < len(self.parent.axes_names):
                        cur_ax_name = self.parent.axes_names[i]
                    else:
                        cur_ax_name = None
                    parent_indices += {"axis_name": cur_ax_name, "axis_position": i, "index": slice_list[i], "value": new_axis}

            sub_data = NumericalData(data_array=sub_array, axes=sub_axes, parent_indices=parent_indices, metadata=self.parent.metadata.copy())

            return sub_data

    def __init__(self, data_array=None, x_axis=None, y_axis=None, axes=None, axes_names=None, parent_indices=None, metadata=None, convert_to_numpy=True):
        if convert_to_numpy:
            data_array = np.asarray(data_array)
        self.data_array = data_array
        self.axes = axes if axes is not None else []
        self.parent_indices = parent_indices if parent_indices is not None else []
        self.metadata = metadata if metadata is not None else {}
        if x_axis is not None:
            self.set_axis(0, x_axis, convert_to_numpy=convert_to_numpy)
        if y_axis is not None:
            self.set_axis(1, y_axis, convert_to_numpy=convert_to_numpy)

        self.axes_names = axes_names if axes_names is not None else []

        self.iloc = self.IndexLocator(self)

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

