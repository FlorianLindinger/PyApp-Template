set "shortcut_location=..\..\..\test_qt.lnk"
set "wdir="
set "path_to_terminal_emulator_exe=%~dp0compiled\run.exe"
set "icon_file=..\..\icons\icon.ico"
set "use_qt_terminal=1"
set "app_id=appid1"
set "args_for_script=test"

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_script%"

set "shortcut_location=..\..\..\test_windows.lnk"
set "use_qt_terminal=0"
set "app_id=appid2"

call py create_shortcut_for_compiled.py "%shortcut_location%" "%wdir%" "%path_to_terminal_emulator_exe%" "%icon_file%" "%use_qt_terminal%" "%app_id%" "%args_for_script%"