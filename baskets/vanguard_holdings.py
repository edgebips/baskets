#!/usr/bin/env python3
"""Download holdings from Vanguard.

Unfornuately this has to be done via Selenium.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
from pprint import pprint
import argparse
import contextlib
import csv
import logging
import os
import re
import time
from typing import Dict

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


def HoldingsTable(rows):
    """Normalized extract contents of an holdings file download."""
    return Table(['ticker', 'fraction', 'description'],
                 [str, float, str],
                 rows)


# FIXME: TODO - Create this in a temp dir.
DOWNLOADS_DIR = "/tmp/dl"

def create_driver(driver_exec: str, headless: bool = False):
    """Create a persistent web driver."""
    opts = options.Options()
    # FIXME: TODO - downloads should be a temp directory.
    prefs = {"download.default_directory" : DOWNLOADS_DIR}
    opts.add_experimental_option("prefs", prefs)
    opts.set_headless(headless)
    return webdriver.Chrome(executable_path=driver_exec, options=opts)


def retry(func, *args):
    """Autoamtically retry a failed."""
    while True:
        try:
            return func(*args)
        except selenium.common.exceptions.WebDriverException:
            time.sleep(1)
            logging.info("Retrying")


def get_holdings(driver, download_dir, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = ("https://advisors.vanguard.com"
           "/web/c1/fas-investmentproducts/{}/portfolio".format(symbol))
    logging.info("Fetching %s", url)
    driver.get(url)

    retry(driver.find_element_by_link_text, "Holding details")
    element.click()

    retry(driver.find_element_by_link_text, "Export data")
    element.click()

    filenames = utils.abslistdir(download_dir)
    if len(filenames) != 1:
        logging.error("Invalid filenames from download: %s", filenames)
    else:
        with open(filenames[0]) as infile:
            contents = infile.read()
    for filename in filenames:
        os.remove(filename)
    return contents


def parse_tables(filename: str) -> Dict[str, Table]:
    """Load tables from the CSV file."""
    with open(filename) as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    sections = csv_utils.csv_split_sections_with_titles(rows)
    table_map = {title: Table(rows[0], [str] * len(rows[0]), rows[1:])
                 for title, rows in sections.items()}
    parsers = {
        'Equity': parse_equity,
        'Fixed income': parse_fixed_income,
        'Short-term reserves': parse_shortterm_reserves,
    }
    rows = []
    for title, table in table_map.items():
        parser = parsers[title]
        ptable = parser(table)
        rows.extend(ptable.rows)

    return Table(ptable.columns, ptable.types, rows)


def normalize_holdings_table(table: Table):
    """The assets don't actually sum to 100%, normalize them."""
    total = sum([row.fraction for row in table])
    if not (0.98 < total < 1.02):
        logging.error("Total weight seems invalid: {}".format(total))
    scale = 1. / total
    return table.map('fraction', lambda f: f*scale)


def pct_to_fraction(string):
    if re.match(r'<0\.', string):
        return 0
    else:
        return float(string.replace('%', '')) / 100.


def parse_equity(table):
    """Parse the Equity table."""
    indexes = [table.columns.index(name)
               for name in ['ticker', 'pct_of_funds', 'holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        [row.ticker, pct_to_fraction(row.pct_of_funds), row.holdings]
        for row in table.rows])


def parse_fixed_income(table):
    """Parse the Fixed income table."""
    indexes = [table.columns.index(name)
               for name in ['sedol', 'pct_of_funds', 'holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['SEDOL:{}'.format(row.sedol.strip()) if row.sedol != '-' else '',
         pct_to_fraction(row.pct_of_funds),
         row.holdings]
        for row in table.rows])

def parse_shortterm_reserves(table):
    """Parse the Short-term reserves table."""
    indexes = [table.columns.index(name)
               for name in ['pct_of_funds', 'holdings']]
    pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['CASH', pct_to_fraction(row.pct_of_funds), row.holdings]
        for row in table.rows])


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('assets_csv',
                        help=('A CSV file which contains the tickers of assets and '
                              'number of units'))
    parser.add_argument('output',
                        help="Output directory to write all the downloaded files.")
    parser.add_argument('--headless', action='store_true',
                        help="Run without poppping up the browser window.")
    parser.add_argument('-b', '--driver-exec', action='store',
                        default="/usr/local/bin/chromedriver",
                        help="Path to chromedriver executable.")
    args = parser.parse_args()

    # Load up the list of assets from the exported Beancount file.
    tbl = beansupport.read_exported_assets(args.assets_csv)

    # Clean up the downloads dir.
    for filename in utils.abslistdir(DOWNLOADS_DIR):
        logging.error("Removing file: %s", filename)
        os.remove(filename)

    # Fetch baskets for each of those.
    driver = None
    for row in sorted(tbl):
        if row.issuer != 'Vanguard':
            continue

        outfilename = path.join(args.output, '{}.csv'.format(row.ticker))
        if path.exists(outfilename):
            logging.info("Skipping %s; already downloaded", row.ticker)
            continue
        logging.info("Fetching holdings for %s", row.ticker)
        driver = driver or create_driver(args.driver_exec, headless=args.headless)
        contents = get_holdings(driver, DOWNLOADS_DIR, row.ticker)
        with open(outfilename, 'w') as outfile:
            outfile.write(contents)
    if driver:
        driver.close()

    # Extract tables from each downloaded file.
    norm_table_map = {}
    _, __, filenames = next(os.walk(args.output))
    for filename in sorted(path.join(args.output, f) for f in filenames):
        logging.info("Parsing %s", filename)
        tbl = parse_tables(filename)
        norm_table_map[filename] = normalize_holdings_table(tbl)

    # Compute a sum-product of the tables.




if __name__ == '__main__':
    main()
