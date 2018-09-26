"""Group assets by similarity.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

import collections
import logging
import re
import math
from typing import Tuple

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
    """Print a list of rows."""
    for row in rows:
        print(row, file=outfile)
    for link in links:
        print(link, file=outfile)
    print(file=outfile)


def print_detailed_debug_info(component, graph):
    """Print some detailed debug information."""
    for c in component:
        # pylint: disable=unidiomatic-typecheck
        if type(c) is not tuple:
            print(c)
            for e in graph.edges(c):
                print(e[1])
            print()
    print()
    print()
    print()


def build_graph(holdings: Table) -> nx.Graph:
    """Build a graph of relationships using the identifier columns and name."""
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
    return g


def group(holdings: Table, debug_filename: str = None) -> Tuple[Table, Table]:
    """Group assets by similarity."""

    # Compute the connected components.
    g = build_graph(holdings)
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
            # pylint: disable=unidiomatic-typecheck
            (links if type(c) is tuple else rows).append(c)
        counts[len(rows)] += 1
        groups.append(rows)

        # Print all groups to a test file.
        if debugfile:
            print_group(rows, links, debugfile)

        # if ('ticker', 'GOOG') in links or ('ticker', 'GOOGL') in links:
        #     print_detailed_debug_info(c, g)

        # if 0:
        #     # Print groups with mixed asset types.
        #     if len(set(row.asstype for row in rows)) > 1:
        #         print_group(rows, links)

        # if 0:
        #     # Print groups without any ticker.
        #     if len(rows) != 1:
        #         continue
        #     linkdict = dict(links)
        #     if linkdict.get('ticker', None):
        #         continue
        #     print_group(rows, links)

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
        # Select the longest name. It seems to nealy always be the best variant.
        names = sorted(set(row.name for row in rows), key=len, reverse=True)
        name = names[0]
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


def group_sectors(holdings: Table) -> Tuple[Table]:
    """Group assets by sectors."""


    # Fix up some of the sector names manually.
    fholdings = holdings.map('sector', fix_sectors)
    # sectors = (fholdings
    #            .group('sector', 'amount', sum)
    #            .map('amount', lambda a: '{:,.0f}'.format(a)))
    # print(sectors)

    # # Compute the list of unique sectors.
    # sectors = collections.defaultdict(int)
    # for sector in fulltable.values('sector'):
    #     sectors[sector] += 1
    # from pprint import pprint
    # pprint(sectors)

    g = build_graph(fholdings)

    sectors = set()
    for row in fholdings:
        if not row.sector:
            continue
        sector = ('sector', row.sector)
        g.add_edge(row, sector)
        sectors.add(sector)

    cc = list(nx.connected_components(g))
    print("Num components: {}".format(len(cc)))

    sectors = []
    unknown_amount = 0
    unknown_rows = []
    for component in cc:
        csectors = set()
        amount = 0
        rows = []
        for c in component:
            if type(c) is tuple:
                if c[0] == 'sector':
                    csectors.add(c[1])
            else:
                amount += c.amount
                rows.append(c)
        if csectors:
            sectors.append((','.join(csectors), rows, amount))
        else:
            unknown_amount += amount
            unknown_rows.extend(rows)
    sectors.append(('', unknown_rows, unknown_amount))

    for sector, rows, amount in sorted(sectors):
        print('* {:32} : {:12,.0f}'.format(sector, amount))
        fields = rows[0]._fields
        tbl = Table(fields, [str] * len(fields), rows)
        print(tbl)
        print()





def fix_sectors(sector):
    return _SECTOR_MAP.get(sector, sector)

_SECTOR_MAP = {
    'Banking': 'Financials',
    'Finance Companies': 'Financials',
    'Financial Other': 'Financials',
    'Brokerage/Asset Managers/Exchanges': 'Financials',
    'Health': 'Health Care',
    'Utility Other': 'Utilities',
    'Utility': 'Utilities',
    'Telecommunication Services': 'Telecommunications',
    'Reits': 'Real Estate',
    'Basic Industry': 'Industrials',
    'Owned No Guarantee': 'Energy',
}
