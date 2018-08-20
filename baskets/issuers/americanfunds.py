"""Download holdings from American Funds.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
import csv
import logging
import re
import time
from typing import Dict

from selenium.common import exceptions

from baskets import collect
from baskets import driverlib
from baskets.table import Table


def gettext(element):
    return element.text.replace('\n', ' ')

def download(driver, symbol: str):
    """Get the list of holdings for Vanguard."""

    url = ('https://www.americanfunds.com'
           '/individual/investments/quarterlyholdings/{}'.format(symbol.lower()))
    logging.info("Opening %s", url)
    driver.get(url)

    # Get header of table.
    tbl = driver.find_element_by_id('com-mod-fund-holding-results-table')
    tr = tbl.find_element_by_tag_name('tr')
    header = [gettext(td) for td in tr.find_elements_by_tag_name('th')]

    row_end = row_last = None
    rows = []
    while row_last is None or row_end < row_last:
        paging = driver.find_element_by_class_name('paging-info')
        for span in paging.find_elements_by_tag_name('span'):
            match = re.match(r'(\d+) - (\d+) of (\d+)', span.text)
            if match:
                row_start, row_end, row_last = map(int, match.groups())
                break
        else:
            logging.error("Could not find paging info locator.")
            return

        logging.info("Reading page: %s - %s of %s", row_start, row_end, row_last)
        tbl = driver.find_element_by_id('com-mod-fund-holding-results-table')
        rowiter = iter(tbl.find_elements_by_tag_name('tr'))

        # Check header row is the same.
        tr = next(rowiter)
        _header = [gettext(td) for td in tr.find_elements_by_tag_name('th')]
        assert _header == header, (_header, header)

        for tr in rowiter:
            row = [td.text for td in tr.find_elements_by_tag_name('th')]
            rows.append(row)

        if row_end == row_last:
            break

        element = driver.find_element_by_class_name('next-btn')
        element.click()
        time.sleep(2)  # FIXME: Is there a way to wait for the page update to complete, here?

    logging.info("Writing to %s", driver.downloads_dir.name)
    filename = path.join(driver.downloads_dir.name, 'AllHoldings.csv')
    with open(filename, 'w') as tmpfile:
        writer = csv.writer(tmpfile)
        writer.writerow(header)
        writer.writerows(rows)

    return [filename]


HAS_TICKERS = False


def parse(filename: str, namemap: Dict[str,str]) -> Table:
    with open(filename) as infile:
        reader = csv.reader(infile)
        header = next(reader)
        rows = list(reader)
    tbl = (Table(header, [str] * len(header), rows)
           .map('security_name', str.strip)
           .map('market_value', clean_amount))
    total_value = sum(tbl.values('market_value'))
    tbl = (tbl
           .create('fraction', lambda row: row.market_value/total_value)
           .create('ticker', lambda row: match_name(namemap, row)))

    # Calculate how many of the names were matched.
    matched_fraction = 0
    for row in tbl:
        if row.ticker:
            matched_fraction += row.fraction
    logging.info("Matched: {:%}".format(matched_fraction))

    return (tbl
            .rename(('security_name', 'description'))
            .select(['ticker', 'fraction', 'description']))


def match_name(namemap: Dict[str,str], row) -> str:
    key = collect.normalize_name(row.security_name)
    tickers = namemap.get(key, None)
    if tickers and len(tickers) == 1:
        return next(iter(tickers))
    return ''


def clean_amount(string: str) -> float:
    """Convert $ amount to a float."""
    clean_str = string.replace('$', '').replace(',', '')
    return float(clean_str) if clean_str else D('0')
