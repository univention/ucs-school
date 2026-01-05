#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based format hooks."""

from __future__ import absolute_import

from ucsschool.importer.utils.import_pyhook import ImportPyHook


class FormatPyHook(ImportPyHook):
    """
    Format hook base class

    See ImportPyHook base class for documentation regarding the class' attributes.
    """

    priority = {
        "patch_fields_staff": None,
        "patch_fields_student": None,
        "patch_fields_teacher": None,
        "patch_fields_legal_guardian": None,
        "patch_fields_teacher_and_staff": None,
    }
    # The hook will be run only for property names in this list.
    properties = ()

    def patch_fields_staff(self, property_name, fields):
        """
        Run code before formatting an property using a schema in
        format_from_scheme().

        :param str property_name: Name of property_name that will be formatted
        :param dict fields: dictionary with the users attributes and udm_properties
        :return: fields dictionary that be used by format_from_scheme()
        :rtype: dict
        """
        return fields

    def patch_fields_student(self, property_name, fields):
        """
        Run code before formatting an property using a schema in
        format_from_scheme().

        :param str property_name: Name of property_name that will be formatted
        :param dict fields: dictionary with the users attributes and udm_properties
        :return: fields dictionary that be used by format_from_scheme()
        :rtype: dict
        """
        return fields

    def patch_fields_teacher(self, property_name, fields):
        """
        Run code before formatting an property using a schema in
        format_from_scheme().

        :param str property_name: Name of property_name that will be formatted
        :param dict fields: dictionary with the users attributes and udm_properties
        :return: fields dictionary that be used by format_from_scheme()
        :rtype: dict
        """
        return fields

    def patch_fields_legal_guardian(self, property_name, fields):
        """
        Run code before formatting an property using a schema in
        format_from_scheme().

        :param str property_name: Name of property_name that will be formatted
        :param dict fields: dictionary with the users attributes and udm_properties
        :return: fields dictionary that be used by format_from_scheme()
        :rtype: dict
        """
        return fields

    def patch_fields_teacher_and_staff(self, property_name, fields):
        """
        Run code before formatting a property using a schema in
        format_from_scheme().

        :param str property_name: Name of property_name that will be formatted
        :param dict fields: dictionary with the users attributes and udm_properties
        :return: fields dictionary that be used by format_from_scheme()
        :rtype: dict
        """
        return fields
