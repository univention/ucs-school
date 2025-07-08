#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import absolute_import

from ucsschool.lib.models.utils import exec_cmd
from univention.listener import ListenerModuleHandler


class SchoolCreationHttpApiUpdateListener(ListenerModuleHandler):
    # replaces the 70http_api_school_create 00_hook script

    class Configuration(object):
        name = "http_api_school_listener"
        description = "Updates the database for the http_api"
        ldap_filter = "(objectClass=ucsschoolOrganizationalUnit)"

    def _update_http_api(self):
        with self.as_root():
            self.logger.info("Syncing all schools in http api")
            returncode, stdout, stderr = exec_cmd(
                ["/usr/bin/python3", "-m", "ucsschool.http_api.manage", "updateschools", "-a"],
                raise_exc=False,
            )
            if returncode:
                self.logger.warning("http_api says: %r", (returncode, stdout, stderr))

    def initialize(self):
        self._update_http_api()

    def create(self, dn, new):
        """
        Updates the database for the http_api

        :param dn: the dn of the new school
        :param new: the new school object
        :return:
        """
        self.logger.debug("dn: %r", dn)
        name = new["ou"][0].decode("UTF-8")
        with self.as_root():
            self.logger.info("Update school {} in http api".format(name))
            returncode, stdout, stderr = exec_cmd(
                ["/usr/bin/python3", "-m", "ucsschool.http_api.manage", "updateschools", "--ou", name],
                raise_exc=False,
            )
            if returncode:
                self.logger.warning("http_api says: %r", (returncode, stdout, stderr))

    def remove(self, dn, old):
        self.logger.debug("dn: %r", dn)
        self._update_http_api()
