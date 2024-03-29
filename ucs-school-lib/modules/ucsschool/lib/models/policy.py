#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2024 Univention GmbH
#
# http://www.univention.de/
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
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import ldap

from .attributes import EmptyAttributes
from .base import UCSSchoolHelperAbstractClass
from .utils import _


class Policy(UCSSchoolHelperAbstractClass):
    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).policies

    def attach(self, obj, lo):
        # add univentionPolicyReference if neccessary
        oc = lo.get(obj.dn, ["objectClass"])
        if b"univentionPolicyReference" not in oc.get("objectClass", []):
            try:
                lo.modify(obj.dn, [("objectClass", [], b"univentionPolicyReference")])
            except ldap.LDAPError:
                self.logger.warning("Objectclass univentionPolicyReference cannot be added to %r", obj)
                return
        # add the missing policy
        pl = lo.get(obj.dn, ["univentionPolicyReference"])
        self.logger.info("Attaching %r to %r", self, obj)
        if not any(
            self.dn.lower() == x.decode("UTF-8").lower() for x in pl.get("univentionPolicyReference", [])
        ):
            modlist = [("univentionPolicyReference", [], self.dn.encode("utf-8"))]
            try:
                lo.modify(obj.dn, modlist)
            except ldap.LDAPError:
                self.logger.warning("Policy %s cannot be referenced to %r", self, obj)
        else:
            self.logger.info("Already attached!")


class UMCPolicy(Policy):
    class Meta:
        udm_module = "policies/umc"


class DHCPDNSPolicy(Policy):
    empty_attributes = EmptyAttributes(_("Empty attributes"))

    class Meta:
        udm_module = "policies/dhcp_dns"
