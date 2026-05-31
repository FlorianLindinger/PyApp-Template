# print(len("============================="))
import os
import sys
import time

root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

t1 = time.time()
from DONT_CHANGE.specific_scripts.common_code import unminimize_window

t2 = time.time()
print(t2 - t1)

time.sleep(2)

t1 = time.time()
unminimize_window()
t2 = time.time()
print(t2 - t1)

# import ctypes
# import time

# user32 = ctypes.windll.user32
# kernel32 = ctypes.windll.kernel32

# SW_RESTORE = 9

# hwnd = kernel32.GetConsoleWindow()

# if hwnd:
#     user32.ShowWindow(hwnd, SW_RESTORE)  # unminimize / restore
#     time.sleep(0.5)
#     user32.SetForegroundWindow(hwnd)  # bring to front
# else:
#     print("fail")


# import ctypes
# hwnd = ctypes.windll.kernel32.GetConsoleWindow()
# ctypes.windll.user32.ShowWindow(hwnd, 9)
# ctypes.windll.user32.SetForegroundWindow(hwnd)


input("test")
