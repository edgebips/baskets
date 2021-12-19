"""Utilities for webdriver & Selenium.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import argparse
import logging
import os
import re
import tempfile
import time
from os import path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service


def create_driver(executable_path: str, headless: bool = False):
    """Create a persistent web driver."""
    service = Service(executable_path)
    options = webdriver.ChromeOptions()

    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')

    # Important note: Snap package installations of Chromedriver will be
    # sandboxed to writing files only in /media. Just make sure /media/tmp
    # exists and is writable by the running user.
    root_downloads_dir = '/media/tmp'
    assert path.exists(root_downloads_dir)
    downloads_dir_obj = tempfile.TemporaryDirectory(dir=root_downloads_dir,
                                                    prefix='baskets.')
    downloads_dir = downloads_dir_obj.name
    options.add_experimental_option('prefs', {
        "download": {
            "prompt_for_download": False,
            "directory_upgrade": True,
            "default_directory"  : downloads_dir
        },
        "profile.default_content_settings.popups": 0,
    })

    driver = webdriver.Chrome(service=service, options=options)
    driver.downloads_dir_obj = downloads_dir_obj
    driver.downloads_dir = downloads_dir
    return driver


def get_downloads(downloads_dir: str):
    """Get the list of downloaded files after running the driver."""
    return [path.join(downloads_dir, fn)
            for fn in os.listdir(downloads_dir)
            if not re.match(r'.*\.crdownload$', fn)]


def wait_for_downloads(downloads_dir: str, pattern: str = None):
    """Block until the downloads directory has at least one non-temp file."""
    while True:
        filenames = os.listdir(downloads_dir)
        okfiles = [fn
                   for fn in filenames
                   if (not re.match(r'.*\.crdownload$', fn) and
                       (not pattern or re.match(pattern, fn)))]
        if okfiles:
            break
    return [path.join(downloads_dir, fn) for fn in okfiles]


def retry(func, *args):
    """Automatically retry a failed."""
    while True:
        try:
            return func(*args)
        except WebDriverException:
            time.sleep(1)
            logging.info("Retrying")
