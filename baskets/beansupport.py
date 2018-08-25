"""Support loading from Beancount.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import re

from baskets import table


def AssetsTable(rows):
    """A table describing the list of assets."""
    return table.Table(['ticker', 'issuer', 'quantity'],
                       [str, str, float],
                       rows)


def get_ticker(row) -> str:
    """Get the ticker corresponding to the value in 'export' column.
    This involves removing the exchange, if present.
    """
    if not row.export:
        return row.currency if row.currency != row.cost_currency else ''
    else:
        exch, _, symbol = row.export.partition(':')
        if not symbol:
            symbol = exch
        return symbol


def safefloat(v: str, default: float = 1):
    """Create a float from the column if not empty."""
    return float(v) if v else default


def read_portfolio(filename: str, unused_ignore_options: bool = False):
    """Dispatch the reader function between regular and Beancount."""
    match = re.match(r'beancount:(.*)', filename)
    return (read_exported_portfolio(match.group(1))
            if match
            else read_regular_portfolio(filename))


def read_regular_portfolio(filename: str):
    """Read the public file format for assets."""
    with open(filename) as infile:
        assets = table.read_csv(infile)
    assets.checkall(['ticker', 'account', 'issuer', 'price', 'quantity'])
    return (assets
            .map('price', float)
            .map('quantity', float))


def read_exported_portfolio(filename: str, ignore_options: bool = False) -> table.Table:
    """Load a file in beancount.projects.export format."""
    tbl = table.read_csv(filename)
    if ignore_options:
        tbl = tbl.filter(lambda row: row.assetcls != 'Options')
    tbl = (tbl
           .select(['account_abbrev', 'currency', 'cost_currency', 'export',
                    'number', 'issuer',
                    'price_file', 'rate_file'])
           .rename(('account_abbrev', 'account'))
           .map('price_file', safefloat)
           .map('rate_file', safefloat)
           .map('number', float)
           .rename(('number', 'quantity'))
           .create('ticker', get_ticker)
           .delete(['export', 'currency'])
           .filter(lambda row: bool(row.ticker))
           .create('price', lambda row: row.price_file * row.rate_file)
           .delete(['price_file', 'rate_file'])
           .group(('ticker', 'account', 'issuer', 'price'), 'quantity', sum)
           .order(lambda row: (row.ticker, row.issuer, row.account, row.price))
           .checkall(['ticker', 'account', 'issuer', 'price', 'quantity']))
    return tbl
