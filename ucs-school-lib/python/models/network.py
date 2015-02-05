#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2015 Univention GmbH
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

from ucsschool.lib.models.attributes import Netmask, NetworkAttribute, NetworkBroadcastAddress, SubnetName
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.dhcp import DHCPSubnet
from ucsschool.lib.models.utils import ucr, _, logger

class Network(UCSSchoolHelperAbstractClass):
	netmask = Netmask(_('Netmask'))
	network = NetworkAttribute(_('Network'))
	broadcast = NetworkBroadcastAddress(_('Broadcast'))

	_netmask_cache = {}

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).networks

	def get_subnet(self):
		# WORKAROUND for Bug #14795
		subnetbytes = 0
		netmask_parts = self.netmask.split('.')
		for part in netmask_parts:
			if part == '255':
				subnetbytes += 1
			else:
				break
		return '.'.join(self.network.split('.')[:subnetbytes])

	def create_without_hooks(self, lo, validate):
		dns_reverse_zone = DNSReverseZone.cache(self.get_subnet())
		dns_reverse_zone.create(lo)

		dhcp_service = self.get_school_obj(lo).get_dhcp_service()
		dhcp_subnet = DHCPSubnet(name=self.network, school=self.school, subnet_mask=self.netmask, broadcast=self.broadcast, dhcp_service=dhcp_service)
		dhcp_subnet.create(lo)

		# TODO:
		# set netbios and router for dhcp subnet
		#if defaultrouter:
		#	print 'setting default router'
		#	set_router_for_subnet (network, defaultrouter, schoolNr)

		#if netbiosserver:
		#	print 'setting netbios server'
		#	set_netbiosserver_for_subnet (network, netbiosserver, schoolNr)

		## set default value for nameserver
		#if nameserver:
		#	print 'setting nameserver'
		#	set_nameserver_for_subnet (network, nameserver, schoolNr)

		return super(Network, self).create_without_hooks(lo, validate)

	def do_create(self, udm_obj, lo):
		from ucsschool.lib.models.school import School
		# TODO:
		#if iprange:
		#	object['ipRange']=[[str(iprange[0]), str(iprange[1])]]

		# TODO: this is a DHCPServer created when school is created (not implemented yet)
		udm_obj['dhcpEntryZone'] = 'cn=%s,cn=dhcp,%s' % (self.school, School.cache(self.school).dn)
		udm_obj['dnsEntryZoneForward'] = 'zoneName=%s,cn=dns,%s' % (ucr.get('domainname'), ucr.get('ldap/base'))
		reversed_subnet = '.'.join(reversed(self.get_subnet().split('.')))
		udm_obj['dnsEntryZoneReverse'] = 'zoneName=%s.in-addr.arpa,cn=dns,%s' % (reversed_subnet, ucr.get('ldap/base'))
		return super(Network, self).do_create(udm_obj, lo)

	@classmethod
	def invalidate_cache(cls):
		super(Network, cls).invalidate_cache()
		cls._netmask_cache.clear()

	@classmethod
	def get_netmask(cls, dn, school, lo):
		if dn not in cls._netmask_cache:
			network = cls.from_dn(dn, school, lo)
			netmask = network.netmask # e.g. '24'
			network_str = '0.0.0.0/%s' % netmask
			try:
				ipv4_network = IPv4Network(network_str)
			except (AddressValueError, NetmaskValueError, ValueError):
				logger.warning('Unparsable network: %r' % network_str)
			else:
				netmask = str(ipv4_network.netmask) # e.g. '255.255.255.0'
			logger.debug('Network mask: %r is %r' % (dn, netmask))
			cls._netmask_cache[dn] = netmask
		return cls._netmask_cache[dn]

	class Meta:
		udm_module = 'networks/network'

class DNSReverseZone(UCSSchoolHelperAbstractClass):
	name = SubnetName(_('Subnet'))
	school = None

	@classmethod
	def get_container(cls, school=None):
		return 'cn=dns,%s' % ucr.get('ldap/base')

	def do_create(self, udm_obj, lo):
		udm_obj['nameserver'] = ucr.get('ldap/master')
		udm_obj['contact'] = 'root@%s' % ucr.get('domainname')
		return super(DNSReverseZone, self).do_create(udm_obj, lo)

	class Meta:
		udm_module = 'dns/reverse_zone'

