from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("clerq")
except PackageNotFoundError:
    __version__ = "unknown"
