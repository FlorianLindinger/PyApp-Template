###########################################################################
# Add code here that runs with the start of the program.
###########################################################################
# Import the user defined variables (given in ../settings.yaml)
# with the 3 code lines below (e.g. "name: variable" in ../settings.yaml
# can be accessed here with s["name"])
###########################################################################
import yaml  # install as pyyaml                            # nopep8
with open("..\settings.yaml") as file:					    # nopep8
    s = yaml.safe_load(file)  # get values with s["name"]	# nopep8
###########################################################################
