# Dual License with Third-Party Exceptions

Except for the contents of **`backend_python`** and **`backend_packages`**, all files in this directory and its subdirectories are available under either of the following licenses, at your choice:

* [MIT License](LICENSES/MIT.txt)
* [Apache License 2.0](LICENSES/Apache-2.0.txt)

The corresponding SPDX license expression is:

```text
MIT OR Apache-2.0
```

You may use the covered files under either license. You do not have to comply with both licenses simultaneously.

## Third-party exceptions

The dual license above does not apply to the contents of these directories:

* **`backend_python`** contains a Python distribution and is governed by the license terms included in that directory, including **`backend_python/LICENSE.txt`**.
* **`backend_packages`** contains third-party Python packages. Each package is governed by its own license terms, normally included in its package directory or `.dist-info` metadata.

These exceptions include every file and subdirectory below the named directories, including third-party packages below `backend_python/Lib/site-packages` if that directory exists.

## Distribution note

The current **`.gitignore`** in this directory excludes `backend_python` and `backend_packages` from normal Git tracking. This allows the template-owned, dual-licensed files to be shared through Git without also committing installed Python or package files.

`.gitignore` does not alter licensing terms. If either excluded directory is force-added to Git or included in an archive, installer, binary distribution, or other delivery, retain its license and notice files and comply with the applicable third-party licenses.
