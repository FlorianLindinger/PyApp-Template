####################################################################################################################################
# Add code at the bottom that runs with the start of the program.
####################################################################################################################################
# imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"]):
from settings import s
####################################################################################################################################


import time

for i in range(50):
    print(i)
    time.sleep(0.1)