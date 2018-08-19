"""Download holdings from PowerShares.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import time
import logging

from selenium.common import exceptions

from baskets import driverlib


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
