# This script is just a shortcut to the actual script (at relative_path_to_actual_script) to have a shorter path in Windows shortcuts

relative_path_to_actual_script = r"specific_scripts\open_settings.py"

import os
import subprocess
import sys

script_path = os.path.join(os.path.dirname(__file__), relative_path_to_actual_script)
python_exe = sys.executable

result = subprocess.run([python_exe, script_path])  # noqa:S603

sys.exit(result.returncode)