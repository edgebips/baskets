===============================================================
   baskets: ETF Holdings Downloader,Parser and Disaggregator
===============================================================

Introduction
--------------------

`baskets` is a project that provides Python library code that, given a list of
Exchange Trade Funds and quantities, can

1. automatically download the compositions of those ETFs (i.e., the list of
   holdings) from the issuer's web pages and maintain a lightweight database of
   those downloads at multiple dates, and

2. collect the list of holdings and from the fractional constituents of each ETF
   reconstruct the dollar amount exposure to each constituent stock.

If you invest mostly with ETFs / baskets of stocks, it essentially answers the
question: "What's my exposure to stock X?"


Motivation
--------------------

You may be surprised that none of the brokers currently offer this service, and
that automatically scraping the list of holdings from the issuers web pages is
made difficult on purpose (although always available, as retail investors may
want this information). However, download formats that would be convenient to
pull from a computer program in a common format are typically only offered to
financial institutions, or for an expensive fee (e.g., see services like
etf.com, etfdb.com, etc.). I preferred to cook my own, since I had to write code
on top anyway.


Usage
--------------------

Two Python scripts are provided for the two aforementioned tasks:
`basksets-updatedb` and `baskets-portfolio`.


Input Format
--------------------

The tools require you to provide your portfolio in order to provide it with a
list of ETFs and their quantities. The input format is a CSV file with the
following fields:

- `ticker`: The ETF symbol, in capital letters. Individual stock symbols are
  supported as well (if no issuer is supplied, it is assumed that the position
  is for a single stock; see `issuer field below).

- `account`: The account which holds the ETF. This is used for detailed
  reporting whereby we list the presence of a particular stock in various ETFs
  and accounts. You can put any value here, it's a free-form string.

- `issuer`: The financial company which issues the ETF, that is, which allows
  traders to create or redeem it. Examples include iShares_, Vanguard_,
  PowerShares, SPDRs, and `more <http://etfdb.com/issuers/>`_. See the
  baskets/issuers directory for supported sources.

- `price`: The current price of the ETF. This project does not implement
  automatically price fetching, so you must provide the price of each instrument
  (manually, or perhaps via a script).

- `quantity`: number of shares of that ETF or stock which you hold. This is used
  along with the price to compute the dollar amount.

.. _iShares: http://www.ishares.com
.. _Vanguard: https://investor.vanguard.com/etf/list
.. _PowerShares: http://www.invescopowershares.com
.. _SPDRs: https://us.spdrs.com

Here's an example input file::

  ticker,account,issuer,price,quantity
  VFINX,Vanguard:401k,Vanguard,104.32,648.2332
  VHT,Schwab,Vanguard,169.87,230
  VNQ,Schwab,Vanguard,82.17,400
  VTI,Schwab,Vanguard,145.78,1235

Installation
--------------------

You need a recent Python-3 (at the time of writing this I've been developing
using Python-3.7).

You will need to install the following Python libraries:

- requests
- xlrd
- openpyxl
- selenium
- networkx
- numpy
- pandas
- pytest

You can install them like this:

  python3 -m pip install -r requirements.txt

Install this package:

  python3 -m pip install .

Furthermore, you will need a WebDriver implementation for Selenium to control to
fetch the holdings pages (from baskets-updatedb). You *need* the Chrome
WebDriver, the others aren't guaranteed to work (I've witnessed the Firefox
WebDriver fail on some pages, for example). Git it here:

  https://sites.google.com/a/chromium.org/chromedriver/

Untar the binary and install it under `/usr/loca/bin/chromedriver`.
Alternatively, `baskets-updatedb` accepts the `--driver-exec=` option where you
can provide the location of your WebDriver executable.
