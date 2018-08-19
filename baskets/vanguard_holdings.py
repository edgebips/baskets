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


# class AssetsTable(table.DefTable):
#     """An input table for assets.
#     This is the input you provide to list your assets and quantities.
#     """
#     field_types = [
#         ('ticker', str),
#         ('issuer', str),
#         ('quantity', float),
#     ]


class HoldingsTable(Table):
    """A table of downloaded holdings.
    This is the common output type we convert all the downloads to.
    """
    _columns = ['ticker', 'fraction', 'description']
    _types = [str, float, str]


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


def get_holdings(driver, download_dir, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = ("https://advisors.vanguard.com"
           "/web/c1/fas-investmentproducts/{}/portfolio".format(symbol))
    logging.info("Fetching %s", url)
    driver.get(url)
    time.sleep(2)
    element = driver.find_element_by_link_text("Holding details")
    element.click()

    element = driver.find_element_by_link_text("Export data")
    element.click()

    filenames = abslistdir(download_dir)
    if len(filenames) != 1:
        logging.error("Invalid filenames from download: %s", filenames)
    else:
        with open(filenames[0]) as infile:
            contents = infile.read()
    for filename in filenames:
        os.remove(filename)
    return contents


# FIXME: Move this to utils.
def abslistdir(directory):
    for filename in os.listdir(directory):
        yield path.join(directory, filename)


def load_tables(filename: str) -> Dict[str, Table]:
    """Load tables from the CSV file."""
    with open(filename) as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    sections = csv_utils.csv_split_sections_with_titles(rows)
    table_map = {title: Table(rows[0], rows[1:])
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

    return Table(ptable.columns, rows)


def pct_to_fraction(string):
    if re.match(r'<0\.', string):
        return 0
    else:
        return float(string.replace('%', '')) / 100.


def parse_equity(table):
    """Parse the Equity table."""
    indexes = [table.columns.index(name)
               for name in ['Ticker', '% of funds*', 'Holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        [row[ticker_idx].strip(), pct_to_fraction(row[pct_idx]), row[desc_idx]]
        for row in table.rows])


def parse_fixed_income(table):
    """Parse the Fixed income table."""
    indexes = [table.columns.index(name)
               for name in ['SEDOL', '% of funds*', 'Holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['SEDOL:{}'.format(row[ticker_idx].strip()), pct_to_fraction(row[pct_idx]), row[desc_idx]]
        for row in table.rows])

def parse_shortterm_reserves(table):
    """Parse the Short-term reserves table."""
    indexes = [table.columns.index(name)
               for name in ['% of funds*', 'Holdings']]
    pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['CASH', pct_to_fraction(row[pct_idx]), row[desc_idx]]
        for row in table.rows])


def load_beancount_assets(filename: str) -> Table:
    """Load a file in beancount.projects.export format."""
    tbl = table.read_csv(filename)
    tbl = tbl.select(['export', 'number', 'cost_currency', 'issuer'])
    def clean_ticker(export) -> str:
        exch, _, symbol = export.partition(':')
        if not symbol:
            symbol = exch
        return symbol
    tbl = (tbl
           .map('number', float)
           .map('export', clean_ticker)
           .filter(lambda row: bool(row.export))
           .filter(lambda row: bool(row.issuer))
           .group(('export', 'issuer'), 'number', sum)
           .order(lambda row: (row.issuer, row.export))
           .rename('export', 'ticker'))
    return tbl


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
    tbl = load_beancount_assets(args.assets_csv)
    for row in tbl:
        print(row.ticker)

    # Clean up the downloads dir.
    for filename in abslistdir(DOWNLOADS_DIR):
        logging.error("Removing file: %s", filename)
        os.remove(filename)

    # Fetch baskets for each of those.
    driver = None
    for currency, symbol in sorted(issuer_currencies):
        outfilename = path.join(args.output, '{}.csv'.format(currency))
        if path.exists(outfilename):
            logging.info("Skipping %s; already downloaded", currency)
            continue
        logging.info("Fetching holdings for %s (via %s)", currency, symbol)
        driver = driver or create_driver(args.driver_exec, headless=args.headless)
        contents = get_holdings(driver, DOWNLOADS_DIR, symbol)
        with open(outfilename, 'w') as outfile:
            outfile.write(contents)
    if driver:
        driver.close()

    # Extract tables from each downloaded file.
    norm_table_map = {}
    for filename in abslistdir(args.output):
        table = load_tables(filename)
        norm_table_map[filename] = table

    # Compute a sum-product of the tables.




if __name__ == '__main__':
    main()
