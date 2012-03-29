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

import tempfile
import subprocess

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_CommandError
import univention.admin.modules as udm_modules

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_Filter

_ = Translation('ucs-school-umc-wizards').translate

class SchoolImport(object):
	"""Wrapper for the ucs-school-import script
	"""
	_SCRIPT_PATH = '/usr/share/ucs-school-import/scripts'
	USER_SCRIPT = '%s/import_user' % _SCRIPT_PATH

	def _run_script(self, script, entry):
		"""Executes the script with given entry
		"""
		# Replace `True` with 1 and `False` with 0
		entry = [{True: 1, False: 0, } .get(x, x) for x in entry]
		# Separate columns by tabs
		entry = '\t'.join(['%s' % column for column in entry])

		try:
			tmpfile = tempfile.NamedTemporaryFile()
			tmpfile.write(entry)
			tmpfile.flush()
			return_code = subprocess.call([script, tmpfile.name])
		except IOError, err:
			MODULE.info(str(err))
			raise UMC_CommandError(_('Execution of command failed'))
		else:
			return return_code
		finally:
			tmpfile.close()

	@LDAP_Connection()
	def _username_used(self, username, search_base=None,
	                   ldap_user_read=None, ldap_position=None):
		ldap_filter = LDAP_Filter.forAll(username, ['username'])
		user_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                 scope = 'sub', filter = ldap_filter)
		return bool(user_exists)

	@LDAP_Connection()
	def _mail_address_used(self, address, search_base=None,
	                       ldap_user_read=None, ldap_position=None):
		ldap_filter = LDAP_Filter.forAll(address, ['mailPrimaryAddress'])
		address_exists = udm_modules.lookup('users/user', None, ldap_user_read,
		                                    scope = 'sub', filter = ldap_filter)
		return bool(address_exists)

	def import_user(self, username, lastname, firstname, school, class_,
	                mailPrimaryAddress, teacher, staff):
		"""Imports a new user
		"""
		MODULE.info('#### user: %s' % str(username))

		if self._username_used(username):
			raise ValueError(_('Username is already in use'))
		if mailPrimaryAddress:
			if self._mail_address_used(mailPrimaryAddress):
				raise ValueError(_('Mail address is already in use'))

		entry = ['A', username, lastname, firstname, school, class_, '',
		         mailPrimaryAddress, teacher, True, staff, ]

		return_code = self._run_script(SchoolImport.USER_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create user'))
