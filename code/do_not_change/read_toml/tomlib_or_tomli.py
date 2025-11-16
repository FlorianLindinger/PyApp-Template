# prefer builting tomllib over legacy tomli in python 3.11+
try:
    import tomllib as _toml  # Python 3.11+
except ModuleNotFoundError:  # older Python, use vendored tomli
    import tomli as _toml


TOMLDecodeError = _toml.TOMLDecodeError
load = _toml.load
loads = _toml.loads
