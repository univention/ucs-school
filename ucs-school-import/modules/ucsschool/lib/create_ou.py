# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2018-2019 Univention GmbH
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

"""
Temporary class and function to create an OU using shell hooks.
Remove once Bug #48141 has been fixed.
Used by create_ou script and customer single user HTTP API.
"""

import os
import sys
import subprocess
import tempfile
import logging
from ucsschool.lib.models.school import School
import univention.config_registry
from ldap.filter import filter_format

config_registry = univention.config_registry.ConfigRegistry()
config_registry.load()
_hooks = None


# TODO: REMOVE WITH Bug #48141
class Hooks(object):
	OBJECTS = ('user', 'group', 'printer', 'computer', 'network', 'router', 'ou')
	OPERATIONS = {'A': 'create', 'M': 'modify', 'D': 'remove'}

	PATH = '/usr/share/ucs-school-import/hooks/'

	def _create_temp_file(self, line):
		tmpfile = tempfile.NamedTemporaryFile()
		tmpfile.write(line)
		tmpfile.flush()
		return tmpfile

	def __run(self, phase, module, action, **kwargs):
		# verify phase
		if action not in Hooks.OPERATIONS:
			return False

		# verify path
		path = os.path.join(Hooks.PATH, '%s_%s_%s.d' % (module, Hooks.OPERATIONS[action], phase))
		if not os.path.isdir(path) or not os.listdir(path):
			return False

		# create temporary file with data
		if 'line' in kwargs:
			kwargs['line'] = kwargs['line'].strip() + "\n"
			tmpfile = self._create_temp_file(kwargs.get('line'))

		# invoke hook scripts
		# <script> <temporary file> [<ldap dn>]
		command = ['run-parts', path]
		if 'line' in kwargs:
			command.extend(('--arg', tmpfile.name))
		if 'dn' in kwargs:
			command.extend(('--arg', kwargs['dn']))

		sys.stdout.flush()
		sys.stderr.flush()
		ret_code = subprocess.call(command)

		# close temporary file (also deletes the file)
		if 'line' in kwargs:
			tmpfile.close()

		return ret_code == 0

	def pre(self, module, action, **kwargs):
		return self.__run('pre', module, action, **kwargs)

	def post(self, module, action, **kwargs):
		return self.__run('post', module, action, **kwargs)


def create_ou(ou_name, display_name, edu_name, admin_name, share_name, lo, baseDN, hostname, is_single_master):
	"""Raises ValueError, uidAlreadyUsed"""
	global _hooks
	# TODO: REMOVE WITH Bug #48141
	if not _hooks:
		_hooks = Hooks()
	hooks = _hooks

	# invoke pre hooks
	if edu_name:
		dccn = edu_name
	else:
		dccn = ''
	myline = '%s\t%s' % (ou_name, dccn)
	hooks.pre('ou', 'A', line=myline)

	if not edu_name and is_single_master:
		edu_name = hostname
	elif not edu_name and not is_single_master:
		edu_name = 'dc{}-01'.format(ou_name)

	if display_name is None:
		display_name = ou_name

	logger = logging.getLogger(__name__)

	new_school = School(name=ou_name, dc_name=edu_name, dc_name_administrative=admin_name,
						display_name=display_name)

	# TODO: Reevaluate this validation after CNAME changes are implemented
	share_dn = ''
	if share_name is None:
		share_name = edu_name
	objects = lo.searchDn(filter='(&(objectClass=univentionHost)(cn={}))'.format(share_name), base=baseDN)
	if not objects:
		if share_name == 'dc{}-01'.format(ou_name) or (edu_name and share_name == edu_name):
			share_dn = filter_format('cn=%s,cn=dc,cn=server,cn=computers,%s', [share_name, new_school.dn])
		else:
			logger.warn(
				'WARNING: share file server name %r not found! Using %r as share file server.',
				share_name, config_registry.get('hostname'))
			share_dn = config_registry.get('ldap/hostdn')
	else:
		share_dn = objects[0]

	new_school.class_share_file_server = share_dn
	new_school.home_share_file_server = share_dn

	new_school.validate(lo)
	if len(new_school.warnings) > 0:
		logger.warn('The following fields reported warnings during validation:')
		for key, value in new_school.warnings.items():
			logger.warn('%s: %s', key, value)
	if len(new_school.errors) > 0:
		error_str = 'The following fields reported errors during validation:\n'
		for key, value in new_school.errors.items():
			error_str += '{}: {}\n'.format(key, value)
		raise ValueError(error_str)
	new_school.create(lo)
	if new_school.exists(lo):
		logger.info('OU %r exists', new_school.name)
		# TODO: REMOVE WITH Bug #48141
		# invoke post hooks
		# for OUs the temporary file contains the LDAP DN
		hooks.post('ou', 'A', dn=new_school.dn, line=myline)
