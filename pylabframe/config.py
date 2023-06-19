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

_config_path = None


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
    if run_post_config_hooks:
        _post_config()



def get_settings(key=None, file=None):
    if file is None:
        file = _config_path

    with open(file, "rb") as f:
        settings_dict = tomllib.load(f)

    if key is not None:
        settings_dict = settings_dict[key]

    return settings_dict


# code to run after a configuration file has been specified
# used to set up the environment
_post_config_hooks = []


def register_post_config_hook(func):
    _post_config_hooks.append(func)


def _post_config():
    settings = get_settings()
    for hook_func in _post_config_hooks:
        hook_func(settings)
