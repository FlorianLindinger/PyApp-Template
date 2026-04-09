import os
import sys

#############################
# local variables (might also be imported by callers)

file_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"

developer_settings_path = os.path.normpath(file_dir + "..\\..\\developer_settings.py")

portable_python_installer_path = os.path.normpath(file_dir + "..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = os.path.normpath(file_dir + "..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = os.path.normpath(file_dir + "..\\..\\py_env")

backend_python_exe_path = os.path.normpath(file_dir + "..\\P\\P.exe")

script_wrapper_path = file_dir + "script_wrapper.py"

#############################
# process local variables

sys.path.insert(0, os.path.dirname(developer_settings_path))
import developer_settings

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"