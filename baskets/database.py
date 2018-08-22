"""Database of daily dated downloads per key.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
import os
from typing import NamedTuple, Union
import datetime


DEFAULT_DIR = path.join(os.environ['HOME'], '.baskets/db')


Database = NamedTuple('Database', [('directory', str)])


def getdir(db: Database, key: str, date: datetime.date) -> str:
    """Get or create directory."""
    return path.join(db.directory, key, '{:%Y/%m/%d}'.format(date))


def getlatest(db: Database, key: str) -> Union[str, type(None)]:
    """Return the latest downloaded filename."""
    curdir = path.join(db.directory, key)
    try:
        for _ in range(3):
            filenames = os.listdir(curdir)
            if not filenames:
                return None
            curdir = path.join(curdir, filenames[-1])
        filenames = os.listdir(curdir)
        if filenames:
            return path.join(curdir, sorted(filenames)[-1])
    except FileNotFoundError:
        pass
    return None
