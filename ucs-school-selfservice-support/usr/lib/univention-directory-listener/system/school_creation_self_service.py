# -*- coding: utf-8 -*-
#
# Copyright 2017-2024 Univention GmbH
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
# you and Univention.
#
# This program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.
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
        name = new["ou"][0]
        value = "Domain Users {}".format(name)
        self.logger.info("Adding %r to ucrv %r.", value, self.ucrv)
        with self.as_root():
            add_or_remove_ucrv_value(self.ucrv, "add", value, self.delimiter)

    def remove(self, dn, old):
        self.logger.debug("dn: %r", dn)
        value = "Domain Users {}".format(old["ou"][0])
        self.logger.info("Removing %r from ucrv %r.", value, self.ucrv)
        with self.as_root():
            add_or_remove_ucrv_value(self.ucrv, "remove", value, self.delimiter)
