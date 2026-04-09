import os

#############################
# variables

make_abs = lambda x: os.path.normpath(file_dir + x)  # noqa
get_dir = lambda x: os.path.dirname(x)  # noqa

file_dir = get_dir(make_abs(__file__)) + "\\"

developer_settings_path = make_abs("..\\..\\developer_settings.py")
developer_settings_dir=get_dir(developer_settings_path)

portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs("..\\..\\py_env")

backend_python_exe_path = make_abs("..\\P\\P.exe")

script_wrapper_path = make_abs("script_wrapper.py")

python_scripts_folder_path = make_abs("..\\..\\")
icon_path = make_abs("..\\..\\icons\\icon.ico")

compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

#############################
# process variables

if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))
