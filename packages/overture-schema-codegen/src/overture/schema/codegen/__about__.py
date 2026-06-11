from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("overture-schema-codegen")
except PackageNotFoundError:
    __version__ = "unknown"
