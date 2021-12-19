"""Download holdings from Global X.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import argparse
import logging
import re
import time

import requests
import petl
from selenium import webdriver

from baskets import etl
from baskets import driverlib
from baskets import utils


def download(driver, symbol: str):
    """Get the list of holdings for Global X."""
    url = ('https://www.globalxetfs.com/funds/{}/?download_full_holdings=true'
           .format(symbol.lower()))
    logging.info("Opening %s", url)
    driver.get(url)
    files = driverlib.wait_for_downloads(driver.downloads_dir)
    return files[0]


def parse(filename: str) -> petl.Table:
    """Parse the holdings file."""

    table = (petl.fromcsv(filename)
             .skip(1)
             .skipcomments('Fund Holdings Data')
             .skipcomments('The information contained herein')
             .convert(['Market Price ($)', 'Shares Held', 'Market Value ($)'],
                      etl.convert_number)
             .rename({
                 '% of Net Assets': 'pct_net_assets',
                 'Ticker': 'symbol',
                 'Name': 'name',
                 'SEDOL': 'sedol',
                 'Market Price ($)': 'price',
                 'Shares Held': 'shares',
                 'Market Value ($)': 'market_value',
             })
             )

    total_market_value = table.values('market_value').sum()
    table = (table
             .addfield('fraction', lambda r: 100 * r.market_value / total_market_value)
             )

    total_fraction = table.values('fraction').sum()

    return table

    # Compute market value.
    tbl = utils.create_fraction_from_market_value(tbl, 'market_value')

    # I think it's all equity for that issuer AFAIK.
    tbl = tbl.create('asstype', lambda _: 'Equity')

    # Select what we got (not much).
    return tbl.select(['name', 'asstype', 'fraction'])


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('symbol', help='Name of ETF to download')
    args = parser.parse_args()

    driver = driverlib.create_driver("/snap/bin/chromium.chromedriver", headless=True)
    filename = download(driver, args.symbol)
    table = parse(filename)
    print(table.lookallstr())


if __name__ == '__main__':
    main()
