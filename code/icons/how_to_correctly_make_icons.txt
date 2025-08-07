################################
HOW TO CORRECTLY MAKE AN ICON
################################

To generate correcly a .ico image:
Convert image to multi resolution icon with imagemagick program (https://imagemagick.org/script/download.php) program: run in cmd in folder containing the photo you want to convert (change filename.fileending to you photo):
magick "filename.fileending" -define icon:auto-resize=16,48,256 -compress zip "icon.ico"

################################