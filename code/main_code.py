from pyqt5_helpers import Q_file_path
import traceback

try:
    from pyqt5_helpers import *

    Q_start()

    widget = Q_sidebar_GUI()
    
    widget.sidebar.add(QLabel("test"))
    widget.sidebar.add(Q_file_path(label="test"))
    
    # widget.sidebar.add(QLabel("test"))
    

    Q_end(widget)
except SystemExit:
    pass
except:
    print(traceback.format_exc())
    input("Press enter to exit")

# # ==============================================================================
# # Add code at the bottom that runs with the start of the program.
# # ==============================================================================
# # Optional: Imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"]). Alternatively use settings.py directly.
# from settings import s # <-needs pyyaml package # noqa isort: skip type: ignore fmt: off
# # ==============================================================================

# import time

# for i in range(50):
#     print(i)
#     time.sleep(0.1)

