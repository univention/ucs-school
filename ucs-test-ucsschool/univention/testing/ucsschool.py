# -*- coding: utf-8 -*-
#
# UCS test
"""
API for testing UCS@school and cleaning up after performed tests
"""
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

import ldap
import subprocess
import univention.testing.utils as utils
import univention.testing.ucr
import univention.testing.udm as utu

def remove_udm_object(module, dn, fail_if_missing=False):
	"""
		Tries to remove UDM object specified by given dn.
		Return None on success or error message.
	"""
	try:
		dn = utils.get_ldap_connection().searchDn(base=dn)[0]
	except (ldap.NO_SUCH_OBJECT, IndexError):
		if fail_if_missing:
			raise
		return 'missing object'

	msg = None
	cmd = [ utu.UCSTestUDM.PATH_UDM_CLI_CLIENT_WRAPPED, module, 'remove', '--dn', dn ]
	retval = subprocess.call(cmd)
	if retval:
		msg = 'ERROR: failed to remove UCS@school %s object: %s' % (module, dn)
		print msg
	return msg


def cleanup_ou(ou_name):
	""" Removes the given school ou and all it's corresponding objects like groups """

	ucr = univention.testing.ucr.UCSTestConfigRegistry()
	ucr.load()

	print '*** Purging OU %s and related objects' % ou_name
	# remove OU specific groups
	for grpdn in ('cn=OU%(ou)s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s',
				  'cn=OU%(ou)s-Member-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s',
				  'cn=OU%(ou)s-Klassenarbeit,cn=ucsschool,cn=groups,%(basedn)s',
				  'cn=OU%(ou)s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s',
				  'cn=OU%(ou)s-DC-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s',
				  'cn=admins-%(ou)s,cn=ouadmins,cn=groups,%(basedn)s',
				  ):
		grpdn = grpdn % { 'ou': ou_name, 'basedn': ucr.get('ldap/base') }
		remove_udm_object('groups/group', grpdn)

	# remove OU recursively
	oudn = 'ou=%(ou)s,%(basedn)s' % { 'ou': ou_name, 'basedn': ucr.get('ldap/base') }
	remove_udm_object('container/ou', oudn)
	print '*** Purging OU %s and related objects: done' % ou_name
