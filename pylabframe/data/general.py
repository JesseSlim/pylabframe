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

            # we need to do identity checking instead of equality checking here (as list.count does) to handle index arrays
            num_ellipses = len([s for s in slice_list if s is Ellipsis])
            if num_ellipses > 1:
                raise ValueError(f"Multiple ellipses specified in {item} (expanded to {slice_list})")
            # expand the ellipses
            elif num_ellipses == 1:
                e_idx = slice_list.index(Ellipsis)
                n_expanded_slices = self.parent.data_array.ndim - (len(slice_list) - 1)
                slice_list = slice_list[:e_idx] + [slice(None)]*(n_expanded_slices) + slice_list[e_idx+1:]

            if len(slice_list) != self.parent.data_array.ndim:
                raise ValueError(f"Incorrect number of indices in {item} (expanded to {slice_list}), expected {self.parent.data_array.ndim}")

            reduced_axes = self.parent.reduced_axes
            sub_axes = []
            sub_axes_names = []
            parent_red_ax_pos = np.array([a["axis"] for a in reduced_axes])

            # the ordering of array indexing is the same as the order of the axis list
            slice_list = slice_list

            for i in range(len(slice_list)):
                if i < len(self.parent.axes) and self.parent.axes[i] is not None:
                    new_ax_or_val = self.parent.axes[i][slice_list[i]]
                else:
                    new_ax_or_val = None

                if isinstance(slice_list[i], int):
                    if i < len(self.parent.axes_names):
                        cur_ax_name = self.parent.axes_names[i]
                    else:
                        cur_ax_name = None
                    cur_ax_pos = i  # TODO: fix this to reflect the axes that have already been taken out in the parent
                    reduced_axes.append({"axis_name": cur_ax_name, "axis": cur_ax_pos, "index": slice_list[i], "value": new_ax_or_val})
                else:
                    sub_axes.append(new_ax_or_val)
                    if i < len(self.parent.axes_names):
                        sub_axes_names.append(self.parent.axes_names[i])

            sub_data = NumericalData(data_array=sub_array, axes=sub_axes, axes_names=sub_axes_names, reduced_axes=reduced_axes, metadata=self.parent.metadata.copy())

            return sub_data

    def __init__(self, data_array=None, x_axis=None, y_axis=None, z_axis=None, axes=None, axes_names=None,
                 reduced_axes=None, metadata=None, convert_to_numpy=True, transpose=False
                 ):
        if convert_to_numpy:
            data_array = np.asarray(data_array)
        if transpose:
            data_array = data_array.T
        self.data_array = data_array
        self.axes = axes if axes is not None else []
        self.reduced_axes = reduced_axes if reduced_axes is not None else []
        self.metadata = metadata if metadata is not None else {}
        if x_axis is not None:
            self.set_axis(0, x_axis, convert_to_numpy=convert_to_numpy)
        if y_axis is not None:
            self.set_axis(1, y_axis, convert_to_numpy=convert_to_numpy)
        if z_axis is not None:
            self.set_axis(2, z_axis, convert_to_numpy=convert_to_numpy)

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

    @classmethod
    def stack(cls, data_objs, axis=-1, new_axis=None, new_axis_name=None, retain_individual_metadata=False, convert_ax_to_numpy=True):
        data_arrays = []
        individual_metadata = {}
        new_metadata = None

        for o in data_objs:
            if isinstance(o, NumericalData):
                data_arrays.append(o.data_array)
                if new_metadata is None:
                    new_metadata = o.metadata.copy()
                if retain_individual_metadata:
                    individual_metadata[len(data_arrays)-1] = o.metadata
            else:
                data_arrays.append(o)

        if new_metadata is None:
            new_metadata = {}

        if retain_individual_metadata:
            new_metadata["_individual_metadata"] = individual_metadata

        # stack new data array
        new_data_array = np.stack(data_arrays, axis=axis)

        # insert new axis
        if convert_ax_to_numpy and new_axis is not None:
            new_axis = np.asarray(new_axis)
        new_axes: list = data_objs[0].axes.copy()
        axis_shortage = data_objs[0].data_array.ndim - len(new_axes)
        if axis_shortage > 0:
            new_axes += [None] * axis_shortage

        ax_insert_index = axis
        if ax_insert_index < 0:
            ax_insert_index = len(new_axes) + 1 + ax_insert_index
        new_axes.insert(ax_insert_index, new_axis)

        # insert new axis name
        new_axnames: list = data_objs[0].axes_names.copy()
        axis_shortage = data_objs[0].data_array.ndim - len(new_axnames)
        if axis_shortage > 0:
            new_axnames += [None] * axis_shortage

        ax_insert_index = axis
        if ax_insert_index < 0:
            ax_insert_index = len(new_axnames) + 1 + ax_insert_index
        new_axnames.insert(ax_insert_index, new_axis_name)

        stacked_obj = cls(new_data_array, axes=new_axes, axes_names=new_axnames, metadata=new_metadata)
        return stacked_obj
