@echo off & setlocal enabledelayedexpansion

call :prompt_user "Delete existing environment and reinstall Python + venv + packages? (Y/N)"
echo %OUTPUT%
echo !OUTPUT!
if "!OUTPUT!"=="1" ( 
    echo 1
) else (
    echo 0
)

goto :EOF



::::::::::::::::::::::::::::::::::::::::::::::::
:: function that prompts user with prompt=arg1 and sets OUTPUT=1 for y and OUTPUT=0 for n.
::::::::::::::::::::::::::::::::::::::::::::::::
:prompt_user
setlocal
set "ans="
:ask
set /p "ans=%1"
if /i "%ans%"=="y" (
    set "OUTPUT=1"
) else if /i "%ans%"=="n" (
    set "OUTPUT=0"
) else (
    echo Invalid input. Please enter y or n.
    goto ask
)
endlocal & set "OUTPUT=%OUTPUT%"
goto :EOF
:: =================================================