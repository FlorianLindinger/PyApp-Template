# Dual License with Third-Party Exceptions

Except for the files listed under "Third-party exceptions", all files in this directory and its subdirectories are available under either of the following licenses, at your choice:

* [MIT License](LICENSES/MIT.txt)
* [Apache License 2.0](LICENSES/Apache-2.0.txt)

The corresponding SPDX license expression is:

```text
MIT OR Apache-2.0
```

You may use the covered files under either license. You do not have to comply with both licenses simultaneously.

## Third-party exceptions

The ASCII-art fonts in `data/fonts` (used for the app name banner, see `scripts/banner.py`) keep their own licenses; each file also names its authors in its header:

* **`data/fonts/standard.flf`**: "Standard" FIGlet font by Glenn Chappell and Ian Chai, part of the FIGlet distribution: [BSD 3-Clause License](LICENSES/BSD-3-Clause-FIGlet.txt).
* **`data/fonts/coder_mini.flf`**: "Coder Mini" by Loic Cressot: [MIT License](LICENSES/MIT-coder_mini.txt).
* **`data/fonts/future.tlf`**: "Future" TOIlet font by Sam Hocevar: [WTFPL, Version 2](LICENSES/WTFPL.txt).
* **`data/fonts/future_smooth.tlf`**: "Future Smooth" by John Goodliff, based on "Future" by Sam Hocevar: [WTFPL, Version 2](LICENSES/WTFPL.txt).

## Distribution note

uv, the Python distributions it installs and the app's third-party packages live outside this directory (see the project's root `LICENSE.md`) and keep their own licenses. `.gitignore` does not alter licensing terms. If you distribute a prepared folder, retain the license and notice files of every included distribution and package.
