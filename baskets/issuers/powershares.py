"""Download holdings from PowerShares.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import csv
import logging

from baskets import driverlib
from baskets import utils
from baskets.table import Table


def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    # Invesco actually has a direct link to the holdings page.
    url = ('https://www.invesco.com'
           '/portal/site/us/financial-professional/etfs/holdings/'
           '?ticker={}'.format(symbol))
    logging.info("Opening %s", url)
    driver.get(url)

    logging.info("Downloading")
    element = driver.find_element_by_partial_link_text('Excel Download')
    element.click()

    logging.info("Waiting for downloads")
    driverlib.wait_for_downloads(driver, r'.*\.csv$')

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Table:
    """Parse the PowerShares holdings file."""
    with open(filename) as infile:
        reader = csv.reader(infile)
        header = next(reader)
        rows = list(reader)
    tbl = Table(header, [str] * len(header), rows)

    # Compute market value.
    tbl = utils.create_fraction_from_market_value(tbl, 'marketvalue')

    # Create asset type column.
    tbl = tbl.create('asstype', lambda _: 'Equity')

    # Create identifier columns.
    tbl = (tbl
           .check(['name'])
           .rename(('holdingsticker', 'ticker'))
           .map('ticker', str.strip)
           .rename(('securitynum', 'cusip')))
    # What about 'securitynum'? What is it?

    return tbl.select(['fraction', 'asstype', 'name', 'ticker', 'cusip'])
