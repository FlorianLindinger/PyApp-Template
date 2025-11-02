# ==============================================================================
# Add code at the bottom that runs after a python crash (if
# restart_main_code_on_crash=0 in "non-user_settings.ini" -
# otherwise it will run main_code.py again with the argument "crashed").
# Python can check for this with sys.argv[-1]=="crashed".
# You can delete this file if you don't want to run any code when it would be executed
# ==============================================================================

# put your code here that you want executed in case of a python crash of main code

import msvcrt
import sys

print("Python has crashed (see above). Press any key to exit.")
msvcrt.getch()  # waits for any kepress
sys.exit(0)
