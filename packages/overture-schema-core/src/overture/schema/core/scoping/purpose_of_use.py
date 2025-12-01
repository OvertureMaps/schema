"""
Types supporting the purpose of use scope.
"""

from enum import Enum


class PurposeOfUse(str, Enum):
    """
    Reason why a person or entity travelling on the transportation network is using a particular
    location.
    """

    AS_CUSTOMER = "as_customer"
    AT_DESTINATION = "at_destination"
    TO_DELIVER = "to_deliver"
    TO_FARM = "to_farm"
    FOR_FORESTRY = "for_forestry"
