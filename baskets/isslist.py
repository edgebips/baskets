"""Burgeoning code to attempt to infer issuer from ETF."""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from baskets import database
from baskets import issuers


def infer(driver):
    """Update ETF list and return a function to infer."""
    # Update the list of etfs.
    driver = fetch_holdings('__LIST__', 'Nasdaq', driver, args, db)
    listfilename = database.getlatest(db, '__LIST__')
    downloader = issuers.get('Nasdaq')
    assert downloader
    etflist = downloader.parse(listfilename)
    etfindex = etflist.index('ticker')

    # Attempt to infer missing issuers.
    def try_infer_issuer(row):
        if row.issuer:
            return row.issuer
        else:
            try:
                return etfindex[row.ticker].issuer
            except KeyError:
                logging.info("Was not able to infer issuer for {}".format(row.ticker))
                return ''
    return try_infer_issuer
