"""Download holdings from Vanguard.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import re
import csv
from typing import Dict
from decimal import Decimal as D

# FIXME: Factor out the Table operations to their own schema; remove Pandas.
from beancount.utils import csv_utils

from selenium import webdriver

from baskets import table
from baskets.table import Table
from baskets import driverlib
from baskets.driverlib import retry


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
    tables = []
    values_columns = ['ticker', 'market_value', 'holdings']
    for title, tbl in table_map.items():
        parser = parsers[title]
        subtbl = parser(tbl)
        subtbl.checkall(values_columns)
        tables.append(subtbl)

    values_table = table.concat(*tables)
    market_value = values_table.values('market_value')
    total_value = sum(market_value)
    tbl = (values_table
           .map('ticker', str.strip)
           .create('fraction', lambda row: row.market_value/total_value)
           .rename(('holdings', 'description')))
    return tbl.select(['ticker', 'fraction', 'description'])


def pct_to_fraction(string: str) -> float:
    """Convert % column to a fraction."""
    if re.match(r'<0\.', string):
        return 0
    else:
        return float(string.replace('%', '')) / 100.


def clean_amount(string: str) -> float:
    """Convert $ amount to a float."""
    clean_str = string.replace('$', '').replace(',', '')
    return float(clean_str) if clean_str else D('0')


def parse_equity(table: Table) -> Table:
    """Parse the Equity table."""
    return (table
            .map('market_value', clean_amount)
            .select(['ticker', 'market_value', 'holdings']))


def parse_fixed_income(table: Table) -> Table:
    """Parse the Fixed income table."""
    def create_ticker(row):
        return 'SEDOL:{}'.format(row.sedol.strip()) if row.sedol != '-' else ''
    return (table
            .map('market_value', clean_amount)
            .create('ticker', create_ticker)
            .select(['ticker', 'market_value', 'holdings']))


def parse_shortterm_reserves(table: Table) -> Table:
    """Parse the Short-term reserves table."""
    index = None
    for fname in 'face_amount', 'face_amount_local_currency':
        try:
            index = table.columns.index(fname)
            break
        except ValueError:
            pass
    assert index is not None
    return (table
         .map(fname, clean_amount)
         .rename((fname, 'market_value'),
                 ('sedol', 'ticker'))
         .select(['ticker', 'market_value', 'holdings']))
