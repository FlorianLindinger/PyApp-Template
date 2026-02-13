# Helper code used to import settings in settings.(toml/yaml/yml/json/ini/env/txt) as the dictionary s.
# Settings can be accessed in python as s["name"] after the line "import settings".
# This code also converts string float values to float (including scientific notation)
# and some simple math operations between float convertables (including scientific notation).

# ==============================================================================

# If strings are in the following form (where a,b,c look like floats or scientific notation), they will be calculated and converted to float:
# a
# a+b
# a-b
# a*b
# a/b
# a^b
# a*b^c
# a/b^c

# ==============================================================================

settings_file_path_noEnding = "settings"

import os
import re


# define custom class for better error message of missing element:
class custom_error_dictionary(dict):
    """dictionary subclass for custom error message of missing key"""

    def __missing__(self, key):
        raise ValueError(f'Missing-setting-error: "{key}" is not defined in "{file_path}"')


# read in settings files as dict
# ==================================================
s = None
base = settings_file_path_noEnding
if os.path.exists(base + ".toml"):
    file_path = os.path.abspath(base + ".toml")
    from do_not_change.read_toml import tomli

    with open(file_path, "rb") as f:
        s = tomli.load(f)
elif os.path.exists(base + ".yaml"):
    file_path = os.path.abspath(base + ".yaml")
    from do_not_change.read_yaml.ruamel.yaml import YAML

    with open(file_path, encoding="utf-8") as f:
        s = YAML(typ="safe").load(f)
elif os.path.exists(base + ".yml"):
    file_path = os.path.abspath(base + ".yml")
    from do_not_change.read_yaml.ruamel.yaml import YAML

    with open(file_path, encoding="utf-8") as f:
        s = YAML(typ="safe").load(f)
elif os.path.exists(base + ".json"):
    file_path = os.path.abspath(base + ".json")
    import json

    with open(file_path, encoding="utf-8") as f:
        s = json.load(f)
elif os.path.exists(base + ".ini"):
    file_path = os.path.abspath(base + ".ini")
    import configparser

    parser = configparser.ConfigParser()
    parser.read(file_path, encoding="utf-8")
    s = {section: dict(parser[section]) for section in parser.sections()}
elif os.path.exists(base + ".env"):
    file_path = os.path.abspath(base + ".env")
    s = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            s[key.strip()] = value.strip()
elif os.path.exists(base + ".txt"):
    file_path = os.path.abspath(base + ".txt")
    s = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            s[k.strip()] = v.strip()
else:
    s = custom_error_dictionary()
    import sys

    sys.exit()
# ==================================================

# convert strings to float
# ==================================================

# identifies strings that python recognises as normal float convertable:
float_regex = r"\s*[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?\s*"


# tests if string & if math operation between 2 float convertables:
def is_match(x, symbol):
    return isinstance(x, str) and bool(re.match(f"^{float_regex}[{symbol}]{float_regex}$", x))


# tests if string & if math operation between 3 float convertables:
def is_match2(x, symbol1, symbol2):
    return isinstance(x, str) and bool(re.match(f"^{float_regex}[{symbol1}]{float_regex}[{symbol2}]{float_regex}$", x))


# str to float
s = {
    key: float(val) if (isinstance(val, str) and bool(re.match(f"^{float_regex}$", val))) else val
    for key, val in s.items()
}
# a+b
s = {
    key: float(val.split("+")[0]) + float(val.split("+")[1]) if is_match(val, "+") else val  # type:ignore
    for key, val in s.items()
}
# a-b
s = {
    key: float(val.split("-")[0]) - float(val.split("-")[1]) if is_match(val, "-") else val  # type:ignore
    for key, val in s.items()
}
# a*b
s = {
    key: float(val.split("*")[0]) * float(val.split("*")[1]) if is_match(val, "*") else val  # type:ignore
    for key, val in s.items()
}
# a/b
s = {
    key: float(val.split(r"/")[0]) / float(val.split(r"/")[1]) if is_match(val, r"/") else val  # type:ignore
    for key, val in s.items()
}
# a^b
s = {
    key: float(val.split("^")[0]) ** float(val.split("^")[1]) if is_match(val, r"\^") else val  # type:ignore
    for key, val in s.items()
}
# a*b^c
s = {
    key: float(val.split("*")[0])  # type:ignore
    * float(val.split("*")[1].split("^")[0])  # type:ignore
    ** float(val.split("*")[1].split("^")[1])  # type:ignore
    if is_match2(val, "*", r"\^")
    else val
    for key, val in s.items()
}
# a/b^c
s = {
    key: float(val.split(r"/")[0])  # type:ignore
    / float(val.split(r"/")[1].split("^")[0])  # type:ignore
    ** float(val.split(r"/")[1].split("^")[1])  # type:ignore
    if is_match2(val, r"/", r"\^")
    else val
    for key, val in s.items()
}

# convert to custom dicitonary:
s = custom_error_dictionary(**s)
# ==================================================
