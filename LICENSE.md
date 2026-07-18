# Licensing

This repository is a project template and may contain components governed by different licenses. The sections below define which license applies to each part of the repository.

## 1. Main project files

Except for the paths listed in Sections 2 and 3, all files in this repository are governed by the license chosen by the project author:

```text
[Replace this notice with the complete text of your chosen project license.]
```

Until that placeholder is replaced, no license is granted for those files beyond rights provided by applicable law.

## 2. PyApp Template backend

The files in **`code/backend/DONT_CHANGE`**, except for the two third-party directories listed in Section 3, are provided by [PyApp Template](https://github.com/FlorianLindinger/PyApp-Template) and are available under either the MIT License or the Apache License 2.0, at the recipient's choice (`MIT OR Apache-2.0`).

The license choice, complete license texts, and applicable exceptions are documented in **`code/backend/DONT_CHANGE/LICENSE.md`** and its **`LICENSES`** directory.

## 3. Python distributions and third-party packages

The following directories, including all files and subdirectories within them, are not covered by the licenses described in Sections 1 or 2:

* **`code/backend/python_and_packages/python`**
* **`code/backend/python_and_packages/packages`**
* **`code/backend/DONT_CHANGE/backend_python`**
* **`code/backend/DONT_CHANGE/backend_packages`**

The `python` and `backend_python` directories contain Python distributions. The `packages` and `backend_packages` directories contain third-party Python packages. Any third-party packages located below a distribution's `Lib/site-packages` directory are also included in this exception because they are descendants of the relevant distribution directory.

Each Python distribution and third-party package remains governed by its own license terms. Those terms are normally included in the distribution, package, or associated metadata, such as `LICENSE`, `NOTICE`, or `.dist-info` files. Preserve those files when redistributing the corresponding components.

## 4. Git sharing and other distribution

The repository's current `.gitignore` rules exclude all four directories listed in Section 3. The intended Git repository therefore contains the project source and dual-licensed template files, but not installed or generated Python distributions and packages.

`.gitignore` controls which files Git normally tracks; it does not change the license of any file. If you force-add an excluded file, change the ignore rules, or distribute a populated project folder by another method, you are responsible for complying with the license terms of every included Python distribution and third-party package.
