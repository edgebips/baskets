"""Download holdings from iShares.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import time
import csv
import logging
from typing import List

from selenium.common import exceptions

from baskets import driverlib
from baskets import utils
from baskets.table import Table


def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    findurl = 'https://www.ishares.com/us/products/etf-product-list'
    logging.info("Opening %s", findurl)
    driver.get(findurl)

    logging.info("Narrowing search %s", findurl)
    element = driver.find_element_by_id('searchInPage')
    element.send_keys(symbol)
    time.sleep(2)

    logging.info("Clicking on instrument page")
    try:
        element = driver.find_element_by_link_text(symbol)
        element.click()
    except exceptions.WebDriverException:
        logging.info("Click away the annoying survey popup")
        element = driver.find_element_by_link_text("No")
        element.click()
        # Try again.
        element = driver.find_element_by_link_text(symbol)
        element.click()

    time.sleep(2)
    logging.info("Clicking on portfolio")
    element = driver.find_element_by_link_text("Portfolio")
    element.click()

    time.sleep(2)
    logging.info("Clicking on holdings download link")
    element = driver.find_element_by_link_text("Detailed Holdings and Analytics")
    element.click()

    logging.info("Waiting for downloads")
    driverlib.wait_for_downloads(driver, '.*\.csv$')

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Table:
    header, outrows = find_table(filename)
    tbl = Table(header, [str] * len(header), outrows)

    # Create fraction column.
    tbl = utils.create_fraction_from_market_value(tbl, 'market_value')

    # Add ticker column.
    if 'Ticker' in header:
        tbl = (tbl
               .create('asstype', lambda _: 'Equity')
               .map('ticker', str.strip))
    else:
        tbl = (tbl
               .create('asstype', lambda _: 'FixedIncome')
               .create('ticker', lambda _: ''))
    return (tbl
            .map('sedol', lambda sedol: '' if sedol == '-' else sedol)
            .select(['fraction', 'asstype', 'name', 'ticker', 'sedol', 'isin']))


def find_table(filename: str) -> List[str]:
    with open(filename) as infile:
        reader = csv.reader(infile)
        for row in reader:
            if row == ['\xa0']:
                break
        else:
            logging.fatal("Could not find start of table")
            return
        header = next(reader)
        outrows = []
        for row in reader:
            if row == ['\xa0']:
                break
            outrows.append(row)
    return header, outrows
