#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014 Univention GmbH
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

import ipaddr

import univention.admin.uldap as udm_uldap
import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects

from ucsschool.lib.models.attributes import DHCPServiceName, Attribute, DHCPSubnetName, DHCPSubnetMask, BroadcastAddress
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.utils import ucr, _, logger

class DHCPService(UCSSchoolHelperAbstractClass):
	name = DHCPServiceName(_('Service'))
	hostname = Attribute(_('Hostname'))
	domainname = Attribute(_('Domain'))

	def do_create(self, udm_obj, lo):
		udm_obj['option'] = ['wpad "http://%s.%s/proxy.pac"' % (self.hostname, self.domainname)]
		return super(DHCPService, self).do_create(udm_obj, lo)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).dhcp

	def add_server(self, dc_name, lo):
		from ucsschool.lib.models.school import School
		# TODO: more or less copied due to time constraints. Not adapted to "new"
		#   model style. DHCPServer or something would be necessary

		# create dhcp-server if not exsistant
		school = School.get(self.school)
		pos = udm_uldap.position(ucr.get('ldap/base'))
		dhcp_server_module = udm_modules.get('dhcp/server')
		dhcp_subnet_module = udm_modules.get('dhcp/subnet')
		objects = lo.searchDn(filter='(&(objectClass=dhcpServer)(cn=%s))' % dc_name, base=ucr.get('ldap/base'))
		if objects:
			# move existing dhcp server object to OU
			new_dhcp_server_dn = 'cn=%s,cn=%s,cn=dhcp,%s' % (dc_name, school.name.lower(), school.dn)
			if len(objects) > 1:
				logger.warning('More than one dhcp-server object found! Moving only one!')
			obj = udm_objects.get(dhcp_server_module, None, lo, position='', dn=objects[0])
			obj.open()
			dhcpServerContainer = ','.join(objects[0].split(',')[1:])
			if obj.dn.lower() != new_dhcp_server_dn.lower():
				attr_server = obj['server']
				logger.info('need to remove dhcp server: %s' % obj.dn)
				try:
					obj.remove()
				except:
					logger.error('Failed to remove dhcp server: %s' % (obj.dn))
				pos.setDn('cn=%s,cn=dhcp,%s' % (school.name.lower(), school.dn))
				logger.info('need to create dhcp server: %s' % pos.getDn())
				obj = dhcp_server_module.object(None, lo, position=pos, superordinate=self)
				obj.open()
				obj['server'] = attr_server
				try:
					obj.create()
					logger.info('%s created' % obj.dn)
				except:
					logger.error('Failed to create dhcp server: %s' % pos.getDn())
			################
			# copy subnets #
			################
			# find local interfaces
			interfaces = []
			for interface_name in set([key.split('/')[1] for key in ucr.keys() if key.startswith('interfaces/eth')]):
				try:
					address = ipaddr.IPv4Network('%s/%s' % (ucr['interfaces/%s/address' % interface_name],
					                                        ucr['interfaces/%s/netmask' % interface_name]))
					interfaces.append(address)
				except ValueError as exc:
					logger.info('Skipping invalid interface %s:\n%s' % (interface_name, exc))
			objects = lo.searchDn(filter = '(objectClass=univentionDhcpSubnet)', base=dhcpServerContainer)
			for object_dn in objects:
				obj = udm_objects.get(dhcp_subnet_module, None, lo, position='', dn=object_dn)
				obj.open()
				subnet = ipaddr.IPv4Network('%s/%s' % (obj['subnet'], obj['subnetmask']))
				if subnet in interfaces: # subnet matches any local subnet
					pos.setDn('cn=%s,cn=dhcp,%s' % (school.name.lower(), school.dn))
					if lo.searchDn(filter='(&(objectClass=univentionDhcpSubnet)(cn=%s))' % obj['subnet'], base=pos.getDn()):
						logger.info('do not need to copy dhcp subnet %s: %s (target already exists)' % (subnet, obj.dn))
					else:
						logger.info('need to copy dhcp subnet %s: %s' % (subnet, obj.dn))
						new_object = dhcp_subnet_module.object(None, lo, position=pos, superordinate=self)
						new_object.open()
						for key in obj.keys():
							value = obj[key]
							new_object[key] = value
						try:
							new_object.create()
							logger.info('%s created' % new_object.dn)
						except:
							logger.error('Failed to copy dhcp subnet %s to %s' % (obj.dn, pos.getDn()))
				else:
					logger.info('Skipping non-local subnet %s' % subnet)
		else:
			# create fresh dhcp server object
			pos.setDn('cn=%s,cn=dhcp,%s'%(school.name.lower(), school.dn))
			obj = dhcp_server_module.object(None, lo, position=pos, superordinate=self)
			obj.open()
			obj['server'] = dc_name
			logger.info('need to create dhcp server: %s' % obj.dn)
			try:
				obj.create()
				logger.info('%s created' % obj.dn)
			except:
				pass

	class Meta:
		udm_module = 'dhcp/service'

class DHCPSubnet(UCSSchoolHelperAbstractClass):
	name = DHCPSubnetName(_('Subnet address'))
	subnet_mask = DHCPSubnetMask(_('Netmask'))
	broadcast = BroadcastAddress(_('Broadcast'))

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).dhcp

	def get_superordinate(self):
		return udm_modules.get(self._meta.udm_module)

	class Meta:
		udm_module = 'dhcp/subnet'

