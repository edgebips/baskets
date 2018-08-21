"""Download holdings from iShares.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import time
import csv
import logging
from typing import List

from selenium.common import exceptions

from beancount.utils import csv_utils

from baskets import driverlib
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
    tbl = (Table(header, [str] * len(header), outrows)
           .map('market_value', clean_amount))
    total_value = sum(tbl.values('market_value'))
    tbl = tbl.create('fraction', lambda row: row.market_value/total_value)
    if 'Ticker' in header:
        tbl = tbl.select(['ticker', 'fraction', 'name'])
    else:
        tbl = (tbl
               .update('name', update_name)
               .create('ticker', lambda _: '')
               .select(['ticker', 'fraction', 'name']))
    return (tbl
            .map('ticker', str.strip)
            .rename(('name', 'description')))


def update_name(row):
    return 'BOND: {}'.format(row.name)


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


def clean_amount(string: str) -> float:
    """Convert $ amount to a float."""
    clean_str = string.replace('$', '').replace(',', '')
    return float(clean_str) if clean_str else D('0')
