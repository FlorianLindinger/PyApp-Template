######################################################################################################################################################
# Add code at the bottom that runs after a python crash (if
# restart_main_code_on_crash=0 in "non-user_settings.ini" -
# otherwise it will run main_code.py again).
######################################################################################################################################################
# Import the user defined variables (given in settings.yaml)
# with the code lines below (e.g. "name: variable" in settings.yaml
# can be accessed here with s["name"])
######################################################################################################################################################
# autopep8: off
import yaml  # install as pyyaml                                      
import re                                                             
with open("settings.yaml") as file: s = yaml.safe_load(file)  # get values with s["name"]	          
# Fix what yaml can't interpret: Converts scientific notaion (as exepted in python) and math operation (+-*/) of 2 float convertables (including scientific notaion) to float:
float_regex = r"\s*[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?\s*"  # identifies strings that python recognises as float convertable 
def is_match(x, symbol): return (isinstance(x, str) and bool(re.match(f"^{float_regex}[{symbol}]{float_regex}$", x)))  # test if string & if math operation between 2 float convertables 
s = {key: float(val) if (isinstance(val, str) and bool(re.match(f"^{float_regex}$", val))) else val for key, val in s.items()} 
s = {key: float(val.split(r"/")[0])/float(val.split(r"/")[1]) if is_match(val, r"/") else val for key, val in s.items()}     #type:ignore
s = {key: float(val.split("^")[0])**float(val.split("^")[1]) if is_match(val, r"\^") else val for key, val in s.items()}     #type:ignore
s = {key: float(val.split("*")[0])*float(val.split("*")[1]) if is_match(val, "*") else val for key, val in s.items()}        #type:ignore
s = {key: float(val.split("+")[0])+float(val.split("+")[1]) if is_match(val, "+") else val for key, val in s.items()}        #type:ignore
s = {key: float(val.split("-")[0])-float(val.split("-")[1]) if is_match(val, "-") else val for key, val in s.items()}        #type:ignore
# autopep8: on
######################################################################################################################################################