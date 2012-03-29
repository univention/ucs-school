#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  Wizards
#
# Copyright 2012 Univention GmbH
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
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_OptionMissing, UMC_CommandError, UMC_OptionTypeError
from univention.management.console.protocol.definitions import *
import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import SchoolBaseModule, LDAP_Connection, LDAP_Filter, USER_READ

from SchoolImport import *

_ = Translation('ucs-school-umc-wizards').translate

class Instance(SchoolBaseModule, SchoolImport):
	"""Base class for the schoolwizards UMC module.
	"""
	def required_values(self, request, *keys):
		missing = filter(lambda key: '' == request.options[key], keys)
		if missing:
			raise ValueError(_('Missing value for the following properties: %s')
			                 % ','.join(missing))

	def create_user(self, request):
		"""Create a new user.
		"""
		MODULE.info('schoolwizards/users/create: options: %s' % str(request.options))

		try:
			# Validate request options
			keys = ['username', 'lastname', 'firstname', 'school', 'class', 'type']
			self.required_options(request, *keys)
			self.required_values(request, *keys)

			isTeacher = False
			isStaff = False
			if request.options['type'] not in ['student', 'teacher', 'staff', 'staffAndTeacher']:
				raise ValueError(_('Invalid value for  \'type\' property'))
			if request.options['type'] == 'teacher':
				isTeacher = True
			elif request.options['type'] == 'staff':
				isStaff = True
			elif request.options['type'] == 'staffAndTeacher':
				isStaff = True
				isTeacher = True

			# Create the user
			self.import_user(request.options['username'],
			                 request.options['lastname'],
			                 request.options['firstname'],
			                 request.options['school'],
			                 request.options['class'],
			                 request.options.get('mailPrimaryAddress', ''),
			                 isTeacher,
			                 isStaff)
		except (ValueError, IOError, OSError), err:
			MODULE.info(str(err))
			result = {'successs': False, 'message': str(err)}
			self.finished(request.id, result)
		else:
			self.finished(request.id, None, _('User successfully created'))
