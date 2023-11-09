import numpy as np
import scipy.optimize
import copy
from enum import Enum

from .. import util
from . import path

class NumericalData:
    """
    Holds numerical data in data_array. The first axis is understood to be the x-axis, the y-axis is the second axis and so forth.
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

    class ValueLocator:
        def __init__(self, parent):
            self.parent: "NumericalData" = parent

        def __getitem__(self, item):
            if not isinstance(item, tuple):
                item = (item,)

            idx_slices = tuple()

            for i, vals in enumerate(item):
                cur_ax = self.parent.axes[i]
                ax_ordered = np.all(cur_ax[:-1] <= cur_ax[1:])
                if not ax_ordered:
                    raise NotImplementedError("Value slicing on unordered or reverse-ordered axes is not yet supported")

                if isinstance(vals, slice):
                    start_idx = None
                    stop_idx = None
                    if vals.step is not None:
                        raise NotImplementedError("Value slicing with custom step size is not yet supported")
                    if vals.start is not None:
                        # find first index along axis >= the start value
                        start_idx = np.argmax(cur_ax >= vals.start)
                        # check if the index we found actually satifies the condition
                        if not cur_ax[start_idx] >= vals.start:
                            # set the start index beyond the axis length
                            start_idx = len(cur_ax)
                    if vals.stop is not None:
                        # find last index along axis <= the stop value
                        # we do include that last value in the slice, contrary to index slicing
                        stop_idx = np.argmax(cur_ax[::-1] <= vals.stop)
                        if cur_ax[::-1][stop_idx] <= vals.stop:
                            stop_idx = len(cur_ax) - stop_idx
                        else:
                            # there is no value smaller than the stop value, meaning the slice should be empty
                            stop_idx = 0

                    idx_slices += (slice(start_idx, stop_idx),)
                else:
                    close_vals = np.isclose(cur_ax, vals)
                    close_idx = np.argmax(close_vals)
                    if close_vals[close_idx] == False:
                        raise ValueError(f"Value {vals} could not be found in axis {i}")
                    idx_slices += (close_idx,)

            return self.parent.iloc[idx_slices]

    def __init__(self, *args, data_array=None, x_axis=None, y_axis=None, z_axis=None, axes=None, axes_names=None,
                 error_array=None, reduced_axes=None, metadata=None, convert_to_numpy=True, transpose=False, check_dimensions=True, last_fit=None
                 ):
        if len(args) > 0:
            # in this case, take the last positional arg as the data array, and the preceding ones as axes
            # allows to initialize using the intuitive syntax NumericalData(X, Y), or (X, Y, Z), etc
            data_array = args[-1]
            if axes is None:
                axes = list(args[:-1])
            elif len(args) > 1:
                raise ValueError("Axes defined both as positional and keyword arguments.")

        if convert_to_numpy:
            data_array = np.asarray(data_array)
            if error_array is not None:
                error_array = np.asarray(error_array)
        if transpose:
            data_array = data_array.T
            if error_array is not None:
                error_array = error_array.T
        self.data_array = data_array
        self.error_array = error_array
        self.axes = axes if axes is not None else []
        if convert_to_numpy:
            self.axes = [(np.asarray(a) if a is not None else None) for a in self.axes]
        self.reduced_axes = reduced_axes if reduced_axes is not None else []
        self.metadata = metadata if metadata is not None else {}
        if x_axis is not None:
            self.set_axis(0, x_axis, convert_to_numpy=convert_to_numpy)
        if y_axis is not None:
            self.set_axis(1, y_axis, convert_to_numpy=convert_to_numpy)
        if z_axis is not None:
            self.set_axis(2, z_axis, convert_to_numpy=convert_to_numpy)

        self.axes_names = axes_names if axes_names is not None else []
        self.last_fit = last_fit

        self.iloc = self.IndexLocator(self)
        self.vloc = self.ValueLocator(self)

        # this only works now if the axes are numpy arrays. could be generalized to list-like axes as well
        if check_dimensions:
            for i in range(min(self.data_array.ndim, len(self.axes))):
                if self.axes[i] is not None:
                    if self.axes[i].ndim != 1:
                        raise ValueError(f"Axis {i} is not one-dimensional but {self.axes[i].ndim}-dimensional")
                    if self.data_array.shape[i] != self.axes[i].shape[0]:
                        raise ValueError(f"Data length {self.data_array.shape[i]} does not match axis length {self.axes[i].shape[0]} along axis {i}")
            if error_array is not None:
                if error_array.shape != data_array.shape:
                    raise ValueError(f"Data array and error array have incompatible shapes {self.data_array.shape} != {self.error_array.shape}")

    def set_axis(self, ax_index, ax_values, convert_to_numpy=True):
        if len(self.axes) < ax_index + 1:
            self.axes = self.axes + [None] * (ax_index + 1 - len(self.axes))
        if convert_to_numpy:
            ax_values = np.asarray(ax_values)
        self.axes[ax_index] = ax_values

    def set_axis_name(self, ax_index, ax_name):
        if len(self.axes_names) < ax_index + 1:
            self.axes_names = self.axes_names + [None] * (ax_index + 1 - len(self.axes_names))
        self.axes_names[ax_index] = ax_name

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

    def get_axis_range(self, ax_index):
        return (np.min(self.axes[ax_index]), np.max(self.axes[ax_index]))

    @property
    def x_range(self):
        return self.get_axis_range(0)

    @property
    def y_range(self):
        return self.get_axis_range(1)

    @property
    def z_range(self):
        return self.get_axis_range(2)

    @property
    def data_range(self):
        return (np.min(self.data_array), np.max(self.data_array))

    # patch all calls that don't work on the NumericalData object directly through to the underlying data_array
    def __getattr__(self, item):
        if hasattr(self.data_array, item):
            return getattr(self.data_array, item)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}' and neither does the underlying data_array")

    # item access is patched through to the metadata dict
    def __getitem__(self, item):
        return self.metadata[item]

    def __setitem__(self, key, value):
        self.metadata[key] = value

    @classmethod
    def stack(cls, data_objs, new_axis=None, new_axis_name=None, axis=-1, retain_individual_metadata=False,
              new_axis_metadata_key=None, sort_by_metadata_key=True,
              convert_ax_to_numpy=True):
        """
        Combine data objects into a single object of higher dimensionality
        :param data_objs:
        :param axis:
        :param new_axis:
        :param new_axis_name:
        :param retain_individual_metadata:
        :param convert_ax_to_numpy:
        :return:
        """
        data_arrays = []
        individual_metadata = {}
        new_metadata = None
        if new_axis is not None and new_axis_metadata_key is not None:
            raise ValueError("new_axis and new_axis_metadata_key can not be set at the same time")

        if new_axis_metadata_key is not None:
            new_axis = []

        if sort_by_metadata_key and new_axis_metadata_key is not None:
            if sort_by_metadata_key is True:
                sort_by_metadata_key = new_axis_metadata_key
            data_objs = sorted(data_objs, key=lambda o: o.metadata[sort_by_metadata_key])

        for o in data_objs:
            if isinstance(o, NumericalData):
                data_arrays.append(o.data_array)
                if new_metadata is None:
                    new_metadata = o.metadata.copy()
                if retain_individual_metadata:
                    individual_metadata[len(data_arrays) - 1] = o.metadata
                if new_axis_metadata_key is not None:
                    new_axis.append(o.metadata[new_axis_metadata_key])
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

    # manipulation functions
    # ======================
    def reverse_axis(self, axis=0):
        self.axes[axis] = self.axes[axis][::-1]
        self.data_array = np.flip(self.data_array, axis=axis)

    def sort_axis(self, axis=0, **sort_kw):
        if axis == 'all':
            for i in range(self.data_array.ndim):
                self.sort_axis(axis=i, **sort_kw)
        else:
            sort_idx = np.argsort(self.axes[axis], **sort_kw)

            self.axes[axis] = np.take(self.axes[axis], sort_idx, axis=0)
            self.data_array = np.take(self.data_array, sort_idx, axis=axis)

    def copy(self, apply_data_func=None, apply_axis_funcs=()):
        if apply_data_func is not None:
            new_data_array = apply_data_func(self.data_array)
        else:
            new_data_array = self.data_array.copy()

        new_axes = []
        for i, orig_axis in enumerate(self.axes):
            try:
                axis_func = apply_axis_funcs[i]
            except (IndexError, KeyError):
                axis_func = lambda a: a.copy()
            new_axes.append(axis_func(orig_axis))

        return type(self)(
            data_array=new_data_array,
            axes=new_axes,
            axes_names=copy.deepcopy(self.axes_names),
            reduced_axes=copy.deepcopy(self.reduced_axes),
            metadata=copy.deepcopy(self.metadata)
        )

    def apply_along_axis(self, func, axis, *args, **kwargs):
        new_data_array = np.apply_along_axis(func, axis, self.data_array, *args, **kwargs)

        new_axes = copy.deepcopy(self.axes)
        new_axes_names = copy.deepcopy(self.axes_names)
        if len(new_axes) > axis:
            new_axes.pop(axis)
        if len(new_axes_names) > axis:
            new_axes_names.pop(axis)

        return type(self)(
            data_array=new_data_array,
            axes=new_axes,
            axes_names=new_axes_names,
            reduced_axes=copy.deepcopy(self.reduced_axes),
            metadata=copy.deepcopy(self.metadata)
        )

    # saving functions
    # ================
    def save_npz(self, file, stringify_enums=True, save_timestamp=True, save_location_option=None, **expand_kw):
        file = path.expand_default_save_location(file, save_location_option=save_location_option, **expand_kw)
        num_axes = len(self.axes) if self.axes is not None else 0
        if num_axes > 0:
            ax_dict = {f"axis_{i}": self.axes[i] for i in range(num_axes)}
        else:
            ax_dict = {}

        if save_timestamp:
            self.metadata["save_date"] = path.current_datestamp()
            self.metadata["save_time"] = path.current_timestamp()

        metadata = copy.deepcopy(self.metadata)
        if stringify_enums:
            metadata = util.map_nested_dict(
                lambda x: f"{x.__class__.__name__}.{x.name}" if isinstance(x, Enum) else x,
                metadata
            )

        np.savez(file,
                 data_array=self.data_array, num_axes=num_axes, **ax_dict,
                 axes_data={'axes_names': self.axes_names, 'reduced_axes': self.reduced_axes},
                 metadata=metadata
                 )

    @classmethod
    def load_npz(cls, file):
        npz_data = np.load(file, allow_pickle=True)
        data_array = npz_data['data_array']
        num_axes = npz_data['num_axes'].item()  # scalar values are saved as a 0-dimensional array, need to extract
        axes_data = npz_data['axes_data'].item()
        metadata = npz_data['metadata'].item()

        axes = [npz_data[f'axis_{i}'] for i in range(num_axes)]

        return cls(data_array, axes=axes, axes_names=axes_data['axes_names'], reduced_axes=axes_data['reduced_axes'], metadata=metadata)

    # plotting functions
    # ==================
    def plot(self, plot_axis=None, x_label=None, y_label=None, auto_label=True, **kw):
        if self.ndim == 1:
            return self.plot_1d(plot_axis, x_label=x_label, y_label=y_label, auto_label=auto_label, **kw)
        elif self.ndim == 2:
            return self.plot_2d(plot_axis, x_label=x_label, y_label=y_label, auto_label=auto_label, **kw)
        else:
            raise NotImplementedError(f"No plotting method available for {self.ndim}-dimensional data")

    def plot_1d(self, plot_axis=None, x_label=None, y_label=None, auto_label=True, apply_data_func=lambda x: x,
                x_scaling=1., x_offset=0., y_scaling=1., y_offset=0., plot_errors=True, error_scaling=2., transpose=False,
                **kw):
        # set some defaults
        if 'm' not in kw and 'marker' not in kw:
            kw['marker'] = '.'

        if plot_axis is None:
            import matplotlib.pyplot as plt
            plot_axis = plt.gca()

        plot_y = y_scaling * (apply_data_func(self.data_array) - y_offset)
        plot_x = x_scaling * (self.x_axis - x_offset)

        if self.error_array is not None:
            plot_err = y_scaling * error_scaling * apply_data_func(self.error_array)  # depending on the data func applied, this might not make sense
        else:
            plot_err = None

        if transpose:
            plot_x, plot_y = plot_y, plot_x
            xerr = plot_err
            yerr = None
        else:
            yerr = plot_err
            xerr = None

        if not np.iscomplexobj(plot_y):
            if not plot_errors or self.error_array is None:
                lines = plot_axis.plot(plot_x, plot_y, **kw)
            else:
                lines = plot_axis.errorbar(plot_x, plot_y, yerr=yerr, xerr=xerr, **kw)
        else:
            # default for complex plotting: plot both quadratures. No individual control over their appearance
            # If you want that, use apply_data_func and call the plotting function for each Q individually
            if not plot_errors or self.error_array is None:
                lines = plot_axis.plot(plot_x, np.real(plot_y), **kw)
                lines += plot_axis.plot(plot_x, np.imag(plot_y), **kw)
            else:
                raise NotImplementedError("Plotting complex data with error bars not yet implemented")

        if x_label is None and auto_label and "x_label" in self.metadata:
            x_label = self.metadata["x_label"]
            if "x_unit" in self.metadata:
                x_label += f" ({self.metadata['x_unit']})"
        if y_label is None and auto_label and "y_label" in self.metadata:
            y_label = self.metadata["y_label"]
            if "y_unit" in self.metadata:
                y_label += f" ({self.metadata['y_unit']})"

        if transpose:
            x_label, y_label = y_label, x_label
        if x_label is not None:
            plot_axis.set_xlabel(x_label)
        if y_label is not None:
            plot_axis.set_ylabel(y_label)

        return lines

    def plot_2d(self, plot_axis=None, x_label=None, y_label=None, z_label=None, auto_label=True, apply_data_func=lambda x: x,
                x_scaling=1., x_offset=0., y_scaling=1., y_offset=0., z_scaling=1., z_offset=0.,
                add_colorbar=True, cax=None, fix_mesh=True, rasterized=True, cbar_kw={},
                **kw):

        if plot_axis is None:
            import matplotlib.pyplot as plt
            plot_axis = plt.gca()

        plot_x = x_scaling * (self.x_axis - x_offset)
        plot_y = y_scaling * (self.y_axis - y_offset)
        plot_z = z_scaling * (apply_data_func(self.data_array) - z_offset)
        plot_z = plot_z.T

        im = plot_2d_data(plot_x, plot_y, plot_z, plot_axis, fix_mesh=fix_mesh, rasterized=rasterized, **kw)

        for a in ['x', 'y', 'z']:
            this_label = locals()[f'{a}_label']
            if this_label is None and auto_label and f'{a}_label' in self.metadata:
                this_label = self.metadata[f'{a}_label']
                if f'{a}_unit' in self.metadata:
                    this_unit = self.metadata[f'{a}_unit']
                    this_label += f" ({this_unit})"
                locals()[f'{a}_label'] = this_label

        if x_label is not None:
            plot_axis.set_xlabel(x_label)
        if y_label is not None:
            plot_axis.set_ylabel(y_label)

        if add_colorbar:
            import matplotlib.pyplot as plt
            plt.colorbar(im, cax=cax, ax=plot_axis, label=z_label, **cbar_kw)

        return im

    # fitting functions
    # =================
    def fit(self, fit_def: "FitterDefinition", p0=None, p0_dict=None, pfix_dict=None, data_transform_func=None, **kw):
        # if issubclass(fit_def, fitters.FitterDefinition):
        fit_func = fit_def.fit_func
        if pfix_dict is None:
            pfix_dict = {}
        fixed_params = list(pfix_dict.keys())
        unknown_params = [pn for pn in fixed_params if pn not in fit_def.param_names]
        if len(unknown_params) > 0:
            raise ValueError(f"There are unknown fixed parameters: {unknown_params}")

        free_params = [pn for pn in fit_def.param_names if pn not in fixed_params]

        if data_transform_func is None:
            data_transform_func = lambda x: x
            data_transform_func_save = None
        else:
            data_transform_func_save = data_transform_func

        if p0 is None and p0_dict is None:
            if fit_def.guess_func:
                p0_dict = fit_def.guess_func(self, pfix_dict=pfix_dict)
            else:
                p0 = [1.] * len(free_params)

        if p0 is None:
            p0 = [p0_dict[pn] for pn in free_params]

        ydata = data_transform_func(self.data_array)
        complex_fit = np.iscomplexobj(ydata)
        if complex_fit:
            ydata = np.concatenate((np.real(ydata), np.imag(ydata)))

        def fit_func_wrapper(xdata, *params):
            all_params = dict(zip(free_params, params))
            all_params.update(pfix_dict)
            ydata_estimate = data_transform_func(fit_func(xdata, **all_params))

            if complex_fit:
                ydata_estimate = np.concatenate((np.real(ydata_estimate), np.imag(ydata_estimate)))

            return ydata_estimate

        popt, pcov, infodict, mesg, ier = scipy.optimize.curve_fit(
            fit_func_wrapper, self.x_axis, ydata, p0=p0, full_output=True, **kw
        )

        popt_dict = dict(zip(free_params, popt))
        perr_dict = dict(zip(free_params, np.sqrt(np.diagonal(pcov))))

        fit_x_range = (self.x_axis.min(), self.x_axis.max())
        this_fit = FitResult(fit_def, popt_dict=popt_dict, perr_dict=perr_dict, pcov=pcov,
                         fit_info=infodict, fit_x_range=fit_x_range, pfix_dict=pfix_dict,
                         data_transform_func=data_transform_func_save, complex_fit=complex_fit)
        self.last_fit = this_fit
        return this_fit

    def guess_fit(self, fit_def: "FitterDefinition", pfix_dict=None):
        if pfix_dict is None:
            pfix_dict = {}
        guessed_params = fit_def.guess_func(self, pfix_dict=pfix_dict)
        # p0 = [guessed_params[pn] for pn in fit_def.param_names]
        # popt_dict = dict(zip(fit_def.param_names, p0))

        popt_dict = guessed_params

        fit_x_range = (self.x_axis.min(), self.x_axis.max())
        return FitResult(fit_def, popt_dict, None, None, None, fit_x_range, guess=True, pfix_dict=pfix_dict)



# fitting infrastructure
# ======================

class FitResult:
    def __init__(self, fit_def, popt_dict, perr_dict, pcov, fit_info, fit_x_range=None, guess=False, pfix_dict=None,
                 data_transform_func=None, complex_fit=None):
        if pfix_dict is None:
            pfix_dict = {}

        self.popt_dict = popt_dict
        self.perr_dict = perr_dict
        self.pfix_dict = pfix_dict
        self.pcov = pcov
        self.fit_def: FitterDefinition = fit_def
        self.fit_info = fit_info
        self.fit_x_range = fit_x_range
        self.guess = guess
        self.data_transform_func = data_transform_func
        self.complex_fit = complex_fit

    @classmethod
    def from_guess(cls, fit_def, p0_dict, fit_x_range=None, pfix_dict=None):
        return cls(fit_def, p0_dict, None, None, None, fit_x_range=fit_x_range, guess=True, pfix_dict=pfix_dict)

    def plot(self, x_start=None, x_stop=None, x_num=1001, x=None, plot_axis=None, **plot_kw):
        if x is None:
            if x_start is None:
                x_start = self.fit_x_range[0]
            if x_stop is None:
                x_stop = self.fit_x_range[1]
            x = np.linspace(x_start, x_stop, num=x_num)
        y = self(x)
        fit_data = NumericalData(x, y)

        plot_kw.setdefault('marker', None)
        return fit_data.plot(plot_axis=plot_axis, **plot_kw)

    def summary(self, do_print=True, do_return=False, sigmas=2, sci_not=True, num_digits=None, print_function=False):
        if num_digits is not None:
            num_digits = f".{num_digits}"
        else:
            num_digits = ""
        float_format = f"{{0:{num_digits}e}}" if sci_not else f"{{0:{num_digits}f}}"

        msg = (
f"""Fit result summary for {self.fit_def.get_name()}
==================
""")
        if print_function:
            import inspect
            msg += "fit function:\n"
            for l in inspect.getsourcelines(self.fit_def.fit_func)[0]:
                msg += f"    {l}"
            msg += "\n"

        msg += f"fixed parameters:\n"
        if len(self.pfix_dict) == 0:
            msg += " > none\n"
        else:
            for k,v in self.pfix_dict.items():
                kc = f"{k}:"
                v1 = float_format.format(v)
                msg += f" > {kc: <20} {v1: <20}\n"

        msg += f"\nparameters with {sigmas}σ confidence intervals:\n"
        for k,v in self.popt_dict.items():
            kc = f"{k}:"
            v1 = float_format.format(v)
            v2 = ""
            if k in self.perr_dict:
                v2 = float_format.format(sigmas*self.perr_dict[k])
            msg += f" > {kc: <20} {v1: <20} +/- {v2: <20}\n"

        if do_print:
            print(msg)

        if do_return:
            return msg

    def __call__(self, x):
        return self.fit_def.fit_func(x, **self.popt_dict, **self.pfix_dict)

    def __repr__(self):
        return f"FitResult({self.fit_def.__name__}, popt_dict={self.popt_dict}, pfix_dict={self.pfix_dict}, <pcov>, ..., guess={self.guess})"

    def __getitem__(self, item):
        if item in self.popt_dict:
            return self.popt_dict[item]
        elif item in self.pfix_dict:
            return self.pfix_dict[item]
        else:
            raise KeyError(item)

    # saving functions
    # ================
    def save_npz(self, file, save_timestamp=True, save_location_option=None, **expand_kw):
        file = path.expand_default_save_location(file, save_location_option=save_location_option, **expand_kw)

        data_to_save = {
            "fit_def": self.fit_def.__name__,
            "popt_dict": self.popt_dict,
            "perr_dict": self.perr_dict,
            "pfix_dict": self.pfix_dict,
            "pcov": self.pcov,
            "fit_info": self.fit_info,
            "fit_x_range": self.fit_x_range,
            "guess": self.guess,
            "data_transform_func": repr(self.data_transform_func),
            "complex_fit": self.complex_fit
        }

        if save_timestamp:
            data_to_save["save_date"] = path.current_datestamp()
            data_to_save["save_time"] = path.current_timestamp()

        np.savez(file, **data_to_save)


class FitterDefinition:
    param_names = None
    name = None

    @classmethod
    def fit_func(cls, x):
        return None

    @classmethod
    def guess_func(cls, data: NumericalData, pfix_dict=None):
        return None

    @classmethod
    def get_name(cls):
        if cls.name is not None:
            return cls.name
        else:
            return cls.__name__


# plotting utility functions
# ==========================

def plot_2d_data(x, y, z, ax=None, fix_mesh=True, rasterized=True, **kw):
    plotdata = [x, y, z]

    if fix_mesh:
        # the X and Y arrays that go into pcolormesh indicate the corners of every square that gets a color
        # specified by C
        # however, our dataArray specified the values at the center values given by X & Y
        # so we need to convert this into corners locations: take the midpoints of the axis points and add
        # corners to the beginning and end of the axis
        plotdata_fixed = []
        for i in range(2):
            center_locs = plotdata[i]
            midpoints = (center_locs[:-1] + center_locs[1:]) / 2
            left_corner = 1.5 * center_locs[0] - 0.5 * center_locs[1]
            right_corner = 1.5 * center_locs[-1] - 0.5 * center_locs[-2]

            corners = np.concatenate(([left_corner], midpoints, [right_corner]))
            plotdata_fixed.append(corners)

        plotdata_fixed.append(plotdata[-1])
        plotdata = plotdata_fixed

    im = ax.pcolormesh(*plotdata, rasterized=rasterized, **kw)

    return im


def load(*args, parent_dir=None, in_today=False, return_multiple=False):
    filenames = path.find_path(*args, parent_dir=parent_dir, in_today=in_today, return_multiple=return_multiple)

    if return_multiple:
        return [NumericalData.load_npz(f) for f in filenames]
    else:
        return NumericalData.load_npz(filenames)
