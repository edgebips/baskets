#!/usr/bin/env python3
"""Install script for Ameritrade package.
"""
__copyright__ = "Copyright (C) 2018-2020  Martin Blais"
__license__ = "GNU GPLv2"

import sys

from setuptools import setup

if sys.version_info[:2] < (3,):
    raise SystemExit("ERROR: Insufficient Python version; you need v3 or higher.")

setup(
    name="baskets",
    version='0.1',
    description="ETF Holdings Downloader, Parser and Disaggregator",

    license="GNU GPLv2 only",
    author="Martin Blais",
    author_email="blais@furius.ca",
    url="http://github.com/blais/baskets",
    download_url="http://github.com/blais/baskets",

    packages = [
        'baskets',
        'baskets/issuers',
    ],

    install_requires = [
        'requests',
        'xlrd',
        'openpyxl',
        'selenium',
        'networkx',
        'numpy',
        'pandas',
        'pytest',
    ]
)
