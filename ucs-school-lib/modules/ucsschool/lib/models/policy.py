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

from udm_rest_client import UDM, ModifyError, UdmObject

from .attributes import EmptyAttributes
from .base import UCSSchoolHelperAbstractClass, UCSSchoolModel
from .utils import _


class Policy(UCSSchoolHelperAbstractClass):
    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).policies

    async def attach(self, obj: UCSSchoolModel, lo: UDM) -> None:
        # add the missing policy
        udm_obj: UdmObject = await obj.get_udm_object(lo)
        if self.dn.lower() not in [dn.lower() for dn in udm_obj.policies[self.Meta.udm_module]]:
            udm_obj.policies[self.Meta.udm_module].append(self.dn)
        else:
            self.logger.info("Already attached!")
            return
        self.logger.info("Attaching %r to %r", self, obj)
        try:
            await udm_obj.save()
        except ModifyError as exc:
            self.logger.warning("Policy %s cannot be referenced to %r: %s", self, obj, exc)


class UMCPolicy(Policy):
    class Meta:
        udm_module = "policies/umc"


class DHCPDNSPolicy(Policy):
    empty_attributes = EmptyAttributes(_("Empty attributes"))

    class Meta:
        udm_module = "policies/dhcp_dns"
