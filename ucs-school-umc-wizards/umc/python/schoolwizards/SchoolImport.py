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

_ = Translation('ucs-school-umc-wizards').translate

class SchoolImport():
	"""Wrapper for the ucs-school-import script
	"""
	_SCRIPT_PATH = '/usr/share/ucs-school-import/scripts'
	USER_SCRIPT = '%s/import_user' % _SCRIPT_PATH
	SCHOOL_SCRIPT = '%s/create_ou' % _SCRIPT_PATH
	GROUP_SCRIPT = '%s/import_group' % _SCRIPT_PATH
	COMPUTER_SCRIPT = '%s/import_computer' % _SCRIPT_PATH

	def _run_script(self, script, entry, run_with_string_argument=False):
		"""Executes the script with given entry
		"""
		# Replace `True` with 1 and `False` with 0
		entry = [{True: 1, False: 0, } .get(x, x) for x in entry]

		if run_with_string_argument:
			entry.insert(0, script)
			try:
				process = subprocess.Popen(entry, stdout=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if stdout and process.returncode > 0:
					MODULE.warn(stdout)
			except (OSError, ValueError) as err:
				MODULE.warn(str(err))
				raise UMC_CommandError(_('Execution of command failed'))
			else:
				return process.returncode
		else:
			# Separate columns by tabs
			entry = '\t'.join(['%s' % column for column in entry])
			try:
				tmpfile = tempfile.NamedTemporaryFile()
				tmpfile.write(entry)
				tmpfile.flush()
				process = subprocess.Popen([script, tmpfile.name], subprocess.PIPE)
				stdout, stderr = process.communicate()
				if stdout and process.returncode > 0:
					MODULE.warn(stdout)
			except (OSError, ValueError) as err:
				MODULE.warn(str(err))
				raise UMC_CommandError(_('Execution of command failed'))
			else:
				return process.returncode
			finally:
				tmpfile.close()

	def import_user(self, username, lastname, firstname, school, class_,
	                mail_primary_address, teacher, staff, password):
		"""Imports a new user
		"""
		class_ = '%s-%s' % (school, class_)
		entry = ['A', username, lastname, firstname, school, class_, '',
		         mail_primary_address, teacher, True, staff, password, ]

		return_code = self._run_script(SchoolImport.USER_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create user'))

	def create_ou(self, name, school_dc):
		"""Creates a new school
		"""
		return_code = self._run_script(SchoolImport.SCHOOL_SCRIPT, [name, school_dc, ], True)
		if return_code:
			raise OSError(_('Could not create school'))

	def import_group(self, school, name, description):
		"""Creates a new class
		"""
		name = '%s-%s' % (school, name)
		entry = ['A', school, name, description, ]

		return_code = self._run_script(SchoolImport.GROUP_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create class'))

	def import_computer(self, type_, name, mac, school, ip_address, subnet_mask, inventory_number):
		"""Imports a new computer
		"""
		if subnet_mask:
			address = '%s/%s' % (ip_address, subnet_mask)
		else:
			address = ip_address

		entry = [type_, name, mac, school, address, inventory_number, ]

		return_code = self._run_script(SchoolImport.COMPUTER_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create computer'))

