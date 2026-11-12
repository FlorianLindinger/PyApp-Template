# Licensing

This repository is a project template and may contain components governed by different licenses. The sections below define which license applies to each part of the repository.

## 1. Main project files

Except for the paths listed in Sections 2 and 3, all files in this repository are governed by the license chosen by the project author:

```text
[Replace this notice with the complete text of your chosen project license. 

Until that placeholder is replaced, no license is granted for those files beyond rights provided by applicable law.]
```



## 2. PyApp-Template backend

The files in **`code/pyapp/DONT_CHANGE`** are provided by [PyApp-Template](https://github.com/FlorianLindinger/PyApp-Template). The backend is licensed under the MIT License; its text is in **`code/pyapp/DONT_CHANGE/LICENSE.md`**, which also names the bundled third-party files (xterm.js, MIT as well).

## 3. Python distributions and third-party packages

The following directories, including all files and subdirectories within them, are not covered by the licenses described in Sections 1 or 2:

* **`code/pyapp/generated/.venv`** (the app's virtual environment with third-party packages)
* **`code/pyapp/generated/pythons`** (Python distributions installed by uv)
* **`code/pyapp/generated/uv`** (the uv executables)
* **`code/pyapp/generated/uv-cache`** (downloaded package files)

Any third-party packages located below a distribution's `Lib/site-packages` directory are also included in this exception because they are descendants of the relevant distribution directory.

Each Python distribution and third-party package remains governed by its own license terms. Those terms are normally included in the distribution, package, or associated metadata, such as `LICENSE`, `NOTICE`, or `.dist-info` files. Preserve those files when redistributing the corresponding components.

## 4. Git sharing and other distribution

The repository's current `.gitignore` rules exclude all directories listed in Section 3. The intended Git repository therefore contains the project source and dual-licensed template files, but not installed or generated Python distributions and packages.

`.gitignore` controls which files Git normally tracks; it does not change the license of any file. If you force-add an excluded file, change the ignore rules, or distribute a populated project folder by another method, you are responsible for complying with the license terms of every included Python distribution and third-party package.
