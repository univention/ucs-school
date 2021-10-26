#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2021 Univention GmbH
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

from typing import TYPE_CHECKING, Optional

import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap
from univention.admin.uexceptions import objectExists

from .attributes import ContainerPath
from .base import UCSSchoolHelperAbstractClass
from .utils import _, ucr

if TYPE_CHECKING:
    from .base import LoType


class MailDomain(UCSSchoolHelperAbstractClass):
    school = None

    @classmethod
    def get_container(cls, school=None):
        return "cn=domain,cn=mail,%s" % ucr.get("ldap/base")

    class Meta:
        udm_module = "mail/domain"


class OU(UCSSchoolHelperAbstractClass):
    def create_without_hooks(self, lo, validate=True):  # type: (LoType, Optional[bool]) -> bool
        self.logger.info("Creating %r", self)
        pos = udm_uldap.position(ucr.get("ldap/base"))
        pos.setDn(self.position)
        udm_obj = udm_modules.get(self._meta.udm_module).object(None, lo, pos)
        udm_obj.open()
        udm_obj["name"] = self.name
        try:
            self.do_create(udm_obj, lo)
        except objectExists as exc:
            return exc.args[0]  # should return bool???
        else:
            return udm_obj.dn  # should return bool???

    def modify(self, lo, validate=True, move_if_necessary=None):
        # type: (LoType, Optional[bool], Optional[bool]) -> bool
        raise NotImplementedError()

    def remove(self, lo):  # type: (LoType) -> bool
        raise NotImplementedError()

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).schoolDN

    class Meta:
        udm_module = "container/ou"


class Container(OU):
    user_path = ContainerPath(_("User path"), udm_name="userPath")
    computer_path = ContainerPath(_("Computer path"), udm_name="computerPath")
    network_path = ContainerPath(_("Network path"), udm_name="networkPath")
    group_path = ContainerPath(_("Group path"), udm_name="groupPath")
    dhcp_path = ContainerPath(_("DHCP path"), udm_name="dhcpPath")
    policy_path = ContainerPath(_("Policy path"), udm_name="policyPath")
    share_path = ContainerPath(_("Share path"), udm_name="sharePath")
    printer_path = ContainerPath(_("Printer path"), udm_name="printerPath")

    class Meta:
        udm_module = "container/cn"
