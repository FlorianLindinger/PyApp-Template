Code in this folder is from PyApp-Template (https://github.com/FlorianLindinger/PyApp-Template) (originally started) by Florian Lindinger

==================================
=== Folder content explanation ===
==================================

T.py, N.py, Q.py, and S.py are shortcuts to scripts in the specific_scripts folder which are needed to have a short path in the Windows shortcuts that calls them.

The file called "!DO NOT CHANGE STUFF IN THIS FOLDER" is just an extra warning not to change stuff.

P is a minimal (deleted unneeded files) embedded Python folder to run the backend framework code of PyApp-Template but not the main code itself which is run by a managed full Python of specific version with specific packages.

general_scripts contains general purpose scripts.

icon_related contains icons and icon related code.

terminal_emulator is code for the fancy terminal emulator.

The remaining files are self explanatory.

===========================
=== Python folder ("P") ===
===========================

Contents are Python 3.12 (embeddible version)

Deleted to safe space:
	sqlite3.dll
	python.cat

Changed python312._pth to:
	python312.zip
	.
	..\python_packages
	..\..

	# Uncomment to run site.main() automatically
	# import site

Renamed python.exe to P.exe

==================================================
=== Python packages folder ("python_packages") ===
==================================================

Installed packages in python_packages. Commands ran within python_packages folder:

py -3.12 -m pip install pip --upgrade
py -3.12 -m pip install --target . --upgrade rich 
py -3.12 -m pip install --target . --upgrade win11toast
py -3.12 -m pip install --target . --upgrade yarg 
py -3.12 -m pip install --target . --upgrade docopt
py -3.12 -m pip install --target . --upgrade pipreqs --no-deps 

============================================