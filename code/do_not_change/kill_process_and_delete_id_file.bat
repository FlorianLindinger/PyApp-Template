@ECHO OFF
SET process_id_file_path=%~1
SET /p PID=<"%process_id_file_path%"

TASKKILL /PID %PID% /T /F
DEL "%process_id_file_path%"

PAUSE