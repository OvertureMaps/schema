from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-places-theme")
except PackageNotFoundError:
    __version__ = "unknown"
