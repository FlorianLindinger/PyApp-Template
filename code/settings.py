# Helper code used to import settings in settings.yaml as the dictionary s (e.g., value from the line "name: value"
# in settings.yaml can be accessed in python as s["name"] after the line "import settings").
# Yaml automatically interprets the data types, with vales that it can't interpret otherwise becoming strings.
# This code also converts string vales to float that yaml does not manage to interpret like some python acceptable
# scientific notation and some simple math operations between float convertables (including scientific notation).

# Implemented math operations are:
# a+b
# a-b
# a*b
# a/b
# a^b
# a*b^c
# a/b^c

# import needed packages
import re
import yaml  # install as pyyaml

# import yaml file
with open("settings.yaml") as file:
    s = yaml.safe_load(file)  # get values with s["name"]

if s != None:

    # identifies strings that python recognises as normal float convertable:
    float_regex = r"\s*[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?\s*"

    # tests if string & if math operation between 2 float convertables:

    def is_match(x, symbol):
        return (isinstance(x, str) and
                bool(re.match(f"^{float_regex}[{symbol}]{float_regex}$", x)))

    # tests if string & if math operation between 3 float convertables:

    def is_match2(x, symbol1, symbol2):
        return (isinstance(x, str) and
                bool(re.match(f"^{float_regex}[{symbol1}]{float_regex}[{symbol2}]{float_regex}$", x)))

    # Fix some of what yaml can't interpret: Converts scientific notation (as accepted in python) & implemented math operations (+-*/^) of 2/3 float convertables (including scientific notation) to float:
    s = {key: float(val) if (isinstance(val, str) and bool(
        re.match(f"^{float_regex}$", val))) else val for key, val in s.items()}
    s = {key: float(val.split("+")[0]) + float(val.split("+")[1]) if  # type:ignore
         is_match(val, "+") else val for key, val in s.items()}
    s = {key: float(val.split("-")[0]) - float(val.split("-")[1]) if   # type:ignore
         is_match(val, "-") else val for key, val in s.items()}
    s = {key: float(val.split("*")[0]) * float(val.split("*")[1]) if  # type:ignore
         is_match(val, "*") else val for key, val in s.items()}
    s = {key: float(val.split(r"/")[0]) / float(val.split(r"/")[1]) if  # type:ignore
         is_match(val, r"/") else val for key, val in s.items()}
    s = {key: float(val.split("^")[0]) ** float(val.split("^")[1]) if  # type:ignore
         is_match(val, r"\^") else val for key, val in s.items()}
    s = {key: float(val.split("*")[0]) * float(val.split("*")[1].split("^")[0]) **  # type:ignore
         float(val.split("*")[1].split("^")[1]) if  # type:ignore
         is_match2(val, "*", r"\^")
         else val for key, val in s.items()}
    s = {key: float(val.split(r"/")[0]) / float(val.split(r"/")[1].split("^")[0]) **  # type:ignore
         float(val.split(r"/")[1].split("^")[1]) if  # type:ignore
         is_match2(val, r"/", r"\^")
         else val for key, val in s.items()}
