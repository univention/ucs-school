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

import re
from ldap.dn import escape_dn_chars

from univention.admin.syntax import (
	gid, string_numbers_letters_dots_spaces, uid_umlauts, iso8601Date,
	primaryEmailAddressValidDomain, boolean, UserDN, GroupDN, ipAddress,
	MAC_Address, disabled, reverseLookupSubnet, ipv4Address, v4netmask,
	netmask, UDM_Objects, string)
from univention.admin.uexceptions import valueError

from ucsschool.lib.models.utils import ucr, _

class ValidationError(Exception):
	pass

class Attribute(object):
	udm_name = None
	syntax = None
	extended = False
	value_type = None
	value_default = None

	def __init__(self, label, aka=None, udm_name=None, required=False, unlikely_to_change=False, internal=False):
		self.label = label
		self.aka = aka or [] # also_known_as
		self.required = required
		self.unlikely_to_change = unlikely_to_change
		self.internal = internal
		self.udm_name = udm_name or self.udm_name

	def _validate_syntax(self, values, syntax=None):
		if syntax is None:
			syntax = self.syntax
		if syntax:
			for val in values:
				try:
					syntax.parse(val)
				except valueError as e:
					raise ValueError(str(e))

	def validate(self, value):
		if value is not None:
			if self.value_type and not isinstance(value, self.value_type):
				raise ValueError(_('"%(label)s" needs to be a %(type)s') % {'type': self.value_type.__name__, 'label': self.label})
			values = value if self.value_type else [value]
			self._validate_syntax(values)
		else:
			if self.required:
				raise ValueError(_('"%s" is required. Please provide this information.') % self.label)

class CommonName(Attribute):
	udm_name = 'name'
	syntax = None

	def __init__(self, label, aka=None):
		super(CommonName, self).__init__(label, aka=aka, required=True)

	def validate(self, value):
		super(CommonName, self).validate(value)
		escaped = escape_dn_chars(value)
		if value != escaped:
			raise ValueError(_('May not contain special characters'))

class Username(CommonName):
	udm_name = 'username'
	syntax = uid_umlauts

class DHCPServerName(CommonName):
	udm_name = 'server'

class DHCPServiceName(CommonName):
	udm_name = 'service'

class GroupName(CommonName):
	syntax = gid

class SchoolClassName(GroupName):
	def _validate_syntax(self, values, syntax=None):
		super(SchoolClassName, self)._validate_syntax(values)
		# needs to check ShareName.syntax, too: SchoolClass will
		#   create a share with its own name
		super(SchoolClassName, self)._validate_syntax(values, syntax=ShareName.syntax)

class ShareName(CommonName):
	syntax = string_numbers_letters_dots_spaces

class SubnetName(CommonName):
	udm_name = 'subnet'
	syntax = reverseLookupSubnet

class DHCPSubnetName(SubnetName):
	udm_name = 'subnet'
	syntax = ipv4Address

class SchoolName(CommonName):
	udm_name = 'name'

	def validate(self, value):
		super(SchoolName, self).validate(value)
		if ucr.is_true('ucsschool/singlemaster', False):
			regex = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$')
			if not regex.match(value):
				raise ValueError(_('Invalid school name'))

class DCName(Attribute):
	def validate(self, value):
		super(DCName, self).validate(value)
		if value:
			regex = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$')
			if not regex.match(value):
				raise ValueError(_('Invalid Domain Controller name'))
			if ucr.is_true('ucsschool/singlemaster', False):
				if len(value) > 12:
					raise ValueError(_('A valid NetBIOS hostname can not be longer than 12 characters.'))
				if sum([len(value), 1, len(ucr.get('domainname', ''))]) > 63:
					raise ValueError(_('The length of fully qualified domain name is greater than 63 characters.'))

class Firstname(Attribute):
	udm_name = 'firstname'

class Lastname(Attribute):
	udm_name = 'lastname'

class Birthday(Attribute):
	udm_name = 'birthday'
	syntax = iso8601Date

class Email(Attribute):
	udm_name = 'mailPrimaryAddress'
	syntax = primaryEmailAddressValidDomain

	def validate(self, value):
		if value:
			# do not validate ''
			super(Email, self).validate(value)

class Password(Attribute):
	udm_name = 'password'

class Disabled(Attribute):
	udm_name = 'disabled'
	syntax = disabled

class SchoolAttribute(CommonName):
	udm_name = None

class SchoolClassesAttribute(Attribute):
	udm_name = None
	value_type = dict
	value_default = dict

class SchoolClassAttribute(Attribute):
	pass

class Description(Attribute):
	udm_name = 'description'

class DisplayName(Attribute):
	udm_name = 'displayName'
	extended = True

class EmptyAttributes(Attribute):
	udm_name = 'emptyAttributes'
	# syntax = dhcp_dnsFixedAttributes # only set internally, no need to use.
	#   also, it is not part of the "main" syntax.py!

class ContainerPath(Attribute):
	syntax = boolean

class ShareFileServer(Attribute):
	syntax = UDM_Objects # UCSSchool_Server_DN is not always available. Easy check: DN
	extended = True

class Groups(Attribute):
	syntax = GroupDN
	value_type = list

class Users(Attribute):
	udm_name = 'users'
	syntax = UserDN
	value_type = list

class IPAddress(Attribute):
	udm_name = 'ip'
	syntax = ipAddress

class SubnetMask(Attribute):
	pass

class DHCPSubnetMask(Attribute):
	udm_name = 'subnetmask'
	syntax = v4netmask

class DHCPServiceAttribute(Attribute):
	pass

class BroadcastAddress(Attribute):
	udm_name = 'broadcastaddress'
	syntax = ipv4Address

class NetworkBroadcastAddress(Attribute):
	syntax = ipv4Address

class NetworkAttribute(Attribute):
	udm_name = 'network'
	syntax = ipAddress

class Netmask(Attribute):
	udm_name = 'netmask'
	syntax = netmask

class MACAddress(Attribute):
	udm_name = 'mac'
	syntax = MAC_Address

class InventoryNumber(Attribute):
	pass

class Hosts(Attribute):
	udm_name = 'hosts'
	value_type = list
	syntax = UDM_Objects

class Schools(Attribute):
	udm_name = 'school'
	value_type = list
	value_default = list
	syntax = string  # ucsschoolSchools (cannot be used because it's not available on import time on a unjoined DC Slave)
	extended = True

class RecordUID(Attribute):
	udm_name = 'ucsschoolRecordUID'
	syntax = string
	extended = True

class SourceUID(Attribute):
	udm_name = 'ucsschoolSourceUID'
	syntax = string
	extended = True
