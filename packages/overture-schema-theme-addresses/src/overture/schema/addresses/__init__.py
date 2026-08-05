"""Addresses theme.

Feature types and shared components for the Overture Maps addresses theme.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .address import Address, AddressLevel

__all__ = ["Address", "AddressLevel"]
