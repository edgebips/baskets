"""Implementation of downloaders and parsers for issuers.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging

from . import vanguard
from . import ishares
from . import powershares
from . import spdr
from . import americanfunds
from .meta import nasdaq

MODULES = {'Vanguard': vanguard,
           'iShares': ishares,
           'PowerShares': powershares,
           'SPDR': spdr,
           'AmericanFunds': americanfunds,
           # For lists.
           'Nasdaq': nasdaq}


def get(issuer: str):
    """Get an issuer implementation.
    This function optionally exits the program on failure."""
    return MODULES.get(issuer)
