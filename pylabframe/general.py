import sys


def get_computer_name():
    cname = None
    with open("pylabframe/config/_computer_name.cfg", "r") as f:
        cname = f.read().strip()

    return cname


def load_config_file(filename):
    config_content = {}
    if not filename.endswith(".cfg"):
        filename += ".cfg"
    with open(f"pylabframe/config/{filename}", "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.strip().startswith("#"):
            # this is a comment, continue
            continue
        if line.strip() == '':
            # empty line, continue
            continue

        # if "#" in line:
        #     # comment somewhere on the line
        #     hash_idx = line.find("#")
        #     line = line[:hash_idx]

        if "=" not in line:
            raise ValueError(f"Invalid config line {line}")

        split_idx = line.find("=")
        k = line[:split_idx].strip()
        v = line[split_idx+1:].strip()

        config_content[k] = v

    return config_content