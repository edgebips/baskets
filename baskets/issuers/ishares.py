"""Download holdings from Vanguard.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import time
import logging

from selenium.common import exceptions

from baskets import driverlib


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
