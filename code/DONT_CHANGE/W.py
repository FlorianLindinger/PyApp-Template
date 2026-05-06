"""This script is just a shortcut to the actual script (at relative_path_to_actual_script) to have a shorter path in Windows shortcuts""" #noqa

import os
import traceback

try:
    relative_path_to_actual_script = "specific_scripts\\start_program.py"

    # ===============

    import runpy
    import sys

    # ===============

    script_path = os.path.join(os.path.dirname(__file__), relative_path_to_actual_script)

    sys.argv = [
        script_path,
        sys.argv[1],  # app id
        "terminal",  # launch mode
    ]
    
    # ===============

    try:
        runpy.run_path(script_path, run_name="__main__")
        exit_code = 0
    except SystemExit as e:
        if isinstance(e.code, int):
            exit_code = e.code
        elif e.code is None:
            exit_code = 0
        else:
            # e.code can be something else which is treated as error
            exit_code = 1
            
    # ===============

    if exit_code == 0:
        sys.exit(0)
    else:
        print()
        print()
        print("=" * 20)
        print(f'[Error] "{script_path}" returned with failure code: {exit_code}')
        print("-" * 20)
        input("[Error] Press enter to exit")
        os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script

except Exception as e:
    print()
    print()
    print("=" * 20)
    print(f'[Error] Failure in running "{__file__}": {e}')
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
