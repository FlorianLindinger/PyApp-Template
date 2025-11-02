# ==============================================================================
# Add code at the bottom that runs with the start of the program.
# ==============================================================================
# Optional: Imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"]). Alternatively use settings.py directly.
from settings import s # <-needs pyyaml package # noqa isort: skip type: ignore fmt: off
# ==============================================================================


import time

for i in range(50):
    print(i)
    time.sleep(0.1)
