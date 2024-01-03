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

from univention.listener import ListenerModuleHandler
from univention.udm import UDM


class SchoolPasswordChangeSelfServiceListener(ListenerModuleHandler):
    # replaces the 10self_service_whitelist 00_hook script

    class Configuration(object):
        name = "selfservice_school_password_change_listener"
        description = "Handles the password change options in a self-service context"
        ldap_filter = "(objectClass=ucsschoolOrganizationalUnit)"

    def create(self, dn, new):
        """
        Adds the domain users of given school to the allowedGroups of the
        self-service (specifically the password change option)

        :param dn: the dn of the new school
        :param new: the new school object
        :return:
        """
        self.logger.debug(f"dn: {dn}")
        name = new["ou"][0].decode("UTF-8")
        ldap_base = self.ucr.get("ldap/base")
        self.logger.info(
            f"Adding 'Domain Users {name}' to allowedGroups of self-service-password-change."
        )

        # fetching required objects via UDM
        portals = UDM(self.lo).version(2).get("portals/entry")
        entry = portals.get(
            f"cn=self-service-password-change,cn=entry,cn=portals,cn=univention,{ldap_base}"
        )
        domain_users_group = f"cn=Domain Users {name},cn=groups,ou={name},{ldap_base}"

        # ensure idempotency of delete operation
        if domain_users_group not in entry.props.allowedGroups:
            entry.props.allowedGroups.append(domain_users_group)
            entry.save()
        else:
            self.logger.info(f"'Domain users {name}' are already eligible to modify their passwords.")

    def remove(self, dn, old):
        self.logger.debug(f"dn: {dn}")
        name = old["ou"][0].decode("UTF-8")
        ldap_base = self.ucr.get("ldap/base")
        self.logger.info(
            f"Removing'Domain Users {name}' from allowedGroups of self-service-password-change."
        )

        # fetching required objects via UDM
        portals = UDM(self.lo).version(2).get("portals/entry")
        entry = portals.get(
            f"cn=self-service-password-change,cn=entry,cn=portals,cn=univention,{ldap_base}"
        )
        domain_users_group = f"cn=Domain Users {name},cn=groups,ou={name},{ldap_base}"

        # ensure idempotency of delete operation
        if domain_users_group in entry.props.allowedGroups:
            entry.props.allowedGroups.remove(domain_users_group)
            entry.save()
        else:
            self.logger.info(
                f"'Domain Users {name}' not found in allowedGroups of self-service-password-change"
            )
