"""Makes "import pyapp_api" work when main.py runs without the launcher (python main.py).

Under the launcher, "import pyapp_api" gets the launcher's helpers directly and this file is not
used. The helpers themselves are in pyapp/DONT_CHANGE/app_api.py, which is updated with the
launcher; this file only forwards to it, so it never needs changing. Keep it if you use pyapp_api.
"""

from pyapp.DONT_CHANGE.app_api import *  # noqa: F403
from pyapp.DONT_CHANGE.app_api import __all__  # noqa: F401
