   # # Extract tables from each downloaded file.
    # norm_table_map = {}
    # _, __, filenames = next(os.walk(args.output))
    # for filename in sorted(path.join(args.output, f) for f in filenames):
    #     logging.info("Parsing %s", filename)
    #     tbl = vanguard.parse_tables(filename)
    #     norm_table_map[filename] = normalize_holdings_table(tbl)

    # # Compute a sum-product of the tables.
