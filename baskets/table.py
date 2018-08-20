"""A simple row-based in-memory table representation and manipulation library.

Think of this as a simpler, more functional, more predictable to use, much less
efficient replacement for something like the Pandas DatFrame class, for doing
relational transforms on in-memory tables. It doesn't optimize nor table
advantage of columnar representation. The intent is to provide an easier-to-use
API for small data tables (e.g. 100's or 1000's of rows).

Usage:

The module provides a "Table" object which has columns and types, and a list of
rows. A "Row" subtype is provided to represent each row and make conveniently
accessing its contents as attributes. A DefTable subtype is provided if you want
to predefine and fix the schema of a table.

Column Ops: You can perform some operations on the columns of a table:

- select: You can select a subset of columns.
- create: You can create new columns, as a function of each row.
- update: You can map the values of a column to a new set of values.
- delete: You can delete columms.
- get: You can get a list of all the values in a column.
- array: You can get a NumPy array of the values in a column (e.g., for plotting).
- coltype: You can get the type of a column by name.
- index: You can create an index of the rows from the unique values in a column.

Row Ops: You can perform some operations on the rows of a table:

- iterate: You can iterate over the rows.
- filter: You can remove rows by filtering them.
- group: You can perform aggregations of the rows.
- pivot: You can pivot on two columns and aggregate the values in each cell.
- append: You can append new rows (suggest only doing this once to build up).

Table Ops: You can perform some operations on a table:

- format: It can be formatted to a string (for human consumption).
- join: You can join two tables on a condition (e.g. same column).
- read_csv: You can read a table from a CSV file.
- write_csv: You can write a table to a CSV file.
- check: You can assert the existence of columns and/or types of a table.

This summarizes the entire interface and all this functionality is implemented
in this one file. The operations can be invoked as function and most of them are
also available as methods of the Table object; note however, that except for the
appned() method, none of them mutate the contents of a table. In some cases a
full copy of the table is returned. (Yes, this is wasteful, but the purpose of
this API not efficiency but rather ease of use.)
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from keyword import iskeyword
from typing import NamedTuple, Tuple, List, Set, Any, Dict, Callable, Union
import argparse
import collections
import csv
import datetime
import io
import itertools
import logging
import re
import typing

# FIXME: Remove this dependency, this is the whole point of this file.
import pandas

# FIXME: Maybe rename Table -> Schema and DefTable -> Table? How do you link a
# Table and its schema? Composition?

# FIXME: Implement automatic type inference.

Header = List[str]
Types = List[type]
Rows = List[List[Any]]
_Table = NamedTuple('_Table', [
    ('columns', Header),
    ('types', Types),
    ('rows', Rows),
    ('Row', tuple),
])

# FIXME: Idea: Should we make a table a subclass of 'list' and provide a factory
# of types instead?

class Table(_Table):
    """Table representation: a list of column names, a list of column types,
     and list of rows (matching the types)."""

    def __new__(cls, columns, types, rows):
        clean_columns = list(itertools.starmap(idify, enumerate(columns)))
        Row = collections.namedtuple('Row', clean_columns)
        assert len(columns) == len(types)
        if not isinstance(rows[0], Row):
            rows = list(map(Row._make, rows))
        return _Table.__new__(cls, clean_columns, types, rows, Row)

    def __str__(self):
        return format(self)

    def __len__(self):
        return len(self.rows)

    # Column operations.
    def select(self, *args, **kw):   return select(self, *args, **kw)
    def create(self, *args, **kw):   return create(self, *args, **kw)
    def update(self, *args, **kw):   return update(self, *args, **kw)
    def map(self, *args, **kw):      return map_(self, *args, **kw)
    def delete(self, *args, **kw):   return delete(self, *args, **kw)
    def values(self, *args, **kw):   return values(self, *args, **kw)
    def array(self, *args, **kw):    return array(self, *args, **kw)
    def coltype(self, *args, **kw):  return coltype(self, *args, **kw)
    def index(self, *args, **kw):    return index(self, *args, **kw)
    def rename(self, *args, **kw):   return rename(self, *args, **kw)

    # Row operations.
    def iterate(self):               return iterate(self)
    def __iter__(self):              return iterate(self)
    def filter(self, *args, **kw):   return filter(self, *args, **kw)
    def group(self, *args, **kw):    return group(self, *args, **kw)
    def order(self, *args, **kw):    return order(self, *args, **kw)
    def pivot(self, *args, **kw):    return pivot(self, *args, **kw)
    def append(self, *args, **kw):   return append(self, *args, **kw)

    # Table operations.
    def format(self, *args, **kw):   return format(self, *args, **kw)
    def head(self, *args, **kw):     return head(self, *args, **kw)
    def concat(self, *args, **kw):   return concat(self, *args, **kw)
    def join(self, *args, **kw):     return join(self, *args, **kw)
    def check(self, *args, **kw):    return check(self, *args, **kw)
    def checkall(self, *args, **kw): return checkall(self, *args, **kw)

    # @property
    # def Row(self):
    #     """Get the row tuple type."""
    #     _Row = self._Row
    #     if _Row is None:
    #         _Row = NamedTuple('Row', cls.field_types)
    #         self._Row = _Row
    #     return _Row


# class DefTable(Table):
#     """A base class to tables with a fixed set of columns."""

#     # Override this to define your table type.
#     field_types = []

#     def __new__(cls, rows):
#         columns = [column for column, _ in self.field_types]
#         types = [type_ for _, type_ in self.field_types]
#         Table.__new__(self, columns, types, rows)


def idify(index: int, name: str):
    """Coerce string into an identifier. For columns."""
    if not name:
        return 'col{:02d}'.format(index)
    if '%' in name:
        name = name.replace('%', 'pct')
    name = re.sub('_+', '_', re.sub(r'[^a-zA-Z0-9_]', '_', name)).strip('_')
    if iskeyword(name):
        name = name + '_'
    return name.lower()


def select(table: Table, columns: List[str]) -> Table:
    """Select, transform or create some columns.
    Here the columns may be just strings, or tuples of (new-column-name,
    function) where function operates on every row (like a map).
    """
    indexes = [table.columns.index(column)
               for column in columns]
    rows = [[row[index] for index in indexes]
            for row in table.rows]
    types = [table.types[index] for index in indexes]
    return Table(columns, types, rows)


def create(table: Table, column: str, newfunc: Callable) -> Table:
    """Insert a new column."""
    columns = table.columns + [column]

    hints = typing.get_type_hints(newfunc)
    types = list(table.types)
    types.append(hints.get('return', str))

    rows = [row + (newfunc(row),)
            for row in table.rows]

    return Table(columns, types, rows)



def update(table: Table, column: str, mapfunc: Callable) -> Table:
    """Replace the contents of a column via a mapper on a row."""
    index = table.columns.index(column)
    hints = typing.get_type_hints(mapfunc)
    new_types = list(table.types)
    new_types[index] = hints.get('return', str)
    new_rows = []
    for row in table.rows:
        kw = {column: mapfunc(row)}
        new_rows.append(row._replace(**kw))
    return Table(table.columns, new_types, new_rows)


def map_(table: Table, column: str, mapfunc: Callable) -> Table:
    """Replace the contents of a column via a mapper on the column."""
    return update(table, column, lambda row: mapfunc(getattr(row, column)))


def delete(table: Table, columns: List[str]) -> Table:
    """Delete one or more columns."""
    indexes = [index
               for index, column in enumerate(table.columns)
               if column not in columns]
    columns = [table.columns[index] for index in indexes]
    types = [table.types[index] for index in indexes]
    return Table(columns, types,
                 [[row[index] for index in indexes]
                  for row in table.rows])


def values(table: Table, column: str):
    """Get a column's list of values."""
    index = table.columns.index(column)
    return [row[index] for row in table.rows]


def array(*args, **kw): raise NotImplementedError
def coltype(*args, **kw): raise NotImplementedError
def index(*args, **kw): raise NotImplementedError


def rename(table: Table, *namepairs: Tuple[Tuple[str]]) -> Table:
    """Rename a column."""
    columns = list(table.columns)
    for oldname, newname in namepairs:
        index = table.columns.index(oldname)
        columns[index] = newname
    return Table(columns, table.types, table.rows)


def iterate(table: Table):
    """Return an iterator on the rows."""
    return iter(table.rows)


def filter(table: Table, predicate: Callable) -> Table:
    """Filter the rows of a table."""
    rows = [row for row in table.rows if predicate(row)]
    return table.__class__(table.columns, table.types, rows)


def _get_group_column(table: Table, key: Union[Callable,str]):
    if isinstance(key, str):
        key = (key,)
    elif isinstance(key, Callable):
        key = (key,)
    else:
        assert isinstance(key, tuple)
    names = []
    types = []
    funcs = []
    for part in key:
        if isinstance(part, str):
            func = lambda row, k=part: getattr(row, k)
            type = table.types[table.columns.index(part)]
            name = part
        else:
            assert isinstance(part, Callable)
            func = part
            hints = typing.get_type_hints(func)
            type = hints.get('return', str)
            name = func.__name__
        names.append(name)
        types.append(type)
        funcs.append(func)
    return names, types, funcs


def group(table: Table,
          key: Union[Callable,str],
          value: [Callable,str],
          aggfunc: Callable):
    """Group the rows of a table."""
    keynames, keytypes, keyfuncs = _get_group_column(table, key)
    valuenames, valuetypes, valuefuncs = _get_group_column(table, value)
    aggregates = collections.defaultdict(list)
    for row in table.rows:
        key = tuple(func(row) for func in keyfuncs)
        values = tuple(func(row) for func in valuefuncs)
        aggregates[key].append(values)

    columns = keynames + valuenames
    types = keytypes + valuetypes
    rows = []
    for key, valuetuples in aggregates.items():
        valuelists = list(zip(*valuetuples))
        for valuelist in valuelists:
            value = aggfunc(valuelist)
            rows.append(key + (value,))

    return Table(columns, types,  rows)


def order(table: Table, key: Union[str,Callable], asc: bool = True) -> Table:
    """Reorder the rows of a table."""
    if isinstance(key, str):
        index = table.columns.index(key)
        key = lambda row, i=index: row[i]
    return Table(table.columns, table.types,
                 sorted(table.rows, key=key, reverse=(not asc)))


def pivot(*args, **kw):    raise NotImplementedError
def append(*args, **kw):   raise NotImplementedError


def format(table: Table):
    """Format the table as aligned ASCII."""
    return pandas.DataFrame(table.rows, columns=table.columns).to_string(index=False)


def head(table: Table, num: int = 8):
    """Return the first 'num' rows of the table."""
    return Table(table.columns, table.types, table.rows[:num])


def concat(*tables: Tuple[Table]):
    """Return the first 'num' rows of the table."""
    table1 = tables[0]
    rows = list(table1.rows)
    for table2 in tables[1:]:
        assert table2.columns == table1.columns
        assert table2.types == table1.types
        rows.extend(table2.rows)
    return Table(table1.columns, table1.types, rows)


def join(*args, **kw):     raise NotImplementedError


def check(table: Table, columns: List[str]):
    """Assert the existence of some columns."""
    for column in columns:
        assert column in table.columns
    return table


def checkall(table: Table, columns: List[str]):
    """Assert the existence of some columns."""
    if columns != table.columns:
        raise AssertionError("Differing columns: {} != {}".format(table.columns, columns))
    return table


##def leftjoin(main_table: Table, *col_tables: Tuple[Tuple[Tuple[str], Table]]) -> Table:
##    """Join a table with a number of other tables.
##    col_tables is a tuple of (column, table) pairs."""
##
##    new_header = list(main_table.columns)
##    new_types = list(main_table.types)
##    for cols, col_table in col_tables:
##        header = list(col_table.columns)
##        types = list(col_table.types)
##        for col in cols:
##            assert col in main_table.columns
##            index = header.index(col)
##            del header[index]
##            del types[index]
##        new_header.extend(header)
##        new_types.extend(types)
##
##    col_maps = []
##    for cols, col_table in col_tables:
##        indexes_main = [main_table.columns.index(col) for col in cols]
##        indexes_col = [col_table.columns.index(col) for col in cols]
##        #indexes_notcol = sorted(set(range(len(col_table.columns))) - set(indexes_col))
##        col_map = {}
##        for row in col_table.rows:
##            key = tuple(row[index] for index in indexes_col)
##            col_map[key] = row
##        assert len(col_map) == len(col_table.rows), cols
##        col_maps.append((indexes_main, indexes_col, col_map))
##
##    rows = []
##    for row in main_table.rows:
##        row = list(row)
##        empty_row = [None] * (len(col_table.columns) - len(indexes_col))
##        for indexes_main, indexes_col, col_map in col_maps:
##            key = tuple(row[index] for index in indexes_main)
##            other_row = col_map.get(key, None)
##            if other_row is not None:
##                other_row = list(other_row)
##                for index in reversed(indexes_col):
##                    del other_row[index]
##            else:
##                other_row = empty_row
##            row.extend(other_row)
##        rows.append(row)
##
##    return Table(new_header, new_types, rows)


def read_csv(infile: Union[str,io.TextIOBase]) -> Table:
    """Read from a CSV file."""
    close = False
    if isinstance(infile, str):
        close = True
        infile = open(infile)
    try:
        reader = csv.reader(infile)
        readit = iter(reader)

        # Skip empty lines at the beginning.
        header = None
        while not header:
            header = next(readit)

        types = [str] * len(header)
        rows = list(readit)
    finally:
        if close:
            infile.close()
    return Table(header, types, rows)


def write_csv(table: Table, outfile: str):
    """Write a table to a CSV file."""
    with outfile:
        writer = csv.writer(outfile)
        writer.writerow(table.columns)
        writer.writerows(table.rows)


# FIXME: Powerful select() variant which can create new columns.
##def select(table: Table, columns: List[Union[str,Tuple[str,Callable]]]) -> Table:
##    """Select, transform or create some columns.
##    Here the columns may be just strings, or tuples of (new-column-name,
##    function) where function operates on every row (like a map).
##    """
##    new_columns = []
##    types = []
##    transforms = []
##    for column in columns:
##        if isinstance(column, str):
##            index = table.columns.index(column)
##            function = lambda row, i=index: row[i]
##            ftype = table.types[index]
##        else:
##            assert isinstance(column, tuple)
##            if len(column) == 2:
##                column, function = column
##                hints = typing.get_type_hints(function)
##                ftype = hints.pop('return', str)
##            elif len(column) == 3:
##                column, function, ftype = column
##        new_columns.append(column)
##        types.append(ftype)
##        transforms.append(function)
##
##    # FIXME: Make this part of the class metadata.
##    Row = NamedTuple('Row', list(zip(map(idify, table.columns), table.types)))
##
##    rows = [[transform(Row(*row)) for transform in transforms]
##            for row in table.rows]
##    return Table(new_columns, types, rows)
