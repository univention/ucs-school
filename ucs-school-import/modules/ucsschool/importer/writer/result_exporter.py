#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for result exporters."""

import os.path
import stat

from ucsschool.lib.models.utils import mkdir_p


class ResultExporter(object):
    """
    Write a CSV/JSON/XML file representing the result of an import job.
    Create one writer per object type.

    Clients of this class should only call dump().

    Subclasses implement get_iter() to create a stream of objects to serialize
    and run serialize() on each of them.
    """

    def __init__(self, *arg, **kwargs):
        """
        Create a CSV file writer.

        :param list arg: arguments for implementing class
        :param dict kwargs: arguments for implementing class
        """

    def dump(self, import_handler, filename):
        """
        Create file about added/modified/deleted objects and errors.

        :param UserImport import_handler: object that contains data to dump from an import job (for
            example UserImport)
        :param str filename: filename to write data to
        """
        mkdir_p(os.path.dirname(filename), "root", "root", stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        writer = self.get_writer()
        with writer.open(filename):
            writer.write_header(self.get_header())
            for obj in self.get_iter(import_handler):
                row = self.serialize(obj)
                writer.write_obj(row)
            writer.write_footer(self.get_footer())

    def get_footer(self):
        """
        Data for an optional footer (line) after the main data.
        IMPLEMENTME if you wish to write a footer.

        :return: object that can be used by the writer to create a footer
        """

    def get_header(self):
        """
        Data for an optional header (line) before the main data.
        IMPLEMENTME if you wish to write a header line.

        :return: object that can be used by the writer to create a header
        """

    def get_iter(self, import_handler):
        """
        Iterator over all created objects and errors of an import job.
        IMPLEMENTME to change the order of objects and errors in the generated
        output.

        :param import_handler: object that contains data to dump from an import job
        :return: iterator for both import objects and UcsSchoolImportError objects
        :rtype: Iterator
        """
        raise NotImplementedError()

    def get_writer(self):
        """
        Object that will write the data to disk/network in the desired format.
        IMPLEMENTME

        :return: an object of a BaseWriter subclass
        :rtype: BaseWriter
        """
        raise NotImplementedError()

    def serialize(self, obj):
        """
        Make a dict of attr_name->strings from an import object.
        IMPLEMENTME to dump a single object (user/computer/error) delivered by
        the iterator from get_iter().

        :param obj: object to serialize
        :return: attr_name->strings that will be used to write the output file
        :rtype: dict
        """
        raise NotImplementedError()
