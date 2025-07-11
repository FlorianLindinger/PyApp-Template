###########################################################################
# Add code here that runs after a python crash (if
# restart_main_code_on_crash=0 in "non-user_settings.ini" -
# otherwise it will run main_code.py again).
###########################################################################
# Import the user defined variables (given in settings.yaml)
# with the 3 code lines below (e.g. "name: variable" in settings.yaml
# can be accessed here with s["name"])
###########################################################################
import yaml  # install as pyyaml                            # nopep8
with open("settings.yaml") as file:				    	    # nopep8
    s = yaml.safe_load(file)  # get values with s["name"]	# nopep8
###########################################################################
