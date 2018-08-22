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

MODULES = {'Vanguard': vanguard,
           'iShares': ishares,
           'PowerShares': powershares,
           'SPDR': spdr,
           'AmericanFunds': americanfunds}


def get(issuer: str, ignore_missing_issuer: bool):
    """Get an issuer implementation.
    This function optionally exits the program on failure."""
    try:
        return MODULES[issuer]
    except KeyError:
        message = "Missing issuer: {}".format(issuer)
        if ignore_missing_issuer:
            logging.error("%s; Skipping", message)
            return None
        else:
            logging.fatal("%s; Exiting", message)
            raise SystemExit(message)
