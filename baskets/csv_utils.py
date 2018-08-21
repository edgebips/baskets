"""Utilities for reading and writing CSV files.
"""
__copyright__ = "Copyright (C) 2018  Martin Blais"
__license__ = "GNU GPLv2"


def csv_split_sections(rows):
    """Given rows, split them in at empty lines.
    This is useful for structured CSV files with multiple sections.

    Args:
      rows: A list of rows, which are themselves lists of strings.
    Returns:
      A list of sections, which are lists of rows, which are lists of strings.
    """
    sections = []
    current_section = []
    for row in rows:
        if row:
            current_section.append(row)
        else:
            sections.append(current_section)
            current_section = []
    if current_section:
        sections.append(current_section)
    return sections


def csv_split_sections_with_titles(rows):
    """Given a list of rows, split their sections. If the sections have single
    column titles, consume those lines as their names and return a mapping of
    section names.

    This is useful for CSV files with multiple sections, where the separator is
    a title. We use this to separate the multiple tables within the CSV files.

    Args:
      rows: A list of rows (list-of-strings).
    Returns:
     A list of lists of rows (list-of-strings).

    """
    sections_map = {}
    for index, section in enumerate(csv_split_sections(rows)):
        # Skip too short sections, cannot possibly be a title.
        if len(section) < 2:
            continue
        if len(section[0]) == 1 and len(section[1]) != 1:
            name = section[0][0]
            section = section[1:]
        else:
            name = 'Section {}'.format(index)
        sections_map[name] = section
    return sections_map
