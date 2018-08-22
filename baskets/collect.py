"""Update the holdings database with missing or the newest files.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import argparse
import collections
import logging

import numpy

from baskets import table
from baskets.table import Table
from baskets import beansupport
from baskets import database
from baskets import issuers
from baskets import graph


def normalize_holdings_table(tbl: Table) -> Table:
    """The assets don't actually sum to 100%, normalize them."""
    total = sum([row.fraction for row in tbl])
    if not 0.98 < total < 1.02:
        logging.error("Total weight seems invalid: %s", total)
    scale = 1. / total
    return tbl.map('fraction', lambda f: f*scale)


ASSTYPES = {'Equity', 'FixedIncome', 'ShortTerm'}
IDCOLUMNS = ['name', 'ticker', 'sedol', 'isin', 'cusip']
COLUMNS = ['etf', 'account', 'fraction', 'asstype'] + IDCOLUMNS


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
    parser.add_argument('--dbdir', default=database.DEFAULT_DIR,
                        help="Database directory to write all the downloaded files.")
    parser.add_argument('-i', '--ignore-missing-issuer', action='store_true',
                        help="Ignore positions where the issuer implementation is missing")
    parser.add_argument('-o', '--ignore-options', action='store_true',
                        help=("Ignore options positions "
                              "(only works with  Beancount export file)"))
    parser.add_argument('-l', '--ignore-shorts', action='store_true',
                        help="Ignore short positions")

    parser.add_argument('-F', '--full-table', action='store',
                        help="Path to write the full table to.")

    parser.add_argument('-A', '--agg-table', action='store',
                        help="Path to write the full table to.")

    parser.add_argument('-D', '--debug-output', action='store',
                        help="Path to debugging output of grouping algorithm.")

    args = parser.parse_args()
    db = database.Database(args.dbdir)

    # Load up the list of assets from the exported Beancount file.
    assets = beansupport.read_assets(args.assets_csv, args.ignore_options)
    assets.checkall(['ticker', 'account', 'issuer', 'price', 'quantity'])

    assets = assets.order(lambda row: (row.issuer, row.ticker))
    if 0:
        print()
        print(assets)
        print()

    # Fetch baskets for each of those.
    tickermap = collections.defaultdict(list)
    alltables = []
    for row in assets:
        if row.quantity < 0 and args.ignore_shorts:
            continue

        if not row.issuer:
            holdings = Table(['fraction', 'asstype', 'ticker'],
                             [str, str, str],
                             [[1.0, 'Equity', row.ticker]])
        else:
            downloader = issuers.get(row.issuer, args.ignore_missing_issuer)

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
        holdings = holdings.create('etf', lambda _: row.ticker)
        holdings = holdings.create('account', lambda _: row.account)
        holdings = holdings.select(COLUMNS)

        # Convert fraction to dollar amount.
        dollar_amount = row.quantity * row.price
        holdings = (holdings
                    .create('amount', lambda row: row.fraction * dollar_amount)
                    .delete(['fraction']))

        alltables.append(holdings)
    fulltable = table.concat(*alltables)

    # Aggregate the holdings.
    aggtable, annotable = graph.group(fulltable, args.debug_output)
    if args.agg_table:
        with open(args.agg_table, 'w') as outfile:
            table.write_csv(aggtable, outfile)

    # Write out the full table.
    logging.info("Total amount from full holdings table: {:.2f}".format(
        numpy.sum(fulltable.array('amount'))))
    logging.info("Total amount from full holdings table: {:.2f}".format(
        numpy.sum(annotable.array('amount'))))
    if args.full_table:
        with open(args.full_table, 'w') as outfile:
            table.write_csv(annotable, outfile)

    # Cull out the tail of holdings for printing.
    tail = 0.90
    amount = aggtable.array('amount')
    total_amount = numpy.sum(amount)
    logging.info('Total: {:.2f}'.format(total_amount))
    cum_amount = numpy.cumsum(amount)
    headsize = len(amount[cum_amount < total_amount * tail])
    print(aggtable.head(headsize))


if __name__ == '__main__':
    main()
