r"""Current config file format:

--- toml file contents ---

computer_name = "lab-pc-1"

[data]
root_dir = 'C:\Users\labuser\Data'  # using single quotes here to interpret as raw string (keep backslashes as-is)
datestamp_fmt = "%Y-%m-%d"
datestamp_suffix = " "
timestamp_fmt = "%H%M%S"
timestamp_suffix = " "
day_starts_hour = 4
require_today_dir = true
default_save_location = "today_dir"  # options are: today_dir, root_dir, cwd, cwd_with_timestamp
default_add_timestamp = true

[devices]
    [devices.scope1]
    driver = "tekvisa.TektronixScope"
    address = "USB::0x1234::125::A22-5::INSTR"

    [devices.esa]
    driver = "keysightvisa.KeysightESA"
    address = "USB::0x5678::654::A44-9::INSTR"

--- end toml file contents ---

"""

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import os
import copy
import pprint

_config_path = None
_loaded_settings = None


_default_settings_toml = """
computer_name = ""

[data]
root_dir = '' 
datestamp_fmt = "%Y-%m-%d"
datestamp_suffix = " "
timestamp_fmt = "%H%M%S"
timestamp_suffix = " "
day_starts_hour = 4
require_today_dir = true
default_save_location = "cwd"  # options are: today_dir, root_dir, cwd, cwd_with_timestamp
default_add_timestamp = true
"""

_default_settings = tomllib.loads(_default_settings_toml)
_default_settings['data']['root_dir'] = os.path.join('~', 'lab_data')


def use(config_file, run_post_config_hooks=True):
    global _config_path
    if os.path.isfile(config_file):
        _config_path = os.path.abspath(config_file)
    else:
        user_config_file = os.path.join(
            os.path.expanduser('~'),
            '.pylabframe',
            'config',
            config_file
        )
        if os.path.isfile(user_config_file):
            _config_path = user_config_file
        else:
            raise FileNotFoundError(f"Configuration file {config_file} could not be found in either the current directory or in ~/.pylabframe/config")

    # load settings
    reload(run_post_config_hooks=run_post_config_hooks)




def reload(file=None, run_post_config_hooks=True):
    if file is None:
        file = _config_path

    with open(file, "rb") as f:
        settings_dict = tomllib.load(f)

    global _loaded_settings
    _loaded_settings = settings_dict

    if run_post_config_hooks:
        _post_config()


def print(default=False):
    if not default:
        pprint.pprint(_loaded_settings)
    else:
        pprint.pprint(_default_settings)


def get(key=None):
    if key == None:
        return copy.deepcopy(_loaded_settings)
    try:
        return _get(key, _loaded_settings)
    except (KeyError, TypeError):
        return _get(key, _default_settings)


def _get(key, settings_dict):
    keys = key.split(".")

    leaf = settings_dict
    for k in keys:
        leaf = leaf[k]

    return copy.deepcopy(leaf)


def set(key, val):
    keys = key.split(".")

    leaf = _loaded_settings
    parent_leaf = None

    for k in keys:
        parent_leaf = leaf
        if k in leaf:
            leaf = leaf[k]
        else:
            # if we add a new setting, this will add a dict for that final key part, which is later overwritten.
            # not the most efficient but it's fine.
            leaf[k] = {}
            leaf = leaf[k]

    parent_leaf[keys[-1]] = val


# code to run after a configuration file has been specified
# used to set up the environment
_post_config_hooks = []


def register_post_config_hook(func):
    _post_config_hooks.append(func)


def _post_config():
    for hook_func in _post_config_hooks:
        hook_func()
