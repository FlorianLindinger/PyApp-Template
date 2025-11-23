# ==============================================================================
# Add code at the bottom that runs after a python crash (if
# restart_main_code_on_crash=false in "non-user_settings.ini" -
# otherwise it will run the main code again with the argument "crashed").
# Python can check for this with sys.argv[-1]=="crashed".
# You can delete this file if you don't want to run any code when it would be executed
# ==============================================================================

# put your code below that you want executed in case of a python crash of main code:

import msvcrt
import sys

print()
print("[Error] Python has crashed (see above). Press any key to exit.")
msvcrt.getch()  # waits for any key press
sys.exit(0)
