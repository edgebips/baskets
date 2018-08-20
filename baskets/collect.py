"""Update the holdings database with missing or the newest files.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
from pprint import pprint
from typing import Dict
import argparse
import collections
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


def normalize_holdings_table(table: Table) -> Table:
    """The assets don't actually sum to 100%, normalize them."""
    total = sum([row.fraction for row in table])
    if not (0.98 < total < 1.02):
        logging.error("Total weight seems invalid: {}".format(total))
    scale = 1. / total
    return table.map('fraction', lambda f: f*scale)


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
    assets = beansupport.read_exported_assets(args.assets_csv)
    assets.checkall(['ticker', 'issuer', 'price', 'number'])

    if 0:
        print()
        print(assets)
        print()

    # Fetch baskets for each of those.
    tickermap = collections.defaultdict(list)
    for row in sorted(assets):
        amount = row.number * row.price
        if not row.issuer:
            hrow = (row.ticker, 1.0, row.ticker)
            tickermap[row.ticker].append((amount, hrow))
        else:
            try:
                downloader = issuers.MODULES[row.issuer]
            except KeyError:
                logging.error("Missing issuer %s", row.issuer)
                continue

            filename = database.getlatest(db, row.ticker)
            if filename is None:
                logging.error("Missing file for %s", row.ticker)
                continue

            if not hasattr(downloader, 'parse'):
                logging.error("Parser for %s is not implemented", row.ticker)
                continue

            holdings = downloader.parse(filename)
            for hrow in holdings:
                tickermap[hrow.ticker].append((amount, hrow))

    rows = []
    for ticker, assetlist in sorted(tickermap.items(), key=lambda item: len(item[1])):
        amount = 0
        for hamount, hrow in assetlist:
            _, fraction, description = hrow
            amount += fraction * hamount
        rows.append((ticker, amount, description))
    tbl = Table(['ticker', 'amount', 'description'], [str, float, str], rows)
    print(tbl.order('amount', asc=False).head(64))


if __name__ == '__main__':
    main()
