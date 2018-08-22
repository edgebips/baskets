"""Unit tests for table library.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import textwrap
import io
from decimal import Decimal as D

from baskets import table


# FIXME: Write all the tests, this is burgeoning code.
# pylint: disable=missing-docstring


def test_constructor():
    t = table.Table(['units', 'currency'],
                    [D, str],
                    [[D('0.01'), 'USD'],
                     [D('0.02'), 'CAD'],
                     [D('0.03'), 'AUD']])
    assert isinstance(t, table.Table)
    assert isinstance(t.Row, type)
    assert issubclass(t.Row, tuple)
    assert isinstance(t.rows, list)
    assert isinstance(t.rows[0], t.Row)
    # FIXME: TODO - check invalid sizes.


def test_idify():
    assert table.idify(0, 'foo') == 'foo'
    assert table.idify(1, 'foo a') == 'foo_a'
    assert table.idify(2, '  foo  bar ') == 'foo_bar'
    assert table.idify(3, 'foo123a') == 'foo123a'
    assert table.idify(4, '') == 'col04'


def test_select():
    t = table.Table(['units', 'currency'],
                    [D, str],
                    [[D('0.01'), 'USD'],
                     [D('0.02'), 'CAD'],
                     [D('0.03'), 'AUD']])
    nt = t.select(['currency'])
    assert nt.columns == ['currency']
    assert nt.types == [str]
    assert nt.rows == list(map(nt.Row, ['USD', 'CAD', 'AUD']))


def test_update():
    t = table.Table(['units', 'currency'],
                    [D, str],
                    [[D('0.01'), 'USD'],
                     [D('0.02'), 'CAD'],
                     [D('0.03'), 'AUD']])
    nt = t.update('currency', lambda row: row.currency.lower())
    assert nt.columns == ['units', 'currency']
    assert nt.types == [D, str]
    assert nt.rows == list(map(nt.Row._make, [[D('0.01'), 'usd'],
                                              [D('0.02'), 'cad'],
                                              [D('0.03'), 'aud']]))


def test_filter():
    t = table.Table(['units', 'currency'],
                    [D, str],
                    [[D('0.01'), 'USD'],
                     [D('0.02'), 'CAD'],
                     [D('0.03'), 'AUD']])
    nt = t.filter(lambda row: row.currency == 'USD')
    assert nt.columns == t.columns
    assert nt.types == t.types
    assert nt.rows == list(map(nt.Row._make, [[D('0.01'), 'USD']]))


def test_read_csv():
    buf = io.StringIO(textwrap.dedent("""
      units,currency
      0.01,USD
      0.02,CAD
      0.03,AUD
    """))
    t = table.read_csv(buf)
    e = table.Table(['units', 'currency'],
                    [str, str],
                    [[('0.01'), 'USD'],
                     [('0.02'), 'CAD'],
                     [('0.03'), 'AUD']])
    assert t.columns == e.columns
    assert t.types == e.types
    assert t.rows == e.rows
