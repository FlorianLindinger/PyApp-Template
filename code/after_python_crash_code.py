####################################################################################################################################
# Add code at the bottom that runs after a python crash (if
# restart_main_code_on_crash=0 in "non-user_settings.ini" -
# otherwise it will run main_code.py again with the argument "crashed").
# Python can check for this with sys.argv[-1]=="crashed".
# You can delete this file if you don't want to run any code when it would be executed
####################################################################################################################################
from settings import s # imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"])
####################################################################################################################################