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


def normalize_name(name: str):
    """Normalize the company name for most accurate match against name database.
    We want to be able to use the name as a key."""
    name = re.sub(r'[^a-z0-9]', ' ', name.lower())
    name = re.sub(r'\b(ltd|inc|co|corp|plc|llc)\b', '', name)
    name = re.sub(r' +', ' ', name).strip()
    #name = tuple(sorted(name.split()))
    return name


ASSTYPES = {'Equity', 'FixedIncome', 'ShortTerm'}
IDCOLUMNS = ['name', 'ticker', 'sedol', 'isin', 'cusip']
COLUMNS = ['fraction', 'asstype'] + IDCOLUMNS


def check_holdings(holdings: Table):
    """Check that the holdings Table has the required columns."""
    actual = set(holdings.columns)

    allowed = {'asstype', 'fraction'} | set(IDCOLUMNS)
    other = actual - allowed
    assert not other, "Extra columns found: {}".format(other)

    required = {'asstype', 'fraction'}
    assert required.issubset(actual), (
        "Required columns missing: {}".format(required - actual))

    assert set(IDCOLUMNS) & actual, "No ids columns found: {}".format(actual)

    assert all(cls in ASSTYPES for cls in holdings.values('asstype'))


def add_missing_columns(tbl: Table) -> Table:
    for column in IDCOLUMNS:
        if column not in tbl.columns:
            tbl = tbl.create(column, lambda _: '')
    return tbl


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())

    parser.add_argument('assets_csv',
                        help=('A CSV file which contains the tickers of assets and '
                              'number of units'))

    parser.add_argument('-l', '--ignore-shorts', action='store_true',
                        help="Ignore short positions")
    parser.add_argument('-o', '--ignore-options', action='store_true',
                        help="Ignore options positions")

    parser.add_argument('--dbdir', default=database.DEFAULT_DIR,
                        help="Database directory to write all the downloaded files.")
    args = parser.parse_args()
    db = database.Database(args.dbdir)

    # Load up the list of assets from the exported Beancount file.
    assets = beansupport.read_exported_assets(args.assets_csv, args.ignore_options)
    assets.checkall(['ticker', 'issuer', 'price', 'number'])

    assets = assets.order(lambda row: (row.issuer, row.ticker))

    if 0:
        print()
        print(assets)
        print()

    # Fetch baskets for each of those.
    tickermap = collections.defaultdict(list)
    alltables = []
    for row in assets:
        if row.number < 0 and args.ignore_shorts:
            continue

        amount = row.number * row.price
        if not row.issuer:
            hrow = (row.ticker, 1.0, row.ticker)
            tickermap[row.ticker].append((amount, hrow, row.ticker))
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
            logging.info("Parsing file '%s' with '%s'", filename, row.issuer)

            if not hasattr(downloader, 'parse'):
                logging.error("Parser for %s is not implemented", row.ticker)
                continue

            # Parse the file.
            holdings = downloader.parse(filename)
            check_holdings(holdings)

            # Add parent ETF and fixup columns.
            holdings = add_missing_columns(holdings)
            holdings = holdings.select(COLUMNS)

            alltables.append(holdings)

            # for hrow in holdings:
            #     assert hrow.ticker.strip() == hrow.ticker, hrow.ticker
            #     tickermap[hrow.ticker].append((amount, hrow, row.ticker))

    alltable = table.concat(*alltables)
    #print(alltable)
    raise SystemExit

    rows = []
    for ticker, assetlist in sorted(tickermap.items(), key=lambda item: len(item[1])):
        amount = 0
        for hamount, hrow, basket_ticker in assetlist:
            _, fraction, description = hrow
            pos_amount = fraction * hamount
            amount += pos_amount
            if DEBUG_TICKER is not None and ticker == DEBUG_TICKER:
                print(basket_ticker, hrow, pos_amount)
        rows.append((ticker, amount, description))
    tbl = Table(['ticker', 'amount', 'name'], [str, float, str], rows)

    head = tbl.order('amount', asc=False).head(2048)
    print(head)
    table.write_csv(head, '/tmp/disag.csv')

    # FIXME: BRKB BRK.B
    # FIXME: Group SEDOL's together, many are same name.
    #print(tbl.order('amount', asc=False).head(2048).map('description', str.lower).order('description'))

    # FIXME: Include SEDOL as a column to help matching.
    # FIXME: Include ISIN as a column to help matching.
    # FIXME: Rename 'description' to 'name' everywhere.

            # #'BND', 'BNDX', 'VBTIX', 'LQD', 'NYF'
            # # Fixup missing ticker names.
            # #
            # # FIXME: Remove this and move the mapping from americanfunds.com to
            # # a second loop in here after the collection stage, and do a
            # # two-step train & classify on all the missing symbols.
            # #
            # if 0:
            #     for v in holdings.values('ticker'):
            #         if v and not re.match(r'[A-Z0-9.]+$', v):
            #             print(v, filename)
            #     #holdings = holdings.update('ticker', lambda row: row.ticker or row.description)


DEBUG_TICKER = None # 'AAPL'
#DEBUG_TICKER = 'AMAZON.COM INC'
#DEBUG_TICKER = ''


if __name__ == '__main__':
    main()
