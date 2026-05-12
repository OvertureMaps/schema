"""
Types supporting the recognized status scope.
"""

from enum import Enum


class RecognizedStatus(str, Enum):
    """
    Status of the person or entity travelling as recognized by authorities controlling the particular
    location.
    """

    AS_PERMITTED = "as_permitted"
    AS_PRIVATE = "as_private"
    AS_DISABLED = "as_disabled"
    AS_EMPLOYEE = "as_employee"
    AS_STUDENT = "as_student"
