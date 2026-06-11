from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-base-theme")
except PackageNotFoundError:
    __version__ = "unknown"
