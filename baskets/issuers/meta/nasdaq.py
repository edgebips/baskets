"""Downloader for a list of all ETFs.

We do this in order to automtically associate each ETF to its issuer.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from typing import Dict
from os import path
import tempfile
import re

import requests

from baskets import table


def download(unused_driver, _: str) -> Dict[str, str]:
    """Download a list of ETF ticker to issuer name."""

    resp = requests.get('https://www.nasdaq.com'
                        '/investing/etfs/etf-finder-results.aspx'
                        '?download=Yes')
    tempdir = tempfile.gettempdir()
    filename = path.join(tempdir, 'etflist.csv')
    with open(filename, 'w') as outfile:
        outfile.write(resp.text)
    return [filename]


def parse(filename: str) -> table.Table:
    """Parse the NASDAQ ETFs list."""
    tbl = table.read_csv(filename)
    outrows = []
    for row in tbl:
        for regexp, issuer in [('Vanguard', 'Vanguard'),
                               ('iShares', 'iShares'),
                               ('PowerShares', 'PowerShares'),
                               ('StateStreet', 'StateStreet')]:
            if re.search(regexp, row.name):
                outrows.append((row.symbol, issuer, row.name))
                break

    return table.Table(['ticker', 'issuer', 'name'], [str, str, str], outrows)
