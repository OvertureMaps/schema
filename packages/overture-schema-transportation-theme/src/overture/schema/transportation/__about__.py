from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-transportation-theme")
except PackageNotFoundError:
    __version__ = "unknown"
