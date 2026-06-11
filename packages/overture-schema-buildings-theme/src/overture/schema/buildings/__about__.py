from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-buildings-theme")
except PackageNotFoundError:
    __version__ = "unknown"
