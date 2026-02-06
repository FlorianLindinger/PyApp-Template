import ctypes
import runpy
import sys

# check if arguments are valid
if len(sys.argv) < 3:
    print('Usage: run.exe "python.exe" "script.py" "AppID" [args...]')
    input("[Error] Invalid arguments. Press Enter to exit...")
    sys.exit(1)

# Parse Arguments
target_script = sys.argv[1]
myAppID = sys.argv[2]

# Set Taskbar Grouping (AppID): Such that the shortcut who provides this ID get combined with the started window in the taskbar
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)
except Exception as e:
    print(f"[Warning] Could not set AppID: {e}")

# Fix sys.argv: Now sys.argv works in target_script like it would if run directly
# Current: ['run.py', 'main.py', 'id', 'user_arg1']
# Wanted:  ['main.py', 'user_arg1']
sys.argv = [target_script] + sys.argv[3:]

# Launch script
try:
    # run_name="__main__" is crucial for if __name__ == "__main__": blocks
    runpy.run_path(target_script, run_name="__main__")
except Exception as e:
    print(f"[Error] Application crashed: {e}")
    input("Press Enter to exit...")