"""Download holdings from StateStreet SPDRs.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import logging
import time


import xlrd

from baskets import driverlib
from baskets.table import Table


def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = 'https://us.spdrs.com/en/etf/spdr-sp-500-etf-SPY'
    logging.info("Opening %s", url)
    driver.get(url)

    logging.info("Holdings")
    element = driver.find_element_by_link_text('HOLDINGS')
    element.click()
    time.sleep(1)

    logging.info("Downloading")
    element = driver.find_element_by_partial_link_text('Download All Holdings')
    element.click()

    logging.info("Waiting for downloads")
    driverlib.wait_for_downloads(driver, '.*\.xls$')

    return driverlib.get_downloads(driver)


def parse(filename: str) -> Table:
    header, rows = read_table(filename)
    tbl = Table(header, [str] * len(header), rows)

    # Use weight column as fraction directly.
    tbl = tbl.map('weight', float).rename(('weight', 'fraction'))
    total_value = sum(tbl.itervalues('fraction'))
    if not (99 <= total_value <= 101):
        logging.error("Total value is invalid: %s", total_value)
    tbl = tbl.map('fraction', lambda f: f/total_value)

    # Create asset type column.
    tbl = tbl.create('asstype', lambda _: 'Equity')

    # Add identifiers.
    tbl = (tbl
           .check(['name'])
           .rename(('identifier', 'ticker')))

    return tbl.select(['fraction', 'asstype', 'name', 'ticker'])


def read_table(filename):
    wb = xlrd.open_workbook(filename)
    sheet = wb.sheet_by_index(0)

    rowiter = sheet.get_rows()
    for cell_row in rowiter:
        row = [cell.value for cell in cell_row if cell.value]
        if len(row) > 2:
            header = row
            break
    rows = []
    for cell_row in rowiter:
        row = [cell.value for cell in cell_row if cell.value]
        if len(row) <= 1:
            break
        rows.append(row)
    return header, rows
