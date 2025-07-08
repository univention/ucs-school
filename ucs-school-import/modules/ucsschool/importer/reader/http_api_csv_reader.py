#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2017-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""CSV reader for CSV files created for HTTP-API import."""

from ucsschool.lib.models.user import Staff

from ..configuration import Configuration
from .csv_reader import CsvReader


class HttpApiCsvReader(CsvReader):
    def __init__(self, *args, **kwargs):
        # __init__() cannot have arguments, as it has replaced
        # DefaultUserImportFactory.make_reader() and is instantiated from
        # UserImport.__init__() without arguments.
        # So we'll fetch the necessary information from the configuration.
        self.config = Configuration()
        self.school = self.config["school"]
        filename = self.config["input"]["filename"]
        header_lines = self.config["csv"]["header_lines"]
        super(HttpApiCsvReader, self).__init__(filename, header_lines)

    def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
        """Handle class names (prepend school name to class names)."""
        if mapping_value == "school_classes":
            if not isinstance(import_user, Staff):  # ignore column if user is staff
                import_user.school_classes = {
                    self.school: [
                        "{}-{}".format(self.school, sc.strip())
                        for sc in csv_value.split(",")
                        if sc.strip()
                    ]
                }
            return True
        return super(HttpApiCsvReader, self).handle_input(
            mapping_key, mapping_value, csv_value, import_user
        )
