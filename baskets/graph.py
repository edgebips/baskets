"""Group assets by similarity.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import collections
import logging
import re
import math
from typing import List, Tuple

import networkx as nx

from baskets.table import Table


def name_key(name: str):
    """Normalize the company name for most accurate match against name database.
    We want to be able to use the name as a key."""
    name = name.lower()
    name = re.sub(r'\d{1,2}/\d{1,2}/\d{1,4}', 'replaced_expiration_date', name)
    name = re.sub(r'\b(ltd|inc|co|corp|plc|llc|sa|adr|non-voting|preferred)\b', '', name)
    name = re.sub(r'[^a-z0-9]', ' ', name)
    name = re.sub(r' +', ' ', name).strip()
    #name = tuple(sorted(name.split()))
    return name


def print_group(rows, links, outfile=None):
    for row in rows:
        print(row, file=outfile)
    for link in links:
        print(link, file=outfile)
    print(file=outfile)


def group(holdings: Table, debug_filename: str=None) -> Tuple[Table, Table]:
    """Group assets by similarity."""

    columns = ['ticker', 'cusip', 'isin', 'sedol']
    g = nx.Graph()
    for row in holdings:
        # Add each row.
        g.add_node(row)

        # Add links for each identifier column.
        for column in columns:
            value = getattr(row, column)
            if value and value != '-':
                g.add_edge(row, (column, value))

        # Link via a normalized version of the name but only if they are the
        # same asset type.
        if row.name and row.name != '-':
            key = name_key(row.name)
            if key:
                g.add_edge(row, ('name_key', (row.asstype, key)))

    # Compute the connected components.
    cc = nx.connected_components(g)
    logging.info('Num connected components: %s', nx.number_connected_components(g))

    # Process each component.
    counts = collections.defaultdict(int)
    debugfile = open(debug_filename, 'w') if debug_filename else None
    groups = []
    for component in cc:
        # Separate out the rows and links.
        rows = []
        links = []
        for c in component:
            (links if type(c) is tuple else rows).append(c)
        counts[len(rows)] += 1
        groups.append(rows)

        # Print all groups to a test file.
        if debugfile:
            print_group(rows, links, debugfile)

        if 0:
            # Print groups with mixed asset types.
            if len(set(row.asstype for row in rows)) > 1:
                print_group(rows, links)

        if 0:
            # Print groups without any ticker.
            if len(rows) != 1:
                continue
            linkdict = dict(links)
            if linkdict.get('ticker', None):
                continue
            print_group(rows, links)

    if debugfile is not None:
        debugfile.close()
    logging.info('Matched: {:%}'.format(1 - counts[1] / sum(counts.values())))
    logging.info('Items distribution (log-floored):')
    # Convert to log map.
    logcounts = collections.defaultdict(int)
    for numitems, count in sorted(counts.items()):
        lognumitems = int(math.pow(2, int(math.log2(numitems))))
        logcounts[lognumitems] += count
    for numitems, count in sorted(logcounts.items()):
        logging.info('   {:>3}~{:>3} items: {:10}'.format(numitems-1, numitems, count))

    # Reduce the rows and produce an aggregated table.
    aggrows = []
    sorted_groups = sorted(groups, key=lambda grows: -sum(row.amount for row in grows))
    for rows in sorted_groups:
        assert rows
        amount = sum(row.amount for row in rows)
        name = rows[0].name
        symbol = ','.join(sorted(set(row.ticker for row in rows if row.ticker)))
        asstype = ','.join(sorted(set(row.asstype for row in rows)))
        aggrows.append((symbol, asstype, name, amount))
    columns = ['symbol', 'asstype', 'name', 'amount']
    aggtable = (Table(columns, [str, str, str, float], aggrows)
                .order(lambda row: row.amount, asc=False))

    # Reproduce the original table, but with the row groups annotated this time.
    annotation_map = {}
    for index, rows in enumerate(sorted_groups):
        for row in rows:
            annotation_map[row] = index
    annotable = (holdings.create('group', annotation_map.__getitem__)
                 .order(lambda row: (row.group, -row.amount)))
    assert len(holdings) == len(annotable)

    return aggtable, annotable
