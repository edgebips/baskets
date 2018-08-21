"""Utilities for webdriver & Selenium.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import os
import re
import tempfile
import time

from selenium import webdriver
from selenium.webdriver.chrome import options
from selenium.common.exceptions import WebDriverException

from baskets import utils


def create_driver(driver_exec: str, headless: bool = False):
    """Create a persistent web driver."""
    opts = options.Options()
    downloads_dir = tempfile.TemporaryDirectory('baskets.driverlib.')
    prefs = {"download.default_directory" : downloads_dir.name}
    opts.add_experimental_option("prefs", prefs)
    opts.set_headless(headless)
    driver = webdriver.Chrome(executable_path=driver_exec, options=opts)
    driver.downloads_dir = downloads_dir
    return driver


def get_downloads(driver):
    """Get the list of downloaded files after running the driver."""
    return [fn for fn in utils.abslistdir(driver.downloads_dir.name)
            if not re.match(r'.*\.crdownload$', fn)]


def wait_for_downloads(driver, pattern: str=None):
    """Block until the downloads directory has a single non-temp file."""
    while True:
        filenames = os.listdir(driver.downloads_dir.name)
        okfiles = [fn for fn in filenames
                   if (not re.match(r'.*\.crdownload$', fn) and
                       (not pattern or re.match(pattern, fn)))]
        if okfiles:
            break


def reset(driver):
    """Prepare the driver for a fresh run."""
    for filename in utils.abslistdir(driver.downloads_dir.name):
        os.remove(filename)


def retry(func, *args):
    """Autoamtically retry a failed."""
    while True:
        try:
            return func(*args)
        except WebDriverException:
            time.sleep(1)
            logging.info("Retrying")
