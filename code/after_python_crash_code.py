######################################################################################################################################################
# Add code here that runs after a python crash (if
# restart_main_code_on_crash=0 in "non-user_settings.ini" -
# otherwise it will run main_code.py again).
######################################################################################################################################################
# Import the user defined variables (given in settings.yaml)
# with the code lines below (e.g. "name: variable" in settings.yaml
# can be accessed here with s["name"])
######################################################################################################################################################
import yaml  # install as pyyaml                                      # nopep8
import re                                                             # nopep8
with open("settings.yaml") as file:				    	              # nopep8
    s = yaml.safe_load(file)  # get values with s["name"]	          # nopep8
# Fix what yaml can't interpret: Converts scientific noation (as axepted in python) and math operation (+-*/) of 2 float convertables (including scientific notaion) to float
float_regex=r"\s*[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?\s*" #identifies strings that python recognises as float convertable # nopep8
is_match=lambda x,symbol: (isinstance(x, str) and bool(re.match(f"^{float_regex}[{symbol}]{float_regex}$", x))) #test if string & if math operation between 2 float convertables # nopep8
s = {key: float(val) if (isinstance(val, str) and bool(re.match(f"^{float_regex}$",val))) else val for key, val in s.items()}  #convert to float # nopep8                                
s = {key: float(val.split("*" )[0])*float(val.split("*" )[1]) if is_match(val,"*" ) else val for key, val in s.items()}        #convert to float # nopep8   
s = {key: float(val.split(r"/")[0])/float(val.split(r"/")[1]) if is_match(val,r"/") else val for key, val in s.items()}        #convert to float # nopep8   
s = {key: float(val.split("+" )[0])+float(val.split("+" )[1]) if is_match(val,"+" ) else val for key, val in s.items()}        #convert to float # nopep8   
s = {key: float(val.split("-" )[0])-float(val.split("-" )[1]) if is_match(val,"-" ) else val for key, val in s.items()}        #convert to float # nopep8   
######################################################################################################################################################