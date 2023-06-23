import datetime
import glob
import os.path

from .. import config


def root_dir():
    return os.path.expanduser(config.get('data.root_dir'))


def current_datestamp():
    cur_date = datetime.datetime.now() - datetime.timedelta(hours=config.get('data.day_starts_hour'))

    return cur_date.strftime(config.get('data.datestamp_fmt'))


def today_dir():
    if not os.path.isdir(root_dir()):
        raise FileNotFoundError(f"Root data directory {root_dir()} not found")

    cur_ds = current_datestamp()
    search_glob = os.path.join(root_dir(), f"{cur_ds}*")
    matches = glob.glob(search_glob)

    if len(matches) == 0:
        raise FileNotFoundError(f"No data directory found for date {cur_ds} in {root_dir()}")
    elif len(matches) > 1:
        raise Warning(f"Multiple data directories found for date {cur_ds} in {root_dir()}")

    return matches[0]


def save_path(*args, add_timestamp=True, timestamp=None, ts_suffix=None, parent_dir=None, create_dirs=True, verbose=True, exist_ok=False):
    if len(args) == 0:
        raise ValueError('No filename specified')
    if parent_dir is None:
        parent_dir = today_dir()
    if timestamp is None:
        timestamp = datetime.datetime.now()
    if not isinstance(timestamp, str):
        timestamp = timestamp.strftime(config.get('data.timestamp_fmt'))
    if ts_suffix is None:
        ts_suffix = config.get('data.timestamp_suffix')

    if add_timestamp:
        args = list(args)
        args[-1] = timestamp + ts_suffix + args[-1]

    if verbose:
        print(f"Saving data in file: {os.path.join(*args)}")

    if len(args) > 1 and create_dirs:
        dir_path = os.path.join(parent_dir, args[:-1])
        if verbose:
            print(f" > creating directory: {dir_path}")
        os.makedirs(dir_path, exist_ok=True)

    cur_path = os.path.join(parent_dir, *args)
    if not exist_ok and os.path.exists(cur_path):
        raise FileExistsError(cur_path)

    return cur_path


class TimestampedDir:
    def __init__(self, name, timestamp: datetime.time=None, parent_dir=None, create_dirs=True, ts_suffix=None, verbose=True):
        if parent_dir is None:
            parent_dir = today_dir()
        if timestamp is None:
            timestamp = datetime.datetime.now()
        if not isinstance(timestamp, str):
            timestamp = timestamp.strftime(config.get('data.timestamp_fmt'))
        if ts_suffix is None:
            ts_suffix = config.get('data.timestamp_suffix')

        self.parent_dir = parent_dir
        self.name = name
        self.dir_name = timestamp + ts_suffix + name

        if verbose:
            print(f"Saving data in directory: {self.dir_name}")

        if create_dirs:
            dir_path = os.path.join(self.parent_dir, self.dir_name)
            if verbose:
                print(f" > creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)

    def file(self, *args, verbose=True, exists_ok=False):
        if verbose:
            print(f"Saving current measurement as: {os.path.join(self.dir_name, *args)}")
        cur_path = os.path.join(self.parent_dir, self.dir_name, *args)
        if not exists_ok and os.path.exists(cur_path):
            raise FileExistsError(cur_path)

        return cur_path


def find_path(*args, parent_dir=None, in_today=False, return_multiple=False):
    if parent_dir is None:
        if in_today:
            parent_dir = today_dir()
        else:
            parent_dir = root_dir()

    cur_parent = parent_dir
    for i, a in enumerate(args):
        search_glob = os.path.join(cur_parent, f"{a}*")
        matches = glob.glob(search_glob)
        if len(matches) == 0:
            raise FileNotFoundError(f"Can't find '{a}*' in {cur_parent}")
        if (i < len(args) - 1 or not return_multiple) and len(matches) > 1:
            raise RuntimeError(f"Too many matches for '{a}*' in {cur_parent}: {matches}")

        if i == len(args) - 1 and return_multiple:
            cur_parent = matches
        else:
            cur_parent = matches[0]

    return cur_parent


def expand_default_save_location(file, add_timestamp=True, timestamp=None, ts_suffix=None, create_dirs=True, verbose=True, exist_ok=False):
    if os.path.isabs(file):
        return file  # don't need to do any expansion

    default_save_option = config.get("data.default_save_location")
    if default_save_option == 'cwd':
        return file
    elif default_save_option == 'today_dir':
        return save_path(file, add_timestamp=add_timestamp, timestamp=timestamp, ts_suffix=ts_suffix,
                         parent_dir=today_dir(), create_dirs=create_dirs, verbose=verbose, exist_ok=exist_ok)
    elif default_save_option == 'root_dir':
        return save_path(file, add_timestamp=add_timestamp, timestamp=timestamp, ts_suffix=ts_suffix,
                         parent_dir=root_dir(), create_dirs=create_dirs, verbose=verbose, exist_ok=exist_ok)
    else:
        raise ValueError(f"Invalid option for default save location: {default_save_option}")


def require_today_dir():
    if not os.path.isdir(root_dir()):
        raise FileNotFoundError(f"Root data directory {root_dir()} not found")

    try:
        today_dir()
    except FileNotFoundError:
        new_dir = input("Please enter a new for today's data directory: ")
        new_dir = current_datestamp() + config.get('data.datestamp_suffix') + new_dir

        td = os.path.join(root_dir(), new_dir)
        os.mkdir(td)


@config.register_post_config_hook
def _post_config():
    if config.get('data.require_today_dir'):
        require_today_dir()
