################################################
# Add code here that runs after a python crash (if 
# restart_main_code_on_crash=0 in other_code/non-user_settings.ini -
# otherwise it will run main_code.py again)
# Import the user defined variables (given in ../settings.py) 
# with the 3 code lines below (e.g. variable_name=variable in settings.py 
# can be accessed here as s.variable_name)
################################################
import sys                                           # nopep8
import os                                            # nopep8
sys.path.insert(0, os.path.join(sys.path[0], '..'))  # nopep8
import settings as s                                 # nopep8
################################################
