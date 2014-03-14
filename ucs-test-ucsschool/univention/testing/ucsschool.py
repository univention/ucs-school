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

import tempfile
import ldap
import random
import subprocess
import univention.testing.utils as utils
import univention.testing.ucr
import univention.testing.udm as utu
import univention.testing.strings as uts

class UCSTestSchool_Exception(Exception):
	pass
class UCSTestSchool_MissingOU(UCSTestSchool_Exception):
	pass
class UCSTestSchool_OU_Name_Too_Short(UCSTestSchool_Exception):
	pass


class UCSTestSchool(object):
	_lo = utils.get_ldap_connection()
	_ucr = univention.testing.ucr.UCSTestConfigRegistry()
	_ucr.load()

	LDAP_BASE = _ucr['ldap/base']

	PATH_CMD_BASE = '/usr/share/ucs-school-import/scripts'
	PATH_CMD_CREATE_OU = PATH_CMD_BASE + '/create_ou'
	PATH_CMD_IMPORT_USER = PATH_CMD_BASE + '/import_user'

	CN_STUDENT = _ucr.get('ucsschool/ldap/default/container/pupils', 'schueler')
	CN_TEACHERS = _ucr.get('ucsschool/ldap/default/container/teachers', 'lehrer')
	CN_TEACHERS_STAFF = _ucr.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
	CN_ADMINS = _ucr.get('ucsschool/ldap/default/container/admins', 'admins')
	CN_STAFF = _ucr.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')


	def __init__(self):
		self._cleanup_ou_names = set()


	def __enter__(self):
		return self


	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type:
			print '*** Cleanup after exception: %s %s' % (exc_type, exc_value)
		self.cleanup()


	def _remove_udm_object(self, module, dn, raise_exceptions=False):
		"""
			Tries to remove UDM object specified by given dn.
			Return None on success or error message.
		"""
		try:
			dn = self._lo.searchDn(base=dn)[0]
		except (ldap.NO_SUCH_OBJECT, IndexError):
			if raise_exceptions:
				raise
			return 'missing object'

		msg = None
		cmd = [utu.UCSTestUDM.PATH_UDM_CLI_CLIENT_WRAPPED, module, 'remove', '--dn', dn]
		print '*** Calling following command: %r' % cmd
		retval = subprocess.call(cmd)
		if retval:
			msg = '*** ERROR: failed to remove UCS@school %s object: %s' % (module, dn)
			print msg
		return msg


	def _set_password(self, userdn, password, raise_exceptions=False):
		"""
			Tries to set a password for the given user.
			Return None on success or error message.
		"""
		try:
			dn = self._lo.searchDn(base=userdn)[0]
		except (ldap.NO_SUCH_OBJECT, IndexError):
			if raise_exceptions:
				raise
			return 'missing object'

		msg = None
		cmd = [utu.UCSTestUDM.PATH_UDM_CLI_CLIENT_WRAPPED, 'users/user', 'modify', '--dn', dn, '--set', 'password=%s' % password]
		print '*** Calling following command: %r' % cmd
		retval = subprocess.call(cmd)
		if retval:
			msg = 'ERROR: failed to set password for UCS@school user %s' % (userdn)
			print msg
		return msg


	def cleanup(self):
		""" Cleanup all objects created by the UCS@school test environment """
		for ou_name in self._cleanup_ou_names:

			self.cleanup_ou(ou_name)


	def cleanup_ou(self, ou_name):
		""" Removes the given school ou and all its corresponding objects like groups """

		print '*** Purging OU %s and related objects' % ou_name
		# remove OU specific groups
		for grpdn in ('cn=OU%(ou)s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s',
					  'cn=OU%(ou)s-Member-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s',
					  'cn=OU%(ou)s-Klassenarbeit,cn=ucsschool,cn=groups,%(basedn)s',
					  'cn=OU%(ou)s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s',
					  'cn=OU%(ou)s-DC-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s',
					  'cn=admins-%(ou)s,cn=ouadmins,cn=groups,%(basedn)s',
					  ):
			grpdn = grpdn % {'ou': ou_name, 'basedn': self._ucr.get('ldap/base')}
			self._remove_udm_object('groups/group', grpdn)

		# remove OU recursively
		oudn = 'ou=%(ou)s,%(basedn)s' % {'ou': ou_name, 'basedn': self._ucr.get('ldap/base')}
		self._remove_udm_object('container/ou', oudn)
		print '*** Purging OU %s and related objects: done' % ou_name


	def create_ou(self, ou_name=None, name_edudc=None, displayName=None):
		"""
		Creates a new OU with random or specified name. The function also sets a random display name
		if no display name has been specified. name_edudc may contain the optional name for an
		educational dc slave.

		Return value: (ou_name, ou_dn)
			ou_name: name of the created OU
			ou_dn:   DN of the created OU object
		"""
		# create random display name for OU
		charset = uts.STR_ALPHANUMDOTDASH + uts.STR_ALPHA.upper() + '()[]/,;:_#"+*@<>~ßöäüÖÄÜ$%&!     '
		if displayName is None:
			displayName = uts.random_string(length=random.randint(5, 50), charset=charset)
			ou_displayName = displayName

		# create random OU name
		if not ou_name:
			ou_name = uts.random_string(length=random.randint(3, 12))

		# remember OU name for cleanup
		self._cleanup_ou_names.add(ou_name)

		# build command line
		cmd = [self.PATH_CMD_CREATE_OU]
		if displayName:
			cmd += ['--displayName', ou_displayName]
		cmd += [ou_name]
		if name_edudc:
			cmd += [name_edudc]

		print '*** Calling following command: %r' % cmd
		retval = subprocess.call(cmd)
		if retval:
			utils.fail('create_ou failed with exitcode %s' % retval)

		ou_dn = 'ou=%s,%s' % (ou_name, self.LDAP_BASE)
		return ou_name, ou_dn


	def _get_district(self, ou_name):
		try:
			return ou_name[:2]
		except IndexError:
			raise UCSTestSchool_OU_Name_Too_Short('The OU name "%s" is too short for district mode' % ou_name)


	def _get_ou_base_dn(self, ou_name):
		"""
		Returns the LDAP DN for the given school OU name (the district mode will be considered).
		"""
		dn = '%(school)s,%(district)s%(basedn)s'
		values = {'school':'ou=%s' % ou_name,
				  'district':'',
				  'basedn': self.LDAP_BASE,
				  }
		if self._ucr.is_true('ucsschool/ldap/district/enable'):
			values['district'] = 'ou=%s,' % self._get_district(ou_name)
		return dn % values


	def _get_user_container(self, ou_name, is_teacher=False, is_staff=False):
		"""
		Returns user container for specified user role and ou_name.
		"""
		if is_teacher and is_staff:
			return 'cn=%s,cn=users,%s' % (self.CN_TEACHERS_STAFF, self._get_ou_base_dn(ou_name))
		if is_teacher:
			return 'cn=%s,cn=users,%s' % (self.CN_TEACHERS, self._get_ou_base_dn(ou_name))
		if is_staff:
			return 'cn=%s,cn=users,%s' % (self.CN_STAFF, self._get_ou_base_dn(ou_name))
		return 'cn=%s,cn=users,%s' % (self.CN_STUDENT, self._get_ou_base_dn(ou_name))


	def create_user(self, ou_name, username=None, firstname=None, lastname=None, classes=None,
					mailaddress=None, is_teacher=False, is_staff=False, is_active=True, password='univention'):
		"""
		Create a user in specified OU with given attributes. If attributes are not specified, random
		values will be used for username, firstname and lastname. If password is not None, the given
		password will be set for this user.

		Return value: (user_name, user_dn)
			user_name: name of the created user
			user_dn:   DN of the created user object
		"""
		if not ou_name:
			raise UCSTestSchool_MissingOU('No OU name specified')

		# set default values
		if username is None:
			username = uts.random_username()
		if firstname is None:
			firstname = uts.random_string(length=10, numeric=False)
		if lastname is None:
			lastname = uts.random_string(length=10, numeric=False)
		if classes is None:
			classes = ''
		if mailaddress is None:
			mailaddress = ''

		# create import file
		line = 'A\t%s\t%s\t%s\t%s\t%s\t\t%s\t%d\t%d\t%d\n' % (username, lastname, firstname, ou_name, classes,
															mailaddress, int(is_teacher), int(is_active), int(is_staff))
		with tempfile.NamedTemporaryFile() as tmp_file:
			tmp_file.write(line)
			tmp_file.flush()

			cmd = [self.PATH_CMD_IMPORT_USER, tmp_file.name]
			print '*** Calling following command: %r' % cmd
			retval = subprocess.call(cmd)
			if retval:
				utils.fail('create_ou failed with exitcode %s' % retval)

		user_dn = 'uid=%s,%s' % (username, self._get_user_container(ou_name, is_teacher, is_staff))

		if password is not None:
			self._set_password(user_dn, password)

		return username, user_dn



if __name__ == '__main__':
	with UCSTestSchool() as schoolenv:
		# create ou
		ou_name, ou_dn = schoolenv.create_ou(displayName='') # FIXME: displayName has been disabled for backward compatibility
		print 'NEW OU'
		print '  ', ou_name
		print '  ', ou_dn
		# create user
		user_name, user_dn = schoolenv.create_user(ou_name)
		print 'NEW USER'
		print '  ', user_name
		print '  ', user_dn
		# create user
		user_name, user_dn = schoolenv.create_user(ou_name, is_teacher=True)
		print 'NEW USER'
		print '  ', user_name
		print '  ', user_dn
		# create user
		user_name, user_dn = schoolenv.create_user(ou_name, is_staff=True)
		print 'NEW USER'
		print '  ', user_name
		print '  ', user_dn
		# create user
		user_name, user_dn = schoolenv.create_user(ou_name, is_teacher=True, is_staff=True)
		print 'NEW USER'
		print '  ', user_name
		print '  ', user_dn
