# This script is just a shortcut to the actual script (at relative_path_to_actual_script) to have a shorter path in Windows shortcuts

try:
    relative_path_to_actual_script = "specific_scripts\\start_program.py"

    ###################

    import os
    import runpy
    import sys

    ###################

    script_path = os.path.join(os.path.dirname(__file__), relative_path_to_actual_script)

    sys.argv = [
        script_path,
        sys.argv[1],  # app id
        "1",  # create_terminal: 1" = create, "0" = not
    ]

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

        sys.exit(exit_code)

except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed before start of program with error: {e}:")
    print("=" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")
    sys.exit(1)
