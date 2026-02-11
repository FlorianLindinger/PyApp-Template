

import subprocess
import sys
import os

print(os.getcwd())

file_dir=os.path.dirname(os.path.abspath(__file__))


exe = file_dir+"\\compiled\\run.exe"
args = sys.argv[1:]

result = subprocess.run([exe, *args], check=False)
print("exit code:", result.returncode)
