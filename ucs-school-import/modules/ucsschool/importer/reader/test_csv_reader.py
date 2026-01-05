#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""CSV reader for CSV files created by TestUserCsvExporter."""

from ..configuration import Configuration
from ..reader.csv_reader import CsvReader


class TestCsvReader(CsvReader):
    """
    This class has been deprecated. Please use "CsvReader" instead. It now
    also handles a "__role" column (replace "__type" in the mapping
    configuration with "__role").
    """

    _role_method = CsvReader.get_roles_from_csv
    _csv_roles_value = "__type"

    def __init__(self):
        # __init__() cannot have arguments, as it has replaced
        # DefaultUserImportFactory.make_reader() and is instantiated from
        # UserImport.__init__() without arguments.
        # So we'll fetch the necessary information from the configuration.
        self.config = Configuration()
        filename = self.config["input"]["filename"]
        header_lines = self.config["csv"]["header_lines"]
        super(TestCsvReader, self).__init__(filename, header_lines)
        self.logger.warning(
            'The "TestCsvReader" class has been deprecated. Please use "CsvReader" and use "__role" '
            'instead of "__type" in the mapping configuration.'
        )
