import traceback

try:
    from pyqt5_helpers import *

    Q_start()

    widget = Q_sidebar_GUI()
    
    # widget.sidebar.add(QLabel("test"))

    Q_end(widget)
except SystemExit:
    pass
except:
    print(traceback.format_exc())
    input("Press enter to exit")
