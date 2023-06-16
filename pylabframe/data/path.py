import datetime
import glob
import os.path

from .. import config


def root_dir():
    return config.get_settings('data')['root_dir']


def current_datestamp():
    settings = config.get_settings('data')
    cur_date = datetime.datetime.now() - datetime.timedelta(hours=settings['day_starts_hour'])

    return cur_date.strftime(settings['datestamp_fmt'])


def today_dir(*args):
    if not os.path.isdir(root_dir()):
        raise FileNotFoundError(f"Root data directory {root_dir()} not found")

    cur_ds = current_datestamp()
    search_glob = os.path.join(root_dir(), f"{cur_ds}*")
    matches = glob.glob(search_glob)

    if len(matches) == 0:
        raise FileNotFoundError(f"No data directory find for date {cur_ds} in {root_dir()}")
    elif len(matches) > 1:
        raise Warning(f"Multiple data directories found for date {cur_ds} in {root_dir()}")

    return os.path.join(matches[0], *args)


class TimestampedDir:
    def __int__(self, name, timestamp: datetime.time=None, parent_dir=None, create_dirs=True, ts_suffix=None):
        settings = config.get_settings('data')
        if parent_dir is None:
            parent_dir = today_dir()
        if timestamp is None:
            timestamp = datetime.datetime.now()
        if not isinstance(timestamp, str):
            timestamp = timestamp.strftime(settings['timestamp_fmt'])
        if ts_suffix is None:
            ts_suffix = settings['timestamp_suffix']

        self.parent_dir = parent_dir
        self.name = name
        self.dir_name = timestamp + ts_suffix + name

        if create_dirs:
            os.makedirs(os.path.join(self.parent_dir, self.dir_name), exist_ok=True)

    def file(self, *args):
        return os.path.join(self.parent_dir, self.dir_name, *args)


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


def require_today_dir():
    if not os.path.isdir(root_dir()):
        raise FileNotFoundError(f"Root data directory {root_dir()} not found")

    try:
        today_dir()
    except FileNotFoundError:
        settings = config.get_settings('data')
        new_dir = input("Please enter a new for today's data directory: ")
        new_dir = current_datestamp() + settings['datestamp_suffix'] + new_dir

        td = os.path.join(root_dir(), new_dir)
        os.mkdir(td)


def _post_config(settings):
    if settings['data']['require_today_directory']:
        require_today_dir()
