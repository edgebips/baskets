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
import traceback

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


# FIXME: Remove this function and put this state as part of an object in
# driverlib. Merge with downloads_dir attribute. The 'real' driver needs a
# proxy. Call it something appropriate and different than 'driver'.
def get_driver(driver, args):
    """Get or create a new driver."""
    driver = driver or driverlib.create_driver(args.driver_exec,
                                               headless=not args.visible)
    driverlib.reset(driver)
    return driver


def main():
    """Update the database of holdings for ETFs in the portfolio."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())

    parser.add_argument('portfolio',
                        help=('A CSV file which contains the tickers of assets and '
                              'number of units'))
    parser.add_argument('--dbdir', default=database.DEFAULT_DIR,
                        help="Database directory to write all the downloaded files.")
    parser.add_argument('-i', '--ignore-missing-issuer', action='store_true',
                        help="Ignore positions where the issuer implementation is missing")
    parser.add_argument('-o', '--ignore-options', action='store_true',
                        help=("Ignore options positions "
                              "(only works with  Beancount export file)"))

    parser.add_argument('--visible', action='store_true',
                        help="Run with a visible browser window (not headless).")
    parser.add_argument('-b', '--driver-exec', action='store',
                        default="/usr/local/bin/chromedriver",
                        help="Path to chromedriver executable.")
    args = parser.parse_args()
    db = database.Database(args.dbdir)

    # Load up the list of assets from the exported Beancount file.
    assets = beansupport.read_portfolio(args.portfolio, args.ignore_options)

    # Fetch baskets for each of those.
    driver = None
    for row in sorted(assets):
        if not row.issuer and args.ignore_missing_issuer:
            logging.warning("Ignoring missing issuer for {}".format(row.ticker))
            continue
        try:
            driver, _ = fetch_holdings(row.ticker, row.issuer, driver, db,
                                       args.ignore_missing_issuer, args)
        except Exception:
            traceback.print_exc()
            continue
    if driver:
        driver.close()


def fetch_holdings(ticker, issuer, driver, db, ignore_missing_issuer, args):
    """Fetch the holdings file."""
    downloader = issuers.get(issuer)
    if downloader is None:
        message = "Missing issuer: {}".format(issuer)
        if ignore_missing_issuer:
            logging.error(message)
            return
        else:
            raise SystemExit(message)

    # Check if the file has already been downloaded.
    today = datetime.date.today()
    csvfile = database.get(db, ticker, today)
    if csvfile is not None:
        logging.info("Skipping %s; already downloaded", ticker)
        return driver, [csvfile]

    # Fetch the file.
    logging.info("Fetching holdings for %s", ticker)
    driver = get_driver(driver, args)
    filenames = downloader.download(driver, ticker)
    if filenames is None:
        logging.error("No files found for %s", ticker)
        return driver, filenames

    # Write out the downloaded file to database location.
    csvdir = database.getdir(db, ticker, today)
    os.makedirs(csvdir, exist_ok=True)
    for filename in filenames:
        dst = path.join(csvdir, path.basename(filename))
        logging.info("Copying %s -> %s", filename, dst)
        shutil.copyfile(filename, dst)

    return driver, filenames


if __name__ == '__main__':
    main()
