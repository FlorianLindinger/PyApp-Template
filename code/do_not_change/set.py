# This script is just a shortcut to the actual script (at relative_path_to_actual_script) to have a shorter path in Windows shortcuts

relative_path_to_actual_script = "specific_scripts\\open_settings.py"

###################

import os
import subprocess
import sys

###################

try:
    file_path = os.path.join(os.path.dirname(__file__), relative_path_to_actual_script)

    result = subprocess.run([sys.executable, file_path])  # noqa:S603

    sys.exit(result.returncode)

except Exception as e:
    import traceback
    print(f"[Error] An error occurred while trying to open the settings: {e}")
    print("=" * 80)
    print(traceback.format_exc())
    print()
    input("Press enter to exit.")
