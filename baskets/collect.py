"""Update the holdings database with missing or the newest files.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
from pprint import pprint
from typing import Dict
import argparse
import contextlib
import csv
import datetime
import logging
import os
import re
import shutil
import time

# FIXME: Factor out the Table operations to their own schema; remove Pandas.
from beancount.utils import csv_utils

import pandas
import requests
from selenium import webdriver
#from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome import options

from baskets import table
from baskets.table import Table
from baskets import beansupport
from baskets import utils
from baskets import driverlib
from baskets import database
from baskets import issuers


def HoldingsTable(rows):
    """Normalized extract contents of an holdings file download."""
    return Table(['ticker', 'fraction', 'description'],
                 [str, float, str],
                 rows)


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())

    parser.add_argument('assets_csv',
                        help=('A CSV file which contains the tickers of assets and '
                              'number of units'))

    parser.add_argument('--dbdir', default=database.DEFAULT_DIR,
                        help="Database directory to write all the downloaded files.")
    args = parser.parse_args()
    db = database.Database(args.dbdir)

    # Load up the list of assets from the exported Beancount file.
    tbl = beansupport.read_exported_assets(args.assets_csv)

    # Fetch baskets for each of those.
    driver = None
    for row in sorted(tbl):
        try:
            downloader = issuers.MODULES[row.issuer]
        except KeyError:
            logging.fatal("Missing issuer: %s; Skipping %s", row.issuer, row.ticker)
            continue

        # Check if the file has already been downloaded.
        csvfile = database.getlatest(db, row.ticker)
        if csvfile is None:
            logging.fatal("Missing file for %s", row.ticker)
            continue

    #     # Fetch the file.
    #     csvdir = database.getdir(db, row.ticker, datetime.date.today())
    #     logging.info("Fetching holdings for %s", row.ticker)
    #     driver = driver or driverlib.create_driver(args.driver_exec,
    #                                                headless=args.headless)
    #     driverlib.reset(driver)

    #     filenames = downloader.download(driver, row.ticker)
    #     if filenames is None:
    #         logging.error("No files found for %s", row.ticker)
    #         continue
    #     os.makedirs(csvdir, exist_ok=True)
    #     for filename in filenames:
    #         dst = path.join(csvdir, path.basename(filename))
    #         logging.info("Copying %s -> %s", filename, dst)
    #         shutil.copyfile(filename, dst)
    # if driver:
    #     driver.close()


if __name__ == '__main__':
    main()
