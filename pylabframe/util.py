import re
import os

def map_nested_dict(f, d):
    if isinstance(d, dict):
        new_d = {k: map_nested_dict(f, v) for k,v in d.items()}
        return new_d
    else:
        return f(d)


def extract_tag_value(filename, tag, conv=lambda s: float(s.replace("_",".")), value_re="[0-9]+((_|\\.)[0-9]+)?", raise_on_absence=False, split_filename=True):
    if split_filename:
        filename = os.path.split(filename)[1]
    m = re.search(f"(_|^){tag}(?P<value>{value_re})(_|\\.|$)", filename)
    if m is None:
        if raise_on_absence:
            raise ValueError(tag)
        else:
            return None
    return conv(m.group('value'))