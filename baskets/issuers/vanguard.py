"""Download holdings from Vanguard.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import re
import csv
from typing import Dict

from baskets import csv_utils
from baskets import driverlib
from baskets import table
from baskets import utils
from baskets.driverlib import retry
from baskets.table import Table


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
    driverlib.wait_for_downloads(driver, r'.*\.csv$')

    return driverlib.get_downloads(driver)


VALUES_COLUMNS = ['market_value', 'asstype', 'holdings', 'ticker', 'sedol']


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
    tables = []
    for title, tbl in table_map.items():
        parser = parsers[title]
        subtbl = parser(tbl)
        subtbl.checkall(VALUES_COLUMNS)
        tables.append(subtbl)

    values_table = table.concat(*tables)
    # pylint: disable=bad-continuation
    return (utils.create_fraction_from_market_value(values_table, 'market_value')
            .map('ticker', lambda ticker: ticker if ticker != '-' else '')
            .rename(('holdings', 'name'))
            .map('sedol', utils.empty_dashes)
    	    .select(['fraction', 'asstype', 'name', 'ticker', 'sedol']))


def pct_to_fraction(string: str) -> float:
    """Convert % column to a fraction."""
    if re.match(r'<0\.', string):
        return 0
    else:
        return float(string.replace('%', '')) / 100.


def parse_equity(tbl: Table) -> Table:
    """Parse the Equity table."""
    return (tbl
            .create('asstype', lambda _: 'Equity')
            .map('ticker', str.strip)
            .select(VALUES_COLUMNS))


def parse_fixed_income(tbl: Table) -> Table:
    """Parse the Fixed income table."""
    return (tbl
            .create('asstype', lambda _: 'FixedIncome')
            .create('ticker', lambda _: '')
            .update('sedol', lambda row: row.sedol if row.sedol != '-' else '')
            .select(VALUES_COLUMNS))


def parse_shortterm_reserves(tbl: Table) -> Table:
    """Parse the Short-term reserves table."""
    index = None
    for fname in 'face_amount', 'face_amount_local_currency':
        if fname in tbl.columns:
            index = tbl.columns.index(fname)
            break
    assert index is not None
    return (tbl
            .create('asstype', lambda _: 'ShortTerm')
            .rename((fname, 'market_value'))
            .create('ticker', lambda _: '')
            .update('sedol', lambda row: row.sedol if row.sedol != '-' else '')
            .select(VALUES_COLUMNS))
