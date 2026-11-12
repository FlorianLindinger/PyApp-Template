"""A terminal emulator in the browser for Windows console programs (see README.md).

Self-contained: standard library only, Python 3.8+, no imports from outside this folder, so the
folder can be copied into any project. Importing the package is cheap; the host (host.py, with
its Windows API setup) is only loaded when it runs.
"""
