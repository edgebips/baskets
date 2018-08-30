"""Download holdings from Global X.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import time

import requests

from baskets import driverlib
from baskets.table import Table
from baskets import table
from baskets import utils


def download(driver, symbol: str):
    """Get the list of holdings for Global X."""

    # Note: This works too, but doesn't get us the default filename.
    # resp = requests.get(url, params={'download_full_holdings': 'true'})

    # Note: This somehow doesn't work in headless mode. I don't know why.

    url = ('https://www.globalxfunds.com/funds/{}/'.format(symbol.lower()) +
           '?download_full_holdings=true')
    logging.info("Opening %s", url)
    driver.get(url)

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Table:
    """Parse the SPDRs holdings file."""

    with open(filename) as infile:
        next(infile)  # Title row
        next(infile)  # Date tow
        tbl = table.read_csv(infile)

    # Compute market value.
    tbl = utils.create_fraction_from_market_value(tbl, 'market_value')

    # I think it's all equity for that issuer AFAIK.
    tbl = tbl.create('asstype', lambda _: 'Equity')

    # Select what we got (not much).
    return tbl.select(['name', 'asstype', 'fraction'])
