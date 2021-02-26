# -*- coding: utf-8 -*-
#
# Copyright 2017-2021 Univention GmbH
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

from ucsschool.lib.models.utils import add_or_remove_ucrv
from univention.listener import ListenerModuleHandler


class ListenerModuleTemplate(ListenerModuleHandler):
    # replaces the 10self_service_whitelist 00_hook script:
    #     /usr/share/ucs-school-lib/modify_ucr_list

    ucrv = "umc/self-service/passwordreset/whitelist/groups"

    delimiter = ","

    class Configuration(object):
        name = "selfservice_school_ucrv_listener"
        description = "Handles ucrv for schools in a self-service context"
        ldap_filter = "(objectClass=ucsschoolOrganizationalUnit)"

    def create(self, dn, new):
        self.logger.debug("dn: %r", dn)
        value = "Domain Users {}".format(new["ou"][0])
        self.logger.info("Adding '{}' to ucrv '{}'".format(value, self.ucrv))
        with self.as_root():
            add_or_remove_ucrv(self.ucrv, "add", value, self.delimiter)

    def modify(self, dn, old, new, old_dn):
        pass

    def remove(self, dn, old):
        self.logger.info("=" * 60)
        self.logger.debug("dn: %r", dn)
        value = "Domain Users {}".format(old["ou"][0])
        self.logger.info("Removing '{}' from ucrv '{}'".format(value, self.ucrv))
        with self.as_root():
            add_or_remove_ucrv(self.ucrv, "remove", value, self.delimiter)
