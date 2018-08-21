"""Group assets by similarity.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import collections
import logging
import re

import networkx as nx

from baskets.table import Table


def name_key(name: str):
    """Normalize the company name for most accurate match against name database.
    We want to be able to use the name as a key."""
    name = name.lower()
    name = re.sub(r'\d{1,2}/\d{1,2}/\d{1,4}', 'replaced_expiration_date', name)
    name = re.sub(r'\b(ltd|inc|co|corp|plc|llc|sa|adr|non-voting|preferred|class [A-F])\b', '', name)
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


def group(holdings: Table) -> Table:
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
    logging.info('Num connedted components: %s', nx.number_connected_components(g))

    # Process each component.
    counts = collections.defaultdict(int)
    allfile = None # open('/tmp/allgroups.txt', 'w')
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
        if allfile:
            print_group(rows, links, allfile)

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

    if allfile is not None:
        allfile.close()
    logging.info('Matched: {:%}'.format(1 - counts[1] / sum(counts.values())))
    logging.info('Items distribution: %s', sorted(counts.items()))

    # Reduce the rows
    aggrows = []
    for rows in groups:
        assert rows
        if 0:
            for row in rows:
                print(row)
            print()

        amount = sum(row.amount for row in rows)
        name = rows[0].name
        symbol = ','.join(sorted(set(row.ticker for row in rows if row.ticker)))
        asstype = ','.join(sorted(set(row.asstype for row in rows)))
        aggrows.append((symbol, asstype, name, amount))
    columns = ['symbol', 'asstype', 'name', 'amount']
    aggtable = (Table(columns, [str, str, str, float], aggrows)
                .order(lambda row: row.amount, asc=False))
    return aggtable
