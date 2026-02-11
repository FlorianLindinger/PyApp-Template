:: ========================
:: --- Code Description ---
:: ========================
:: This script automatically scans Python files in a specified folder to determine which packages are imported.
:: It uses 'pipreqs' to identify the dependencies and then determines the currently installed versions in a 
:: temporary environment to generate a 'requirements.txt' file with pinned versions.
::
:: Arguments (expected as predefined variables):
::   arg1: (Optional) Python executable/command to use. Defaults to 'py'.
::   arg2: (Optional) Folder path to search for Python files. Defaults to '.'.
::   arg3: (Optional) Path for the output requirements file. Defaults to 'requirements.txt'.
::   arg4: (Optional) Comma-separated list of folders to ignore.Use quotes (") around the string if spaces or commas are used. 
::
:: Execution Flow:
:: 1. Creates a temporary virtual environment.
:: 2. Installs 'pipreqs' and updates its mapping for common packages.
:: 3. Scans the target folder and generates an initial 'requirements.txt'.
:: 4. Installs the identified packages in the temp environment to verify compatibility and versions.
:: 5. Updates 'requirements.txt' with the specific versions found.
:: 6. Cleans up the temporary environment.

:: ====================================
:: --- Setup, Variables, and Checks ---
:: ====================================

:: turn off printing of commands &  make variables local (with delayed expansion):
@echo off & setlocal enabledelayedexpansion

:: handle arguments:
set "run_python_command=%~1"
set "folder_path_to_search=%~2"
set "output_file_path=%~3"
set "ignored_folders=%~4"

:: set default arguments if not set:
if "%run_python_command%"=="" set "run_python_command=py"
if "%folder_path_to_search%"=="" set "folder_path_to_search=."
if "%output_file_path%"=="" set "output_file_path=requirements.txt"
if "%ignored_folders%"=="" set "ignored_folders="

:: print info & settings:
echo.
call :print_wrap "Script to determine required python packages"
echo.
echo Settings:
echo Python Path/Command: %run_python_command%
echo Folder Path to Search: %folder_path_to_search%
echo Output File Path: %output_file_path%
echo Ignored Folders: %ignored_folders%
echo.

:: add a "," to the end of the ignored_folders string if it is not empty:
if not "%ignored_folders%"=="" (
	set "ignored_folders=%ignored_folders%,"
)

:: ensure folder path does not end with a backslash (which would escape the next quote):
if "%folder_path_to_search:~-1%"=="\" set "folder_path_to_search=%folder_path_to_search%."

:: define local variables (with relative paths being relative to this file)
REM carefull with path of tmp_venv_path because it deletes this folder afterwards
set "tmp_venv_path=%temp%\tmp_venv_for_pipreqs"
REM add a "." if otherwise backslashes are at the end:
set "mapping_file_path=%tmp_venv_path%\Lib\site-packages\pipreqs\mapping"

:: delete tmp_venv_path if it exists:
:: carefull with name because it will delete everything:
if exist "%tmp_venv_path%" (
	rmdir /s /q "%tmp_venv_path%"
)

:: check if python.exe exists:
if not exist "%run_python_command%" (
	echo [Error 1] "%run_python_command%" (first argument^) file does not exist. Aborting. Press any key to exit.
	pause > nul
	exit /b 1
)

:: ======================
:: --- Code Execution ---
:: ======================

:: print info
echo.
call :print_wrap "Creating temporary python environment and installing pipreqs"
echo.

:: create temp environment and install pipreqs:
call "%run_python_command%" -m venv "%tmp_venv_path%"
if %errorlevel% neq 0 (
	echo.
	echo [Error 3] Failed to create temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 3
)

:: activate temp environment:
call "%tmp_venv_path%\Scripts\activate.bat"   
if %errorlevel% neq 0 (
	echo.
	echo [Error 4] Failed to activate temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 4
)

:: install pipreqs:
pip install pipreqs --disable-pip-version-check > nul
if %errorlevel% neq 0 (
	echo.
	echo [Error 5] Failed to install pipreqs (package to find needed packages^) in temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 5
)

:: update mappings of pipreqs
:: ==========================
:: Format: Import:Package
:: Note: Batch variables have a character limit; for very long lists, 
set "LIST="
:: --- Computer Vision & Images ---
set "LIST=!LIST! cv2:opencv-python"
set "LIST=!LIST! PIL:Pillow"
set "LIST=!LIST! skimage:scikit-image"
set "LIST=!LIST! skvideo:scikit-video"
set "LIST=!LIST! fitz:PyMuPDF"
set "LIST=!LIST! pywt:PyWavelets"
set "LIST=!LIST! qrcode:qrcode"
:: --- Machine Learning & Data ---
set "LIST=!LIST! sklearn:scikit-learn"
set "LIST=!LIST! yaml:PyYAML"
set "LIST=!LIST! graphviz:python-graphviz"
set "LIST=!LIST! msgpack:msgpack"
:: --- Web & Networking ---
set "LIST=!LIST! dotenv:python-dotenv"
set "LIST=!LIST! dateutil:python-dateutil"
set "LIST=!LIST! googleapiclient:google-api-python-client"
set "LIST=!LIST! github:PyGithub"
set "LIST=!LIST! telegram:python-telegram-bot"
set "LIST=!LIST! jwt:PyJWT"
set "LIST=!LIST! websocket:websocket-client"
set "LIST=!LIST! paho:paho-mqtt"
set "LIST=!LIST! OpenSSL:pyOpenSSL"
set "LIST=!LIST! flask_sqlalchemy:Flask-SQLAlchemy"
set "LIST=!LIST! flask_cors:flask-cors"
:: --- Hardware & Audio ---
set "LIST=!LIST! serial:pyserial"
set "LIST=!LIST! sounddevice:sounddevice"
set "LIST=!LIST! librosa:librosa"
:: --- Database & Backend ---
set "LIST=!LIST! MySQLdb:mysqlclient"
set "LIST=!LIST! psycopg2:psycopg2-binary"
set "LIST=!LIST! sqlalchemy:SQLAlchemy"
set "LIST=!LIST! redis:redis"
set "LIST=!LIST! pymongo:pymongo"
:: --- Utilities ---
set "LIST=!LIST! comtypes:comtypes"
set "LIST=!LIST! bcrypt:bcrypt"
set "LIST=!LIST! Crypto:pycryptodome"

:: Ensure mapping file exists and print info
if not exist "%mapping_file_path%" (
	echo.
	echo ========================================
	echo [Warning] Mapping file does not exist at "%mapping_file_path%". 
	echo ========================================
	echo.
	goto skip_update_mapping
)
echo.
call :print_wrap "Update pipreqs mappings:"
echo.

:: update mappings in mapping file 
for %%A in (%LIST%) do (
    for /f "tokens=1,2 delims=:" %%I in ("%%A") do (
        set "IMPORT=%%I"
        set "PACKAGE=%%J"
        
        :: Check if the specific import already exists
        findstr /B /C:"!IMPORT!:" "%mapping_file_path%" >nul
        
        if !errorlevel! equ 0 (
            :: UPDATE LOGIC: Replace the line using a temporary file
            set "FOUND_OLD=0"
            for /f "tokens=1* delims=:" %%L in ('findstr /B /C:"!IMPORT!:" "%mapping_file_path%"') do (
                if NOT "%%M"=="!PACKAGE!" (
                    echo [UPDATE] !IMPORT!: %%M ---^> !PACKAGE!
                    set "FOUND_OLD=1"
                )
            )
            
            if !FOUND_OLD! equ 1 (
                type nul > "%mapping_file_path%.tmp"
                for /f "tokens=1* delims=:" %%L in (%mapping_file_path%) do (
                    if "%%L"=="!IMPORT!" (
                        echo !IMPORT!:!PACKAGE!>> "%mapping_file_path%.tmp"
                    ) else (
                        echo %%L:%%M>> "%mapping_file_path%.tmp"
                    )
                )
                move /y "%mapping_file_path%.tmp" "%mapping_file_path%" >nul
            )
        ) else (
            :: ADD LOGIC: Simply append
            echo [ ADD  ] !IMPORT!: !PACKAGE!
            echo !IMPORT!:!PACKAGE!>> "%mapping_file_path%"
        )
    )
)
:skip_update_mapping
:: ==========================================

:: print info
echo.
call :print_wrap "Scanning python files for needed packages in "!folder_path_to_search!""
echo.

:: get needed packages:
:: no fixed versions needed because pipreqs fails to sort out version problems -> pip will sort it out below and return a correct list
pipreqs ^
--savepath "%output_file_path%" ^
--ignore "%ignored_folders%.git,.hg,.svn,__pycache__" ^
--mode no-pin ^
--force ^
"%folder_path_to_search%"

:: check if pipreqs failed:
if %errorlevel% neq 0 (
	echo.
	echo [Error 6] Failed to get needed packages from python files (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 6
)

:: print info
echo.
call :print_wrap "Installing found packages in temporary python environment to determine the correct versions"
echo.

:: install found packages in temp venv for version determination:
pip install -r "%output_file_path%" --disable-pip-version-check
if %errorlevel% neq 0 (
	echo.
	echo [Error 7] Failed to install found packages in temporary python environment (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 7
)

:: use python to get the versions out of required packages while disregarding other packages in temp venv
python -c "import importlib.metadata; path=r'%output_file_path%'; reqs=[l.strip().lower() for l in open(path) if l.strip()]; installed={d.metadata['Name'].lower(): d.version for d in importlib.metadata.distributions()}; f=open(path, 'w'); [f.write(f'{n}=={installed[n]}\n') for n in reqs if n in installed]; f.close()"

:: check if python failed:
if %errorlevel% neq 0 (
	echo.
	echo [Error 8] Failed to get versions out of required packages (see above^). Aborting. Press any key to exit.
	pause > nul
	exit /b 8
)

:: print found packages:
echo.
call :print_wrap "Found the following packages needed in the python files (see "!output_file_path!")"
type "%output_file_path%"
echo ===========================
echo.

:: deactivate temp environment and delete:
call deactivate 

:: carefull with name because it will delete everything:
rmdir /s /q "%tmp_venv_path%"

call :print_wrap "Done. Press any key to exit."
pause > nul
exit /b 0


:: ====================
:: ==== Functions: ====
:: ====================

::::::::::::::::::::::::::::::::::::::::::::::::
:: function that prints a line of '=' characters above and below the text {arg1}
::::::::::::::::::::::::::::::::::::::::::::::::
:print_wrap
SETLOCAL Enabledelayedexpansion
set "str=%~1"
set "len=0"
:len_loop_pw
if not "!str:~%len%,1!"=="" (
    set /a len+=1
    goto :len_loop_pw
)
set "sep="
for /L %%i in (1,1,%len%) do set "sep=!sep!="
echo !sep!
echo !str!
echo !sep!
ENDLOCAL & GOTO :EOF
