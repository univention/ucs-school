#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class of all input readers."""

import logging
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, List, Optional, Text  # noqa: F401

from ..configuration import Configuration
from ..exceptions import UcsSchoolImportSkipImportRecord
from ..factory import Factory
from ..utils.import_pyhook import run_import_pyhooks
from ..utils.ldap_connection import get_admin_connection, get_readonly_connection
from ..utils.post_read_pyhook import PostReadPyHook

if TYPE_CHECKING:
    from ..models.import_user import ImportUser  # noqa: F401


class BaseReader(object):
    """
    Base class of all input readers.

    Subclasses must override get_roles(), map() and read().
    """

    def __init__(self, filename, header_lines=0, **kwargs):  # type: (str, Optional[int], **Any) -> None
        """
        :param str filename: Path to file with user data.
        :param int header_lines: Number of lines before the actual data starts.
        :param dict kwargs: optional parameters for use in derived classes
        """
        self.config = Configuration()
        self.logger = logging.getLogger(__name__)
        self.lo, self.position = (
            get_readonly_connection() if self.config["dry_run"] else get_admin_connection()
        )
        self.filename = filename
        self.header_lines = header_lines
        self.import_users = self.read()
        self.factory = Factory()
        self.ucr = self.factory.make_ucr()
        self.entry_count = 0  # line/node in input data
        self.input_data = None  # input data, as raw as possible/sensible

    def __iter__(self):  # type: () -> BaseReader
        return self

    def __next__(self):  # type: () -> ImportUser
        """
        Generates ImportUsers from input data.

        :return: ImportUser
        :rtype: ImportUser
        """
        while True:
            input_dict = next(self.import_users)
            self.logger.debug("Input %d: %r -> %r", self.entry_count, self.input_data, input_dict)
            try:
                run_import_pyhooks(
                    PostReadPyHook, "entry_read", self.entry_count, self.input_data, input_dict
                )
                break
            except UcsSchoolImportSkipImportRecord as exc:
                self.logger.info(
                    "Skipping input line %d as requested by PostReadPyHook: %s", self.entry_count, exc
                )

        cur_user_roles = self.get_roles(input_dict)
        cur_import_user = self.map(input_dict, cur_user_roles)
        cur_import_user.entry_count = self.entry_count
        cur_import_user.input_data = self.input_data
        cur_import_user.prepare_uids()
        return cur_import_user

    next = __next__  # py 2

    def get_roles(self, input_data):  # type: (Dict[str, Any]) -> Iterable[str]
        """
        IMPLEMENT ME
        Detect the ucsschool.lib.roles from the input data.

        :param dict input_data: dict user from read()
        :return: [ucsschool.lib.roles, ..]
        :rtype: list(str)
        """
        raise NotImplementedError()

    def map(self, input_data, cur_user_roles):  # type: (Dict[str, str], Iterable[str]) -> ImportUser
        """
        IMPLEMENT ME
        Creates a ImportUser object from a users dict (self.cur_entry). Data will not be modified, just
        copied.

        :param dict input_data: user from read()
        :param cur_user_roles: [ucsschool.lib.roles, ..]
        :type cur_user_roles: list(str)
        :return: ImportUser
        :rtype: ImportUser
        """
        raise NotImplementedError()

    def read(self, *args, **kwargs):  # type: (*Any, **Any) -> Iterator[Dict[Text, Text]]
        """
        IMPLEMENT ME
        Generator that returns dicts of read users
        Sets self.entry_count and self.input_data on each read.

        :param tuple args: arguments for implemented reader
        :param dict kwargs: arguments for implemented reader
        :return: iter([user, ...])
        :rtype: Iterator
        """
        raise NotImplementedError()

    def get_data_mapping(self, input_data):  # type: (Iterable[str]) -> Dict[str, Any]
        """
        IMPLEMENT ME
        Create a mapping from the configured input mapping to the actual input data. This is
        configuration and input format specific. See csv_reader for an example.
        Used by ImportUser.format_from_scheme().

        :param input_data: raw input data as stored in ImportUser.input_data
        :type input_data: list(str)
        :return: key->input_data-value mapping
        :rtype: dict
        """
        return {}

    def get_imported_udm_property_names(self, import_user):  # type: (ImportUser) -> List[str]
        """
        IMPLEMENT ME
        Return all udm attributes which are directly set by the reader class. This is
        configuration and input format specific. See csv_reader for an example.
        This function is used to set which attributes should be loaded from ldap into udm_properties
        for users which will be deleted.

        :param ImportUser import_user: an ImportUser object
        :return: list of udm attibute names
        :rtype: list(str)
        """
        return []
