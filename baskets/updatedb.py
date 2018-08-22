"""Collect the holdings of a portfolio of assets.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import os
from os import path
import argparse
import datetime
import logging
import shutil

from baskets.table import Table
from baskets import beansupport
from baskets import driverlib
from baskets import database
from baskets import issuers


def HoldingsTable(rows):
    """Normalized extracted contents of an holdings file download."""
    return Table(['ticker', 'fraction', 'description'],
                 [str, float, str],
                 rows)


def main():
    """Update the database of holdings for ETFs in the portfolio."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())

    parser.add_argument('assets_csv',
                        help=('A CSV file which contains the tickers of assets and '
                              'number of units'))
    parser.add_argument('--dbdir', default=database.DEFAULT_DIR,
                        help="Database directory to write all the downloaded files.")
    parser.add_argument('-i', '--ignore-missing-issuer', action='store_true',
                        help="Ignore positions where the issuer implementation is missing")
    parser.add_argument('-o', '--ignore-options', action='store_true',
                        help=("Ignore options positions "
                              "(only works with  Beancount export file)"))

    parser.add_argument('--headless', action='store_true',
                        help="Run without poppping up the browser window.")
    parser.add_argument('-b', '--driver-exec', action='store',
                        default="/usr/local/bin/chromedriver",
                        help="Path to chromedriver executable.")
    args = parser.parse_args()
    db = database.Database(args.dbdir)

    # Load up the list of assets from the exported Beancount file.
    assets = beansupport.read_assets(args.assets_csv, args.ignore_options)

    # Fetch baskets for each of those.
    driver = None
    for row in sorted(assets):
        downloader = issuers.get(row.issuer, args.ignore_missing_issuer)

        # Check if the file has already been downloaded.
        csvfile = database.getlatest(db, row.ticker)
        if csvfile is not None:
            logging.info("Skipping %s; already downloaded", row.ticker)
            continue

        # Fetch the file.
        csvdir = database.getdir(db, row.ticker, datetime.date.today())
        logging.info("Fetching holdings for %s", row.ticker)
        driver = driver or driverlib.create_driver(args.driver_exec,
                                                   headless=args.headless)
        driverlib.reset(driver)

        filenames = downloader.download(driver, row.ticker)
        if filenames is None:
            logging.error("No files found for %s", row.ticker)
            continue
        os.makedirs(csvdir, exist_ok=True)
        for filename in filenames:
            dst = path.join(csvdir, path.basename(filename))
            logging.info("Copying %s -> %s", filename, dst)
            shutil.copyfile(filename, dst)
    if driver:
        driver.close()


if __name__ == '__main__':
    main()
