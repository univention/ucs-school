#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2021-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Example hook class that creates/modifies an email address for a school class.

Copy to /usr/share/ucs-school-import/pyhooks to activate it.
"""

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.hook import Hook


class MailForSchoolClass(Hook):
    model = SchoolClass
    priority = {
        "post_create": 10,
        "post_modify": 10,
    }

    def post_create(self, obj):  # type: (SchoolClass) -> None
        """
        Create an email address for the new school class.

        :param SchoolClass obj: the SchoolClass instance, that was just created.
        :return: None
        """
        ml_name = self.name_for_mailinglist(obj)
        self.logger.info("Setting email address %r on %r...", ml_name, obj)
        # The SchoolClass object does not have an email attribute, so we'll have to access the underlying
        # UDM object.
        udm_obj = obj.get_udm_object(self.lo)
        udm_obj["mailAddress"] = ml_name
        udm_obj.modify()

    def post_modify(self, obj):  # type: (SchoolClass) -> None
        """
        Change the email address of an existing school class, if it didn't have an email or was renamed.

        :param SchoolClass obj: the SchoolClass instance, that was just modified.
        :return: None
        """
        udm_obj = obj.get_udm_object(self.lo)
        ml_name = self.name_for_mailinglist(obj)
        if udm_obj["mailAddress"] != ml_name:  # this also works if it doesn't have an email address
            self.logger.info(
                "Changing the email address of %r from %r to %r...",
                obj,
                udm_obj["mailAddress"],
                ml_name,
            )
            udm_obj["mailAddress"] = ml_name
            udm_obj.modify()

    def name_for_mailinglist(self, obj):  # type: (SchoolClass) -> str
        return "{}@{}".format(obj.name, self.domainname).lower()

    @property
    def domainname(self):  # type: () -> str
        try:
            return self.ucr["mail/hosteddomains"].split()[0]
        except (AttributeError, IndexError):
            return self.ucr["domainname"]
