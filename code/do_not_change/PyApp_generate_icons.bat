@ECHO OFF

SETLOCAL EnableDelayedExpansion

magick -version >nul 2>&1
IF %errorlevel% NEQ 0 (
    echo: Problem: ImageMagick program not found. Install manually (https://imagemagick.org/script/download.php^) and restart or automatically (via winget^) by just presssing any key and restarting after the installation is finished.
    PAUSE > NUL
    ECHO:
    ECHO: Automatically installing...
  winget install -e --id ImageMagick.ImageMagick.Q16 --accept-package-agreements --accept-source-agreements
    ECHO:
    IF !errorlevel!==0 (
      ECHO: Sucessfully installed ImageMagick. Restart to generate icons. Press any key to exit.
    ) ELSE (
      ECHO: Installation failed. Please (re^)install manually (https://imagemagick.org/script/download.php^) and restart to generate icons. Press any key to exit.
    )
    PAUSE > NUL
    EXIT 0
)

@REM generate icon.ico
magick "icon.png" -define icon:auto-resize=16,32,48,64,128,256 -compress zip "icon.ico"

IF %errorlevel% NEQ 0 (
  ECHO:
  ECHO: Failed to generate icon.ico (see above^)
  ECHO:
)

@REM generate settings.ico (icon.ico as base and settings.png in corner)
magick icon.ico[5] ^
  -set option:OW "%%[fx:int(w*0.6)]" -set option:OH "%%[fx:int(h*0.6)]" ^
  ( settings.png -resize "%%[option:OW]x%%[option:OH]" ) ^
  -gravity southeast -composite ^
  -background none -alpha on -define icon:auto-resize=256,128,64,48,32,16 settings.ico

IF %errorlevel% NEQ 0 (
  ECHO:
  ECHO: Failed to generate settings.ico (see above^)
  ECHO:
)

@REM generate stop.ico (icon.ico as base and stop.png in corner)
magick icon.ico[5] ^
  -set option:OW "%%[fx:int(w*0.6)]" -set option:OH "%%[fx:int(h*0.6)]" ^
  ( stop.png -resize "%%[option:OW]x%%[option:OH]" ) ^
  -gravity southeast -composite ^
  -background none -alpha on -define icon:auto-resize=256,128,64,48,32,16 stop.ico

IF %errorlevel% NEQ 0 (
  ECHO:
  ECHO: Failed to generate stop.ico (see above^). Press any key to exit.
  PAUSE > NUL
  EXIT 1
  ECHO:
) else (
    ECHO:
    ECHO: Icons (.ico files^) should have been generated in current folder if no errors above. Press any key to exit.
    PAUSE > NUL
    EXIT 0
)

