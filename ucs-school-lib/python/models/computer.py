#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2016 Univention GmbH
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

from ipaddr import IPv4Network, AddressValueError, NetmaskValueError
from ldap.filter import escape_filter_chars

from univention.admin.uexceptions import nextFreeIp

from ucsschool.lib.models.attributes import Groups, IPAddress, SubnetMask, MACAddress, InventoryNumber, Attribute
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass, MultipleObjectsError

from ucsschool.lib.models.dhcp import DHCPServer, AnyDHCPService
from ucsschool.lib.models.network import Network
from ucsschool.lib.models.group import BasicGroup
from ucsschool.lib.models.utils import ucr, _, logger

class AnyComputer(UCSSchoolHelperAbstractClass):
	@classmethod
	def get_container(cls, school=None):
		from ucsschool.lib.models.school import School
		if school:
			return School.cache(school).dn
		return ucr.get('ldap/base')

	class Meta:
		udm_module = 'computers/computer'

class SchoolDC(UCSSchoolHelperAbstractClass):
	# NOTE: evaluate filter (&(service=UCS@school)(service=UCS@school Education)) # UCS@school Administration
	# vs. group memberships

	@classmethod
	def get_container(cls, school):
		return 'cn=dc,cn=server,%s' % cls.get_search_base(school).computers

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		try:
			univention_object_class = udm_obj['univentionObjectClass']
		except KeyError:
			univention_object_class = None
		if univention_object_class == 'computers/domaincontroller_slave':
			return SchoolDCSlave
		return cls

class SchoolDCSlave(SchoolDC):
	groups = Groups(_('Groups'))

	def do_create(self, udm_obj, lo):
		udm_obj['unixhome'] = '/dev/null'
		udm_obj['shell'] = '/bin/bash'
		udm_obj['primaryGroup'] = BasicGroup.cache('DC Slave Hosts').dn
		return super(SchoolDCSlave, self).do_create(udm_obj, lo)

	def _alter_udm_obj(self, udm_obj):
		if self.groups:
			for group in self.groups:
				if group not in udm_obj['groups']:
					udm_obj['groups'].append(group)
		return super(SchoolDCSlave, self)._alter_udm_obj(udm_obj)

	def move_without_hooks(self, lo, udm_obj=None, force=False):
		try:
			if udm_obj is None:
				try:
					udm_obj = self.get_only_udm_obj(lo, 'cn=%s' % escape_filter_chars(self.name))
				except MultipleObjectsError:
					logger.error('Found more than one DC Slave with hostname "%s"', self.name)
					return False
				if udm_obj is None:
					logger.error('Cannot find DC Slave with hostname "%s"', self.name)
					return False
			old_dn = udm_obj.dn
			school = self.get_school_obj(lo)
			group_dn = school.get_administrative_group_name('educational', ou_specific=True, as_dn=True)
			if group_dn not in udm_obj['groups']:
				logger.error('%r has no LDAP access to %r', self, school)
				return False
			if old_dn == self.dn:
				logger.info('DC Slave "%s" is already located in "%s" - stopping here', self.name, self.school)
			self.set_dn(old_dn)
			if self.exists_outside_school(lo):
				if not force:
					logger.error('DC Slave "%s" is located in another OU - %s', self.name, udm_obj.dn)
					logger.error('Use force=True to override')
					return False
			if school is None:
				logger.error('Cannot move DC Slave object - School does not exist: %r', school)
				return False
			self.modify_without_hooks(lo)
			if school.class_share_file_server == old_dn:
				school.class_share_file_server = self.dn
			if school.home_share_file_server == old_dn:
				school.home_share_file_server = self.dn
			school.modify_without_hooks(lo)

			removed = False
			# find dhcp server object by checking all dhcp service objects
			for dhcp_service in AnyDHCPService.get_all(lo, None):
				for dhcp_server in dhcp_service.get_servers(lo):
					if dhcp_server.name == self.name and not dhcp_server.dn.endswith(',%s' % school.dn):
						dhcp_server.remove(lo)
						removed = True

			if removed:
				own_dhcp_service = school.get_dhcp_service()

				dhcp_server = DHCPServer(name=self.name, school=self.school, dhcp_service=own_dhcp_service)
				dhcp_server.create(lo)

			logger.info('Move complete')
			logger.warning('The DC Slave has to be rejoined into the domain!')
		finally:
			self.invalidate_cache()
		return True

	class Meta:
		udm_module = 'computers/domaincontroller_slave'
		name_is_unique = True
		allow_school_change = True

class SchoolComputer(UCSSchoolHelperAbstractClass):
	ip_address = IPAddress(_('IP address'), required=True)
	subnet_mask = SubnetMask(_('Subnet mask'))
	mac_address = MACAddress(_('MAC address'), required=True)
	inventory_number = InventoryNumber(_('Inventory number'))
	zone = Attribute(_('Zone'))

	type_name = _('Computer')

	DEFAULT_PREFIX_LEN = 24  # 255.255.255.0

	def get_inventory_numbers(self):
		if isinstance(self.inventory_number, basestring):
			return [inv.strip() for inv in self.inventory_number.split(',')]
		if isinstance(self.inventory_number, (list, tuple)):
			return list(self.inventory_number)
		return []

	def _alter_udm_obj(self, udm_obj):
		super(SchoolComputer, self)._alter_udm_obj(udm_obj)
		inventory_numbers = self.get_inventory_numbers()
		if inventory_numbers:
			udm_obj['inventoryNumber'] = inventory_numbers
		ipv4_network = self.get_ipv4_network()
		if ipv4_network:
			if self._ip_is_set_to_subnet(ipv4_network):
				logger.info('IP was set to subnet. Unsetting it on the computer so that UDM can do some magic: Assign next free IP!')
				udm_obj['ip'] = ''
			else:
				udm_obj['ip'] = str(ipv4_network.ip)
		# set network after ip. Otherwise UDM does not do any
		#   nextIp magic...
		network = self.get_network()
		if network:
			# reset network, so that next line triggers free ip
			udm_obj.old_network = None
			try:
				udm_obj['network'] = network.dn
			except nextFreeIp:
				logger.error('Tried to set IP automatically, but failed! %r is full', network)
				raise nextFreeIp(_('There are no free addresses left in the subnet!'))

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).computers

	def create(self, lo, validate=True):
		if self.subnet_mask is None:
			self.subnet_mask = self.DEFAULT_PREFIX_LEN
		return super(SchoolComputer, self).create(lo, validate)

	def create_without_hooks(self, lo, validate):
		self.create_network(lo)
		return super(SchoolComputer, self).create_without_hooks(lo, validate)

	def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
		self.create_network(lo)
		return super(SchoolComputer, self).modify_without_hooks(lo, validate, move_if_necessary)

	def get_ipv4_network(self):
		if self.subnet_mask is not None:
			network_str = '%s/%s' % (self.ip_address, self.subnet_mask)
		else:
			network_str = str(self.ip_address)
		try:
			return IPv4Network(network_str)
		except (AddressValueError, NetmaskValueError, ValueError):
			logger.warning('Unparsable network: %r', network_str)

	def _ip_is_set_to_subnet(self, ipv4_network=None):
		ipv4_network = ipv4_network or self.get_ipv4_network()
		if ipv4_network:
			return ipv4_network.ip == ipv4_network.network

	def get_network(self):
		ipv4_network = self.get_ipv4_network()
		if ipv4_network:
			network_name = '%s-%s' % (self.school.lower(), ipv4_network.network)
			network = str(ipv4_network.network)
			netmask = str(ipv4_network.netmask)
			broadcast = str(ipv4_network.broadcast)
			return Network.cache(network_name, self.school, network=network, netmask=netmask, broadcast=broadcast)

	def create_network(self, lo):
		network = self.get_network()
		if network:
			network.create(lo)
		return network

	def validate(self, lo, validate_unlikely_changes=False):
		super(SchoolComputer, self).validate(lo, validate_unlikely_changes)
		if self.ip_address:
			name, ip_address = escape_filter_chars(self.name), escape_filter_chars(self.ip_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(ip=%s)' % (name, ip_address)):
				self.add_error('ip_address', _('The ip address is already taken by another computer. Please change the ip address.'))
		if self.mac_address:
			name, mac_address = escape_filter_chars(self.name), escape_filter_chars(self.mac_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(mac=%s)' % (name, mac_address)):
				self.add_error('mac_address', _('The mac address is already taken by another computer. Please change the mac address.'))

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		oc = udm_obj.lo.get(udm_obj.dn, ['objectClass'])
		object_classes = oc.get('objectClass', [])
		if 'univentionWindows' in object_classes:
			return WindowsComputer
		if 'univentionMacOSClient' in object_classes:
			return MacComputer
		if 'univentionCorporateClient' in object_classes:
			return UCCComputer
		if 'univentionClient' in object_classes:
			return IPComputer

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		from ucsschool.lib.models.school import School
		obj = super(SchoolComputer, cls).from_udm_obj(udm_obj, school, lo)
		obj.ip_address = udm_obj['ip']
		school_obj = School.cache(obj.school)
		edukativnetz_group = school_obj.get_administrative_group_name('educational', domain_controller=False, as_dn=True)
		if edukativnetz_group in udm_obj['groups']:
			obj.zone = 'edukativ'
		verwaltungsnetz_group = school_obj.get_administrative_group_name('administrative', domain_controller=False, as_dn=True)
		if verwaltungsnetz_group in udm_obj['groups']:
			obj.zone = 'verwaltung'
		network_dn = udm_obj['network']
		if network_dn:
			netmask = Network.get_netmask(network_dn, school, lo)
			obj.subnet_mask = netmask
		obj.inventory_number = ', '.join(udm_obj['inventoryNumber'])
		return obj

	def build_hook_line(self, hook_time, func_name):
		module_part = self._meta.udm_module.split('/')[1]
		return self._build_hook_line(
			module_part,
			self.name,
			self.mac_address,
			self.school,
			self.get_ipv4_network(),
			','.join(self.get_inventory_numbers()),
			self.zone
		)

	def to_dict(self):
		ret = super(SchoolComputer, self).to_dict()
		ret['type_name'] = self.type_name
		ret['type'] = self._meta.udm_module_short
		return ret

	class Meta:
		udm_module = 'computers/computer'
		name_is_unique = True

class WindowsComputer(SchoolComputer):
	type_name = _('Windows system')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/windows'
		hook_path = 'computer'

class MacComputer(SchoolComputer):
	type_name = _('Mac OS X')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/macos'
		hook_path = 'computer'

class IPComputer(SchoolComputer):
	type_name = _('Device with IP address')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ipmanagedclient'
		hook_path = 'computer'

class UCCComputer(SchoolComputer):
	type_name = _('Univention Corporate Client')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ucc'
		hook_path = 'computer'

