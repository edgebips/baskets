"""A simple row-based in-memory table representation library.

This is intended as a simpler, more functional, more predictable to use, less
efficient replacement for something like Pandas for doing relational transforms
on in-memory tables.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from typing import NamedTuple, Tuple, List, Set, Any, Dict, Callable, Union
import typing
import argparse
import csv
import datetime
import logging
import re

# FIXME: Remove this dependency, this is the whole point of this file.
import pandas


# FIXME: Make Row part of the class definition and coerce that all the data uses
# it. Remove other FIXME in select()..



# Main table representation: a list of column names, a list of column types, and
# a list of rows (matching the types).
Header = List[str]
Types = List[object]
Rows = List[List[Any]]
_Table = NamedTuple('Table', [
    ('columns', Header),
    ('types', Types),
    ('rows', Rows)
])
class Table(_Table):

    # FIXME: Idea: generate Row namedtuple type during construction instead of a
    # generic one.

    def __str__(self):
        return format(self)

    def __iter__(self):
        return iter(self.rows)

    def select(self, *args, **kw):
        return select(self, *args, **kw)

    def map(self, *args, **kw):
        return map(self, *args, **kw)

    def filter(self, *args, **kw):
        return filter(self, *args, **kw)


def addrow(cls):
    cls.Row = NamedTuple('Row', cls.field_types)
    return cls

@addrow
class DefTable(Table):
    """A base class to tables with a fixed set of columns."""

    # Override this to define your table type.
    field_types = []

    # Implement this via metaclasses.
    #Row = NamedTuple('Row', field_types)

    def __init__(self, rows):
        columns = []
        types = []
        for column, ftype in self.field_types:
            columns.append(column)
            types.append(ftype)
        table.Table.__init__(self, columns, types, rows)


def format(table: Table):
    """Format the table as aligned ASCII."""
    return pandas.DataFrame(table.rows, columns=table.columns).to_string(index=False)


def read(infile: str) -> Table:
    """Naive CSV reading routine."""
    close = False
    if isinstance(infile, str):
        close = True
        infile = open(infile)
    try:
        reader = csv.reader(infile)
        readit = iter(reader)
        header = next(readit)
        types = [str] * len(header)
        rows = list(readit)
    finally:
        if close:
            infile.close()
    return Table(header, types, rows)


def write(table: Table, outfile: str):
    """Write a table to a CSV file."""
    with outfile:
        writer = csv.writer(outfile)
        writer.writerow(table.columns)
        writer.writerows(table.rows)


def idify(name: str):
    """Coerce string into an identifier."""
    return re.sub('_+', '_', re.sub(r'[^a-zA-Z0-9_]', '_', name))


def select(table: Table, columns: List[Union[str,Tuple[str,Callable]]]) -> Table:
    """Select, transform or create some columns.
    Here the columns may be just strings, or tuples of (new-column-name,
    function) where function operates on every row (like a map).
    """
    new_columns = []
    types = []
    transforms = []
    for column in columns:
        if isinstance(column, str):
            index = table.columns.index(column)
            function = lambda row, i=index: row[i]
            ftype = table.types[index]
        else:
            assert isinstance(column, tuple)
            if len(column) == 2:
                column, function = column
                hints = typing.get_type_hints(function)
                ftype = hints.pop('return', str)
            elif len(column) == 3:
                column, function, ftype = column
        new_columns.append(column)
        types.append(ftype)
        transforms.append(function)

    # FIXME: Make this part of the class metadata.
    Row = NamedTuple('Row', list(zip(map(idify, table.columns), table.types)))

    rows = [[transform(Row(*row)) for transform in transforms]
            for row in table.rows]
    return Table(new_columns, types, rows)


def map(table: Table, columns: List[Union[str,Tuple[str,Callable]]]) -> Table:
    """Like selection, but keeps all the other columns intact.
    Here you may create new columns or transform existing ones.
    """
    for column in columns:


    new_columns = []
    types = []
    transforms = []
    for column in columns:
        if isinstance(column, str):
            index = table.columns.index(column)
            function = lambda row, i=index: row[i]
            ftype = table.types[index]
        else:
            assert isinstance(column, tuple)
            if len(column) == 2:
                column, function = column
                hints = typing.get_type_hints(function)
                ftype = hints.pop('return', str)
            elif len(column) == 3:
                column, function, ftype = column
        new_columns.append(column)
        types.append(ftype)
        transforms.append(function)

    # FIXME: Make this part of the class metadata.
    Row = NamedTuple('Row', list(zip(map(idify, table.columns), table.types)))

    rows = [[transform(Row(*row)) for transform in transforms]
            for row in table.rows]
    return Table(new_columns, types, rows)



def filter(table: Table, predicate: Callable) -> Table:
    """Filter the rows of a table.
    """
    # FIXME: Make this part of the class metadata.
    Row = NamedTuple('Row', list(zip(map(idify, table.columns), table.types)))
    rows = [row for row in table.rows if predicate(Row(*row))]
    return table.__class__(table.columns, table.types, rows)


def join(main_table: Table, *col_tables: Tuple[Tuple[Tuple[str], Table]]) -> Table:
    """Join a table with a number of other tables.
    col_tables is a tuple of (column, table) pairs."""

    new_header = list(main_table.columns)
    new_types = list(main_table.types)
    for cols, col_table in col_tables:
        header = list(col_table.columns)
        types = list(col_table.types)
        for col in cols:
            assert col in main_table.columns
            index = header.index(col)
            del header[index]
            del types[index]
        new_header.extend(header)
        new_types.extend(types)

    col_maps = []
    for cols, col_table in col_tables:
        indexes_main = [main_table.columns.index(col) for col in cols]
        indexes_col = [col_table.columns.index(col) for col in cols]
        #indexes_notcol = sorted(set(range(len(col_table.columns))) - set(indexes_col))
        col_map = {}
        for row in col_table.rows:
            key = tuple(row[index] for index in indexes_col)
            col_map[key] = row
        assert len(col_map) == len(col_table.rows), cols
        col_maps.append((indexes_main, indexes_col, col_map))

    rows = []
    for row in main_table.rows:
        row = list(row)
        empty_row = [None] * (len(col_table.columns) - len(indexes_col))
        for indexes_main, indexes_col, col_map in col_maps:
            key = tuple(row[index] for index in indexes_main)
            other_row = col_map.get(key, None)
            if other_row is not None:
                other_row = list(other_row)
                for index in reversed(indexes_col):
                    del other_row[index]
            else:
                other_row = empty_row
            row.extend(other_row)
        rows.append(row)

    return Table(new_header, new_types, rows)
