# This script is just a shortcut to the actual script (at relative_path_to_actual_script) to have a shorter path in Windows shortcuts

relative_path_to_actual_script = "specific_scripts\\start_program.py"

###################

import os
import subprocess
import sys

###################

args = [
    sys.argv[1],
    "1",
]  # [app_id,create_terminal] # create_terminal is "1" to create a terminal, "0" to not create a terminal

script_path = os.path.join(os.path.dirname(__file__), relative_path_to_actual_script)

result = subprocess.run([sys.executable, script_path, *args])  # noqa:S603

sys.exit(result.returncode)
