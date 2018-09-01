"""Misc reusable utiliites."""

__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"


import os
from os import path

from baskets.table import Table


def abslistdir(directory):
    """Listdir() with absolute values."""
    filenames = []
    for filename in os.listdir(directory):
        filenames.append(path.join(directory, filename))
    return filenames


def convert_dollar_amount(string: str) -> float:
    """Convert $ amount to a float."""
    clean_str = string.replace('$', '').replace(',', '')
    return float(clean_str) if clean_str else 0


def create_fraction_from_market_value(tbl: Table, column: str) -> Table:
    """Create a 'fraction' column computed from the market value column."""
    tbl = tbl.map(column, convert_dollar_amount)
    total_value = sum(max(0, value) for value in tbl.itervalues(column))
    return tbl.create('fraction', lambda row: max(0, getattr(row, column))/total_value)


def empty_dashes(value: str):
    """Convert single dash strings to empty strings."""
    return '' if value == '-' else value
