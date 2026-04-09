import os
import sys

#############################
# variables

make_abs = lambda x: os.path.normpath(x)  # noqa
get_dir = lambda x: os.path.dirname(x)  # noqa

file_dir = get_dir(make_abs(__file__)) + "\\"

developer_settings_path = make_abs(file_dir + "..\\..\\developer_settings.py")

portable_python_installer_path = make_abs(file_dir + "..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs(file_dir + "..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs(file_dir + "..\\..\\py_env")

backend_python_exe_path = make_abs(file_dir + "..\\P\\P.exe")

script_wrapper_path = file_dir + "script_wrapper.py"

#############################
# process variables

sys.path.insert(0, get_dir(developer_settings_path))
import developer_settings # noqa

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = make_abs(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))
