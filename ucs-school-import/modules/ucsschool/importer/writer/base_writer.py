#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for output writers."""


class BaseWriter(object):
    """Abstraction of a data dump mechanism like CSV, JSON, XML, sockets etc."""

    def __init__(self, *arg, **kwargs):
        """
        Create a writer.

        :param tuple arg: arguments for implementing class
        :param dict kwargs: arguments for implementing class
        """

    def open(self, filename, mode="wb"):
        """
        Get a handle on the output file or something similar to be used as a
        context manager.
        IMPLEMENTME with the method appropriate for the output type.

        :param str filename: filename to write data to
        :param str mode: passed to used open() method
        :return: a context manager
        """
        raise NotImplementedError()

    def write_header(self, header):
        """
        Write an optional header (line) before the main data.
        IMPLEMENTME if you wish to write a header line.

        :param header: object to write as header
        :return: None
        """

    def write_footer(self, footer):
        """
        Write a optional footer (line) after the main data.
        IMPLEMENTME if you wish to write a footer.

        :param footer: object to write as footer
        :return: None
        """

    def write_obj(self, obj):
        """
        Write object to output.
        IMPLEMENTME if it's not just outfile.write(obj).

        :param obj: object or error to write
        :return: result of write operation, if any
        """
        raise NotImplementedError()
