set "shortcut_location=..\..\..\test_qt.lnk"
set "wdir="
set "path_to_terminal_emulator_exe=%~dp0compiled\run.exe"
set "icon_file=..\..\icons\icon.ico"
set "use_qt_terminal=1"
set "app_id=appid1"
set "args_for_target="
set "args_for_script=""test"""

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_target%" "%args_for_script%"

set "shortcut_location=..\..\..\test_windows.lnk"
set "use_qt_terminal=0"
set "app_id=appid2"

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_target%" "%args_for_script%"

set "shortcut_location=..\..\..\test_python_qt.lnk"
set "use_qt_terminal=1"
set "app_id=appid3"
set "path_to_terminal_emulator_exe=""%SystemRoot%\py.exe"""
set "args_for_target=-3 ""%~dp0pyside6_terminal.py"""

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_target%" "%args_for_script%"

set "shortcut_location=..\..\..\test_cmd_qt.lnk"
set "app_id=appid4"
set "path_to_terminal_emulator_exe=cmd.exe"
set "args_for_target=/k ""py -3 %~dp0pyside6_terminal.py"
set "args_for_script=""test"""""

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_target%" "%args_for_script%"