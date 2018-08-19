"""Download holdings from Vanguard.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import re
from typing import Dict

# FIXME: Factor out the Table operations to their own schema; remove Pandas.
from beancount.utils import csv_utils

from selenium import webdriver

from baskets import table
from baskets.table import Table
from baskets import driverlib
from baskets.driverlib import retry


def HoldingsTable(rows):
    """Normalized extract contents of an holdings file download."""
    return Table(['ticker', 'fraction', 'description'],
                 [str, float, str],
                 rows)


def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = ("https://advisors.vanguard.com"
           "/web/c1/fas-investmentproducts/{}/portfolio".format(symbol))
    logging.info("Opening %s", url)
    driver.get(url)

    logging.info("Selecting Holding details")
    element = retry(driver.find_element_by_link_text, "Holding details")
    element.click()

    logging.info("Selecting Export data")
    element = retry(driver.find_element_by_link_text, "Export data")
    element.click()

    logging.info("Waiting for downloads")
    driverlib.wait_for_downloads(driver, '.*\.csv$')

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Dict[str, Table]:
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


def normalize_holdings_table(table: Table) -> Table:
    """The assets don't actually sum to 100%, normalize them."""
    total = sum([row.fraction for row in table])
    if not (0.98 < total < 1.02):
        logging.error("Total weight seems invalid: {}".format(total))
    scale = 1. / total
    return table.map('fraction', lambda f: f*scale)


def pct_to_fraction(string: str) -> float:
    """Convert % column to a fraction."""
    if re.match(r'<0\.', string):
        return 0
    else:
        return float(string.replace('%', '')) / 100.


def parse_equity(table: Table) -> Table:
    """Parse the Equity table."""
    indexes = [table.columns.index(name) for name in ['ticker', 'pct_of_funds', 'holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        [row.ticker, pct_to_fraction(row.pct_of_funds), row.holdings]
        for row in table.rows])


def parse_fixed_income(table: Table) -> Table:
    """Parse the Fixed income table."""
    indexes = [table.columns.index(name) for name in ['sedol', 'pct_of_funds', 'holdings']]
    ticker_idx, pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['SEDOL:{}'.format(row.sedol.strip()) if row.sedol != '-' else '',
         pct_to_fraction(row.pct_of_funds),
         row.holdings]
        for row in table.rows])


def parse_shortterm_reserves(table: Table) -> Table:
    """Parse the Short-term reserves table."""
    indexes = [table.columns.index(name) for name in ['pct_of_funds', 'holdings']]
    pct_idx, desc_idx = indexes
    return HoldingsTable([
        ['CASH', pct_to_fraction(row.pct_of_funds), row.holdings]
        for row in table.rows])
