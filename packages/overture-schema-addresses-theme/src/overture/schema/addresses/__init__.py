"""Addresses theme.

Geographic address point features with flexible administrative levels and location data
structures.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .address import Address

__all__ = ["Address"]
