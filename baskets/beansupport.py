from baskets import table


def AssetsTable(rows):
    """A table describing the list of assets."""
    return table.Table(['ticker', 'issuer', 'quantity'],
                       [str, str, float],
                       rows)


def get_ticker(row) -> str:
    if not row.export:
        return row.currency if row.currency != row.cost_currency else ''
    else:
        exch, _, symbol = row.export.partition(':')
        if not symbol:
            symbol = exch
        return symbol


def safefloat(v: str):
    return float(v) if v else 1.


def read_exported_assets(filename: str) -> table.Table:
    """Load a file in beancount.projects.export format."""
    tbl = (table.read_csv(filename)
           .select(['currency', 'cost_currency', 'export',
                    'number', 'issuer',
                    'price_file', 'rate_file'])
           .map('price_file', safefloat)
           .map('rate_file', safefloat)
           .map('number', float)
           .create('ticker', get_ticker)
           .delete(['export', 'currency'])
           .filter(lambda row: bool(row.ticker))
           .create('price', lambda row: row.price_file * row.rate_file)
           .delete(['price_file', 'rate_file'])
           .group(('ticker', 'issuer', 'price'), 'number', sum)
           .order(lambda row: (row.ticker, row.issuer, row.price))
           .checkall(['ticker', 'issuer', 'price', 'number']))
    return tbl
