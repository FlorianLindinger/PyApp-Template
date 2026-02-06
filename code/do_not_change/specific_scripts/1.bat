@echo off

:: move to folder of this file (needed for relative paths).
:: current_file_path variable needed as workaround for nieche Windows bug where this file gets called with quotation marks:
set "current_file_path=%~dp0"
cd /d "%current_file_path%"

call "start_program.bat"