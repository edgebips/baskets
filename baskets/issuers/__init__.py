"""Implementation of downloaders and parsers for issuers.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging

from . import americanfunds
from . import globalx
from . import ishares
from . import powershares
from . import spdr
from . import vanguard
from .meta import nasdaq

MODULES = {
    'AmericanFunds': americanfunds,
    'GlobalX': globalx,
    'Nasdaq': nasdaq,
    'PowerShares': powershares,
    'SPDR': spdr,
    'Vanguard': vanguard,
    'iShares': ishares,
}


def get(issuer: str):
    """Get an issuer implementation.
    This function optionally exits the program on failure."""
    return MODULES.get(issuer)
