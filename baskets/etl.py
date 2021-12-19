"""Petl globals initialization and related utilities."""

import re
import decimal
from decimal import Decimal

import petl
import petl.config
petl.config.look_style = 'minimal'
petl.config.failonerror = True


def convert_number(string: str)-> decimal.Decimal:
    """Convert an amount with parens and dollar sign to Decimal."""
    if string is None:
        return Decimal(0)
    string = string.strip()
    if not string:
        return Decimal(0)
    match = re.match(r"\((.*)\)", string)
    if match:
        string = match.group(1)
        sign = -1
    else:
        sign = 1
    cstring = string.strip(' $').replace(',', '').replace(' p', '')
    try:
        return Decimal(cstring) * sign
    except decimal.InvalidOperation as exc:
        raise decimal.InvalidOperation(f"Invalid conversion of {cstring!r}") from exc


# def create_fraction_from_market_value(tbl: Table, column: str) -> Table:
#     """Create a 'fraction' column computed from the market value column."""
#     tbl = tbl.map(column, convert_dollar_amount)
#     total_value = sum(max(0, value) for value in tbl.itervalues(column))
#     return tbl.create('fraction', lambda row: max(0, getattr(row, column))/total_value)
