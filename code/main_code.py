######################################################################################################################################################
# Add code here that runs with the start of the program.
######################################################################################################################################################
# Import the user defined variables (given in settings.yaml)
# with the 3 code lines below (e.g. "name: variable" in settings.yaml
# can be accessed here with s["name"])
######################################################################################################################################################
import yaml  # install as pyyaml                                      # nopep8
import re                                                             # nopep8
with open("settings.yaml") as file:				    	              # nopep8
    s = yaml.safe_load(file)  # get values with s["name"]	          # nopep8
# convert scientific notation that yaml does not recognise (yaml needs a dot and a sign in the exponent):                                     # nopep8
s = {key: float(val) if (isinstance(val, str) and bool(re.match(r"-?[0-9]+\.?[0-9]*[Ee]-?[0-9]+", val))) else val for key, val in s.items()}  # nopep8
######################################################################################################################################################
