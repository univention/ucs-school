#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  UCS@school Role share management wizzard
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

from univention.lib.i18n import Translation
from ucsschool.lib.i18n import ucs_school_name_i18n
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import simple_response
from ucsschool.lib.schoolldap import SchoolBaseModule, LDAP_Connection, USER_READ, USER_WRITE
from univention.admin.filter import conjunction, expression
from univention.config_registry import ConfigRegistry
import univention.admin.modules as udm_modules
udm_modules.update()
import grp

_ = Translation('ucs-school-umc-roleshares').translate

ucr = ConfigRegistry()
ucr.load()

class Instance(SchoolBaseModule):
	def init(self):
		super(Instance, self).init()
		self.module_name = "school-roleshares"
		self.udm_module_name = 'shares/share'

	@simple_response
	def query(self):
		"""Searches for role shares
		requests.options = {}
		  'pattern' -- pattern to match
		"""
		MODULE.info('%s.query: options: %s' % (self.module_name, request.options,))
		pattern = request.options.get('pattern', '').lower()
		return self.get_shares(pattern)

	@LDAP_Connection(USER_READ)
	def get_shares(self, pattern, ldap_user_read=None, ldap_position=None, search_base=None)):

		result = {}
		result['shares'] = []

		supported_roles = (role_pupil, role_teacher, role_staff)

		if not search_base.availableSchools:
			MODULE.error('%s.query: No schools available to this user!' % (self.module_name,))
			return result	## empty

		## sanitize the search pattern to match only role shares
		search_pattern_parts = pattern.split("-", 1)
		role_specified=False
		for role in supported_roles:
			if search_pattern_parts[0] == role:
				role_specified=True

		school_ou_specified=False
		if len(search_pattern_parts) == 2:
			for school_ou in search_base.availableSchools:
				if len search_pattern_parts[1] == school_ou:
					school_ou_specified=True

		udm_filter = None
		if school_ou_specified:
			if role_specified:
				udm_filter = pattern
			else:
				hints = []
				for role in supported_roles:
					hints.append(expression('name', "-".join((role, pattern))))
				udm_filter = conjunction('&', hints)
		else:
			if role_specified:
				hints = []
				for school_ou in search_base.availableSchools:
					hints.append(expression('name', "-".join((pattern, school_ou))))
				if hints:
					udm_filter = conjunction('&', hints)
			else:
				## invalid pattern, ignore
				hints = []
				for role in supported_roles:
					for school_ou in search_base.availableSchools:
						hints.append(expression('name', "-".join((role, school_ou))))
				if hints:
					udm_filter = conjunction('&', hints)

		if not udm_filter:
			MODULE.error('%s.query: invalid search filter: %s' % (self.module_name, pattern,))
			return result	## empty

		udm_modules.init(ldap_user_read, ldap_position, udm_modules.get(self.udm_module_name))
		res = udm_modules.lookup(self.udm_module_name, None, ldap_user_read, base=ucr['ldap/base'],  scope='sub', filter=udm_filter)
		result['shares'] = [obj['name'] for obj in res]
		return result

	@simple_response
	def modify(self):
		"""Modify role shares
		requests.options = {}
		"""
		MODULE.info('%s.modify: options: %s' % (self.module_name, request.options,))
		pattern = request.options.get('name', '').lower()

	@LDAP_Connection(USER_READ, USER_WRITE)
	def modify_share(self, sharename, accessmode, ldap_user_read=None, ldap_user_write=None, ldap_position=None, search_base=None)):

		result = {}

		supported_accessmodes = ("none", "read", "read,write")
		if accessmode not in supported_accessmodes:
			MODULE.error('%s.modify: invalid access mode: %s' % (self.module_name, accessmode,))
			return result	## TODO: How to communicate the error?

		## sanitize the sharename to match only role shares
		search_pattern_parts = pattern.split("-", 1)
		role_specified=False
		for role in supported_roles:
			if search_pattern_parts[0] == role:
				role_specified=True
		if not role_specified:
			MODULE.error('%s.modify: sharename is not a role share: %s' % (self.module_name, sharename,))
			return result	## TODO: How to communicate the error?


		specified_school_ou=None
		if len(search_pattern_parts) == 2:
			for school_ou in search_base.availableSchools:
				if len search_pattern_parts[1] == school_ou:
					specified_school_ou=school_ou
		if not specified_school_ou:
			MODULE.error('%s.modify: sharename is not in an accessible school: %s' % (self.module_name, sharename,))
			return result	## TODO: How to communicate the error?

		udm_modules.init(ldap_user_read, ldap_position, udm_modules.get(self.udm_module_name))
		udm_filter="name=%s" % (sharename,)
		res = udm_modules.lookup(self.udm_module_name, None, ldap_user_read, base=ucr['ldap/base'],  scope='sub', filter=udm_filter)
		if not res:
			MODULE.error('%s.modify: share note found: %s' % (self.module_name, sharename,))
			return result	## TODO: How to communicate the error?

		teacher_groupname = "-".join((ucs_school_name_i18n(role_teacher), specified_school_ou))

		udm_obj = res[0]
		if accessmode == "read":
			udm_obj['sambaWriteable'] = 0
			udm_obj['group'] = grp.getgrnam(teacher_groupname).gr_gid
		elif  accessmode == "read,write":
			udm_obj['sambaWriteable'] = 1
			udm_obj['group'] = grp.getgrnam(teacher_groupname).gr_gid
		elif  accessmode == "none":
			udm_obj['sambaWriteable'] = 0
			udm_obj['group'] = grp.getgrnam('nogroup').gr_gid

		udm_obj.modify()

		return result	## TODO: How to communicate the success?

