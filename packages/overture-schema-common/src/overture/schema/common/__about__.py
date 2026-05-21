from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-common")
except PackageNotFoundError:
    __version__ = "unknown"
