"""Download holdings from PowerShares.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import csv
import logging
import time

from selenium.common import exceptions

from baskets import driverlib
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
    driverlib.wait_for_downloads(driver, '.*\.csv$')

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Table:
    with open(filename) as infile:
        reader = csv.reader(infile)
        header = next(reader)
        rows = list(reader)
    tbl = (Table(header, [str] * len(header), rows)
           .rename(('holdingsticker', 'ticker'), ('name', 'description'))
           .map('marketvalue', clean_amount))
    total_value = sum(tbl.values('marketvalue'))
    tbl = (tbl
           .create('fraction', lambda row: row.marketvalue/total_value)
           .select(['ticker', 'fraction', 'description'])
           .map('ticker', str.strip))
    return tbl


def clean_amount(string: str) -> float:
    """Convert $ amount to a float."""
    clean_str = string.replace('$', '').replace(',', '')
    return float(clean_str) if clean_str else D('0')
