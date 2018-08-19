"""Download holdings from StateStreet SPDRs.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import time
import logging

from selenium.common import exceptions

from baskets import driverlib


def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = 'https://us.spdrs.com/en/etf/spdr-sp-500-etf-SPY'
    logging.info("Opening %s", url)
    driver.get(url)

    logging.info("Holdings")
    element = driver.find_element_by_link_text('HOLDINGS')
    element.click()
    time.sleep(1)

    logging.info("Downloading")
    element = driver.find_element_by_partial_link_text('Download All Holdings')
    element.click()

    logging.info("Waiting for downloads")
    driverlib.wait_for_downloads(driver, '.*\.xls$')

    return driverlib.get_downloads(driver)
