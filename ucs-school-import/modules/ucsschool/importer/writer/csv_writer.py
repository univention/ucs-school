#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Write the result of a user import job to a CSV file."""

import os
from csv import QUOTE_ALL, DictWriter, excel
from stat import S_IRUSR, S_IWUSR

from .base_writer import BaseWriter


class CsvWriter(BaseWriter):
    def __init__(self, field_names, dialect=None):
        """
        Create a CSV file writer.

        :param field_names: names of the columns
        :type field_names: list(str)
        :param csv.Dialect dialect: If unset will try to detect dialect of input file or fall back to
            "excel".
        """
        super(CsvWriter, self).__init__()
        self.field_names = field_names
        self.dialect = dialect

        if not self.dialect:
            self.dialect = excel()
            self.dialect.doublequote = True
            self.dialect.quoting = QUOTE_ALL

        self.writer = None

    def open(self, filename, mode="w"):
        """
        Open the output file.

        :param str filename: filename to write data to
        :param str mode: passed to builtin :py:func:`open()` method
        :return: DictWriter instance
        :rtype: csv.DictWriter
        """
        with open(filename, mode) as fd:
            os.fchmod(fd.fileno(), S_IRUSR | S_IWUSR)
        fp = open(filename, mode)
        self.writer = DictWriter(fp, fieldnames=self.field_names, dialect=self.dialect)
        return fp

    def write_header(self, header):
        """
        Write a header line before the main data.

        :param header: object to write as header (ignored)
        :return: None
        """
        self.writer.writeheader()

    def write_obj(self, obj):
        """
        Write object to output.

        :param dict obj: data to write
        :return: None
        """
        return self.writer.writerow(obj)
