#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  Wizards
#
# Copyright 2012-2014 Univention GmbH
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


class SchoolImport(object):

	"""Wrapper for the ucs-school-import script
	"""
	_SCRIPT_PATH = '/usr/share/ucs-school-import/scripts'
	USER_SCRIPT = '%s/import_user' % _SCRIPT_PATH
	SCHOOL_SCRIPT = '%s/create_ou' % _SCRIPT_PATH
	GROUP_SCRIPT = '%s/import_group' % _SCRIPT_PATH
	COMPUTER_SCRIPT = '%s/import_computer' % _SCRIPT_PATH
	MOVE_DC_SCRIPT = '%s/move_domaincontroller_to_ou' % _SCRIPT_PATH

	def _run_script(self, script, entry, run_with_string_argument=False):
		"""Executes the script with given entry
		"""
		# Replace `True` with 1 and `False` with 0
		entry = [{True: 1, False: 0, } .get(x, x) for x in entry]

		if run_with_string_argument:
			entry.insert(0, script)
			try:
				MODULE.process('Executing command: %s' % ' '.join(entry))
				process = subprocess.Popen(entry, stdout=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if stdout and process.returncode > 0:
					MODULE.warn(stdout)
			except (OSError, ValueError) as err:
				MODULE.warn(str(err))
				raise UMC_CommandError(_('Execution of command failed'))
			else:
				return process.returncode, stdout
		else:
			# Separate columns by tabs
			entry = '\t'.join(['%s' % column for column in entry])
			try:
				tmpfile = tempfile.NamedTemporaryFile()
				tmpfile.write(entry)
				tmpfile.flush()
				MODULE.process('Executing command: %s' % script)
				process = subprocess.Popen([script, tmpfile.name], stdout=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if stdout:
					info = '\n'.join([line for line in stdout.splitlines() if not line.startswith('Processing line ')])
					MODULE.process(info)
			except (OSError, ValueError) as err:
				MODULE.warn(str(err))
				raise UMC_CommandError(_('Execution of command failed'))
			else:
				return process.returncode, stdout
			finally:
				tmpfile.close()
		return None, None

	def import_user(self, username, lastname, firstname, school, class_,
	                mail_primary_address, teacher, staff, password):
		"""Imports a new user
		"""
		entry = ['A', username, lastname, firstname, school, class_, '',
		         mail_primary_address, teacher, True, staff, password, ]

		return_code, stdout = self._run_script(SchoolImport.USER_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create user'))

	def import_group(self, school, name, description):
		"""Creates a new class
		"""
		name = '%s-%s' % (school, name)
		entry = ['A', school, name, description, ]

		return_code, stdout = self._run_script(SchoolImport.GROUP_SCRIPT, entry)
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

		return_code, stdout = self._run_script(SchoolImport.COMPUTER_SCRIPT, entry)
		if return_code:
			raise OSError(_('Could not create computer'))
