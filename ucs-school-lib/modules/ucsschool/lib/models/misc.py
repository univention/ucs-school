# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2019 Univention GmbH
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

from univention.admin.uldap import position as uldap_position

from udm_rest_client import UDM

from .attributes import ContainerPath
from .base import UCSSchoolHelperAbstractClass
from .utils import _, ucr


class MailDomain(UCSSchoolHelperAbstractClass):
	school = None

	@classmethod
	def get_container(cls, school: str = None) -> str:
		return 'cn=domain,cn=mail,%s' % ucr.get('ldap/base')

	class Meta:
		udm_module = 'mail/domain'


class OU(UCSSchoolHelperAbstractClass):

	async def create(self, lo: UDM, validate: bool = True):
		self.logger.info('Creating %r', self)
		pos = uldap_position(ucr.get('ldap/base'))
		pos.setDn(self.position)
		udm_obj = await lo.get(self._meta.udm_module).new()
		udm_obj.props.name = self.name
		# try:
		# 	self.do_create(udm_obj, lo)
		# except objectExists as exc:
		# 	return exc.args[0]
		# else:
		# 	return udm_obj.dn
		await self.do_create(udm_obj, lo)
		return udm_obj.dn

	async def modify(self, lo: UDM, validate: bool = True, move_if_necessary: bool = None):
		raise NotImplementedError()

	async def remove(self, lo: UDM):
		raise NotImplementedError()

	@classmethod
	def get_container(cls, school: str):
		return cls.get_search_base(school).schoolDN

	class Meta:
		udm_module = 'container/ou'


class Container(OU):
	user_path = ContainerPath(_('User path'), udm_name='userPath')
	computer_path = ContainerPath(_('Computer path'), udm_name='computerPath')
	network_path = ContainerPath(_('Network path'), udm_name='networkPath')
	group_path = ContainerPath(_('Group path'), udm_name='groupPath')
	dhcp_path = ContainerPath(_('DHCP path'), udm_name='dhcpPath')
	policy_path = ContainerPath(_('Policy path'), udm_name='policyPath')
	share_path = ContainerPath(_('Share path'), udm_name='sharePath')
	printer_path = ContainerPath(_('Printer path'), udm_name='printerPath')

	class Meta:
		udm_module = 'container/cn'
