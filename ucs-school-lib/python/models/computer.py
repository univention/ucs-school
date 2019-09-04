#!/usr/bin/python2.7
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

from ipaddr import IPv4Network, AddressValueError, NetmaskValueError
from ldap.filter import escape_filter_chars

from univention.admin.filter import conjunction, expression, parse
from univention.admin.uexceptions import nextFreeIp

from .attributes import Groups, IPAddress, SubnetMask, MACAddress, InventoryNumber, Attribute, Roles
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass, MultipleObjectsError

from ..roles import role_ip_computer, role_mac_computer, role_win_computer, create_ucsschool_role_string, role_teacher_computer

from .dhcp import DHCPServer, AnyDHCPService
from .network import Network
from .group import BasicGroup
from .utils import ucr, _


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


class SchoolDCSlave(RoleSupportMixin, SchoolDC):
	groups = Groups(_('Groups'))
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])

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

	def get_schools_from_udm_obj(self, udm_obj):
		# fixme: no idea how to find out old school
		return self.school

	def move_without_hooks(self, lo, udm_obj=None, force=False):
		try:
			if udm_obj is None:
				try:
					udm_obj = self.get_only_udm_obj(lo, 'cn=%s' % escape_filter_chars(self.name))
				except MultipleObjectsError:
					self.logger.error('Found more than one DC Slave with hostname "%s"', self.name)
					return False
				if udm_obj is None:
					self.logger.error('Cannot find DC Slave with hostname "%s"', self.name)
					return False
			old_dn = udm_obj.dn
			school = self.get_school_obj(lo)
			group_dn = school.get_administrative_group_name('educational', ou_specific=True, as_dn=True)
			if group_dn not in udm_obj['groups']:
				self.logger.error('%r has no LDAP access to %r', self, school)
				return False
			if old_dn == self.dn:
				self.logger.info('DC Slave "%s" is already located in "%s" - stopping here', self.name, self.school)
			self.set_dn(old_dn)
			if self.exists_outside_school(lo):
				if not force:
					self.logger.error('DC Slave "%s" is located in another OU - %s', self.name, udm_obj.dn)
					self.logger.error('Use force=True to override')
					return False
			if school is None:
				self.logger.error('Cannot move DC Slave object - School does not exist: %r', school)
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

			self.logger.info('Move complete')
			self.logger.warning('The DC Slave has to be rejoined into the domain!')
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

	@classmethod
	def lookup(cls, lo, school, filter_s='', superordinate=None):
		"""
		This override limits the returned objects to actual ucsschoolComputers. Does not contain
		SchoolDC slaves and others anymore.
		"""
		object_class_filter = expression('objectClass', 'ucsschoolComputer', '=')
		if filter_s:
			school_computer_filter = conjunction('&', [object_class_filter, parse(filter_s)])
		else:
			school_computer_filter = object_class_filter
		return super(SchoolComputer, cls).lookup(lo, school, school_computer_filter, superordinate)

	def get_inventory_numbers(self):
		if isinstance(self.inventory_number, basestring):
			return [inv.strip() for inv in self.inventory_number.split(',')]
		if isinstance(self.inventory_number, (list, tuple)):
			return list(self.inventory_number)
		return []

	@property
	def teacher_computer(self):  # type: () -> bool
		"""True if the computer is a teachers computer."""
		return create_ucsschool_role_string(role_teacher_computer, self.school) in self.ucsschool_roles

	@teacher_computer.setter
	def teacher_computer(self, new_value):  # type: (bool) -> None
		"""Un/mark computer as a teachers computer."""
		role_str = create_ucsschool_role_string(role_teacher_computer, self.school)
		if new_value and role_str not in self.ucsschool_roles:
			self.ucsschool_roles.append(role_str)
		elif not new_value and role_str in self.ucsschool_roles:
			self.ucsschool_roles.remove(role_str)

	def _alter_udm_obj(self, udm_obj):
		super(SchoolComputer, self)._alter_udm_obj(udm_obj)
		inventory_numbers = self.get_inventory_numbers()
		if inventory_numbers:
			udm_obj['inventoryNumber'] = inventory_numbers
		ipv4_network = self.get_ipv4_network()
		if ipv4_network and len(udm_obj['ip']) < 2:
			if self._ip_is_set_to_subnet(ipv4_network):
				self.logger.info('IP was set to subnet. Unsetting it on the computer so that UDM can do some magic: Assign next free IP!')
				udm_obj['ip'] = []
			else:
				udm_obj['ip'] = [str(ipv4_network.ip)]
			# set network after ip. Otherwise UDM does not do any
			#   nextIp magic...
			network = self.get_network()
			if network:
				# reset network, so that next line triggers free ip
				udm_obj.old_network = None
				try:
					udm_obj['network'] = network.dn
				except nextFreeIp:
					self.logger.error('Tried to set IP automatically, but failed! %r is full', network)
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
		if self.subnet_mask is not None and len(self.ip_address) > 0:
			network_str = '%s/%s' % (self.ip_address[0], self.subnet_mask)
		elif len(self.ip_address) > 0:
			network_str = str(self.ip_address[0])
		else:
			network_str = ''
		try:
			return IPv4Network(network_str)
		except (AddressValueError, NetmaskValueError, ValueError):
			self.logger.warning('Unparsable network: %r', network_str)

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
		for ip_address in self.ip_address:
			name, ip_address = escape_filter_chars(self.name), escape_filter_chars(ip_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(ip=%s)' % (name, ip_address)):
				self.add_error('ip_address', _('The ip address is already taken by another computer. Please change the ip address.'))
		for mac_address in self.mac_address:
			name, mac_address = escape_filter_chars(self.name), escape_filter_chars(mac_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(mac=%s)' % (name, mac_address)):
				self.add_error('mac_address', _('The mac address is already taken by another computer. Please change the mac address.'))
		own_network = self.get_network()
		own_network_ip4 = self.get_ipv4_network()
		if own_network and not own_network.exists(lo):
			self.add_warning('subnet_mask', _('The specified IP and subnet mask will cause the creation of a new network during the creation of the computer object.'))
			networks = [(network[1]['cn'][0],
						IPv4Network(network[1]['univentionNetwork'][0] + '/' + network[1]['univentionNetmask'][0])) for
						network in lo.search('(univentionObjectType=networks/network)')]
			is_singlemaster = ucr.get('ucsschool/singlemaster', False)
			for network in networks:
				if is_singlemaster and network[0] == 'default' and own_network_ip4 == network[1]: # Bug #48099: jump conflict with default network in singleserver environment
					continue
				if own_network_ip4.overlaps(network[1]):
					self.add_error('subnet_mask', _('The newly created network would overlap with the existing network {}').format(network[0]))


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


class WindowsComputer(RoleSupportMixin, SchoolComputer):
	type_name = _('Windows system')
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])
	default_roles = [role_win_computer]

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/windows'
		hook_path = 'computer'


class MacComputer(RoleSupportMixin, SchoolComputer):
	type_name = _('Mac OS X')
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])
	default_roles = [role_mac_computer]

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/macos'
		hook_path = 'computer'


class IPComputer(RoleSupportMixin, SchoolComputer):
	type_name = _('Device with IP address')
	ucsschool_roles = Roles(_('Roles'), aka=['Roles'])
	default_roles = [role_ip_computer]

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ipmanagedclient'
		hook_path = 'computer'


class UCCComputer(SchoolComputer):
	type_name = _('Univention Corporate Client')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ucc'
		hook_path = 'computer'
