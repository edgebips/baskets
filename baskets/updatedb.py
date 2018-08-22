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


def get_driver(driver, args):
    """Get or create a new driver."""
    driver = driver or driverlib.create_driver(args.driver_exec,
                                               headless=args.headless)
    driverlib.reset(driver)
    return driver


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

    # Update the list of etfs.
    driver = fetch_holdings('__LIST__', 'Nasdaq', None, args, db)
    listfilename = database.getlatest(db, '__LIST__')
    downloader = issuers.get('Nasdaq', False)
    etflist = downloader.parse(listfilename)
    etfindex = etflist.index('ticker')

    # Fetch baskets for each of those.
    for row in sorted(assets):
        if not row.issuer:
            try:
                issuer = etfindex[row.ticker].issuer
            except KeyError:
                raise ValueError("Was not able to infer issuer for {}".format(row.ticker))
        else:
            issuer = row.issuer
        driver = fetch_holdings(row.ticker, issuer, driver, args, db)

    if driver:
        driver.close()


def fetch_holdings(ticker, issuer, driver, args, db):
    """Fetch the holdings file."""
    downloader = issuers.get(issuer, args.ignore_missing_issuer)

    # Check if the file has already been downloaded.
    csvfile = database.getlatest(db, ticker)
    if csvfile is not None:
        logging.info("Skipping %s; already downloaded", ticker)
        return driver

    # Fetch the file.
    logging.info("Fetching holdings for %s", ticker)
    driver = get_driver(driver, args)
    filenames = downloader.download(driver, ticker)
    if filenames is None:
        logging.error("No files found for %s", ticker)
        return driver

    # Write out the downloaded file to database location.
    csvdir = database.getdir(db, ticker, datetime.date.today())
    os.makedirs(csvdir, exist_ok=True)
    for filename in filenames:
        dst = path.join(csvdir, path.basename(filename))
        logging.info("Copying %s -> %s", filename, dst)
        shutil.copyfile(filename, dst)

    return driver


if __name__ == '__main__':
    main()
