from baskets import table


def AssetsTable(rows):
    """A table describing the list of assets."""
    return table.Table(['ticker', 'issuer', 'quantity'],
                       [str, str, float],
                       rows)


def read_exported_assets(filename: str) -> table.Table:
    """Load a file in beancount.projects.export format."""
    tbl = table.read_csv(filename)
    tbl = tbl.select(['export', 'number', 'cost_currency', 'issuer'])
    def clean_ticker(export) -> str:
        exch, _, symbol = export.partition(':')
        if not symbol:
            symbol = exch
        return symbol
    tbl = (tbl
           .map('number', float)
           .map('export', clean_ticker)
           .filter(lambda row: bool(row.export))
           .filter(lambda row: bool(row.issuer))
           .group(('export', 'issuer'), 'number', sum)
           .order(lambda row: (row.issuer, row.export))
           .rename('export', 'ticker'))
    return tbl
