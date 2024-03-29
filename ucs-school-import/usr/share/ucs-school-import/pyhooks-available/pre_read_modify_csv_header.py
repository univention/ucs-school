#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2019-2024 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

"""
A pre-read hooks that changes the header of a input CSV file.

A mapping is read from the configuration file (csv:header_swap), the original
CSV file is backuped and the header is changed.

If a mapping key is not found in the input file, it is ignored.

Example::
    {
        "csv": {
            "header_swap": {
                "Schulen Ost": "Schulen",
                "Schulname": "Schulen",
                "Familienname": "Nachname"
            }
        }
    }
    header 1 before: "ID","Vorname","Nachname","Email","Schulen Ost"
    header 1 after : "ID","Vorname","Nachname","Email","Schulen"
    header 2 before: "ID","Familienname,"Vorname","Schulname"
    header 2 after : "ID","Nachname,"Vorname","Schulen"
"""

import codecs
import csv
import datetime
import io
import shutil

from six import PY3

from ucsschool.importer.exceptions import ConfigurationError
from ucsschool.importer.reader.csv_reader import CsvReader
from ucsschool.importer.utils.pre_read_pyhook import PreReadPyHook


def py3_decode(data, encoding):
    return data.decode(encoding) if PY3 and isinstance(data, bytes) else data


def py2_encode(data, encoder):
    return data if PY3 else encoder.encode(data)


class ModifyCsvHeader(PreReadPyHook):
    """
    Hook is called before starting to read the input file to change the header
    of the CSV input file.
    """

    priority = {
        "pre_read": 1000,
    }

    def pre_read(self):  # type: () -> None
        """
        * get mapping from the configuration file (csv:header_swap)
        * backup original CSV file to {input:filename}.$date.bak.csv
        * rewrite original CSV file with new header, trying to keep encoding
        and CSV dialect

        :return: None
        """
        header_swap = self.config["csv"].get("header_swap")
        if not header_swap:
            raise ConfigurationError("Missing configuration in csv:header_swap.")

        # make backup of original file
        ori_file_name = self.config["input"]["filename"]
        _fn = ori_file_name[:-4] if ori_file_name.endswith(".csv") else ori_file_name
        backup_file_name = "{}.ori.{:%Y-%m-%d_%H:%M:%S}.csv".format(_fn, datetime.datetime.now())
        self.logger.info("Copying %r to %r...", ori_file_name, backup_file_name)
        shutil.copy2(ori_file_name, backup_file_name)

        # get encoding and CSV dialect
        encoding = CsvReader.get_encoding(backup_file_name)
        with open(backup_file_name, "rb") as fp:
            dialect = csv.Sniffer().sniff(py3_decode(fp.read(), encoding))

        # rewrite CSV with different headers
        self.logger.info("Rewriting %r...", ori_file_name)
        with open(backup_file_name, "rb") as fpr, io.open(ori_file_name, "w", encoding=encoding) as fpw:
            fpre = codecs.getreader(encoding)(fpr)
            encoder = codecs.getincrementalencoder(encoding)()
            writer = csv.writer(fpw, dialect=dialect)
            header_swapped = False
            for row in csv.reader(fpre, dialect=dialect):
                if not header_swapped:
                    header_swapped = True
                    self.logger.info("Original header: %r", row)
                    row = [header_swap.get(value, value) for value in row]
                    self.logger.info("New header:      %r", row)
                writer.writerow([py2_encode(r, encoder) for r in row])
        self.logger.info("Done rewriting CSV file.")
