"""Dependency-free entry point for validating an existing or staged backend."""

import sys
from importlib.metadata import version


def main():
    import ctypes
    import ssl

    import pipreqs.pipreqs
    import rich

    # Importing proves the runtime can load its native and required Python modules.
    assert ctypes and ssl and rich and pipreqs.pipreqs
    expected, requirements = sys.argv[1:]
    if sys.version.split()[0] != expected:
        raise RuntimeError("Backend Python version does not match configuration")
    with open(requirements, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, expected_version = line.split("==", 1)
            if version(name.strip()) != expected_version.strip():
                raise RuntimeError("Backend dependency version mismatch: " + name)


if __name__ == "__main__":
    main()
