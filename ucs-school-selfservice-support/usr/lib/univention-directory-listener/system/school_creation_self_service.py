# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#

from __future__ import absolute_import

from ucsschool.lib.models.utils import add_or_remove_ucrv_value
from univention.listener import ListenerModuleHandler


class SchoolCreationSelfServiceListener(ListenerModuleHandler):
    # replaces the 10self_service_whitelist 00_hook script

    ucrv = "umc/self-service/passwordreset/whitelist/groups"
    delimiter = ","

    class Configuration(object):
        name = "selfservice_school_ucrv_listener"
        description = "Handles ucrv for schools in a self-service context"
        ldap_filter = "(objectClass=ucsschoolOrganizationalUnit)"

    def create(self, dn, new):
        """
        Adds a ucrv-value for the school

        :param dn: the dn of the new school
        :param new: the new school object
        :return:
        """
        self.logger.debug("dn: %r", dn)
        name = new["ou"][0].decode("UTF-8")
        value = "Domain Users {}".format(name)
        self.logger.info("Adding %r to ucrv %r.", value, self.ucrv)
        with self.as_root():
            add_or_remove_ucrv_value(self.ucrv, "add", value, self.delimiter)

    def remove(self, dn, old):
        self.logger.debug("dn: %r", dn)
        value = "Domain Users {}".format(old["ou"][0].decode("UTF-8"))
        self.logger.info("Removing %r from ucrv %r.", value, self.ucrv)
        with self.as_root():
            add_or_remove_ucrv_value(self.ucrv, "remove", value, self.delimiter)
