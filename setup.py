#!/usr/bin/env python3
"""Install script for Ameritrade package.
"""
__copyright__ = "Copyright (C) 2018  Martin Blais"
__license__ = "GNU GPLv2"

import sys

if sys.version_info[:2] < (3,):
    raise SystemExit("ERROR: Insufficient Python version; you need v3 or higher.")

setup(
    name="ameritrade",
    version='1.0b1',
    description="Python bindings to the Ameritrade API",

    license="GNU GPLv2 only",
    author="Martin Blais",
    author_email="blais@furius.ca",
    url="http://bitbucket.org/blais/ameritrade",
    download_url="http://bitbucket.org/blais/ameritrade",

    packages = ['ameritrade'],

    install_requires = [
        'requests',
    ]
)
