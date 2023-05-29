

def map_nested_dict(f, d):
    if isinstance(d, dict):
        new_d = {k: map_nested_dict(f, v) for k,v in d.items()}
        return new_d
    else:
        return f(d)