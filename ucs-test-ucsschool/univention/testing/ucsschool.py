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

# This module (univention.testing.ucsschool) tries to import ucsschool.lib.models.
# Without absolute_import python is looking for lib.modules within THIS file which
# is obviously wrong in this case.
from __future__ import absolute_import

import tempfile
import ldap
import random
import subprocess
import univention.testing.utils as utils
import univention.testing.ucr
import univention.testing.udm as utu
import univention.testing.strings as uts
import univention.admin.uldap as udm_uldap
import univention.admin.uexceptions as udm_errors
from ldap import LDAPError
from ucsschool.lib.models import School, User, Student, Teacher, TeachersAndStaff, Staff
from ucsschool.lib.models.utils import add_stream_logger_to_schoollib

from ldap.dn import str2dn
from ucsschool.lib.models.group import BasicGroup
from ucsschool.lib.models.misc import OU, Container
from ucsschool.lib.models.utils import ucr
import univention.testing.udm as udm_test

add_stream_logger_to_schoollib()


class UCSTestSchool_Exception(Exception):
	pass
class UCSTestSchool_MissingOU(UCSTestSchool_Exception):
	pass
class UCSTestSchool_OU_Name_Too_Short(UCSTestSchool_Exception):
	pass
class UCSTestSchool_LDAP_ConnectionError(UCSTestSchool_Exception):
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


	def open_ldap_connection(self, binddn=None, bindpw=None, ldap_server=None, admin=False, machine=False):
		'''Opens a new LDAP connection using the given user LDAP DN and
		password. The connection is established to the given server or
		(if None is given) to the server defined by the UCR variable
		ldap/server/name is used.
		If admin is set to True, a connection is setup by getAdminConnection().
		If machine is set to True, a connection to the master is setup by getMachoneConnection().
		'''

		assert(not(admin and machine))

		account = utils.UCSTestDomainAdminCredentials()
		if not ldap_server:
			ldap_server = self._ucr.get('ldap/master')
		port = int(self._ucr.get('ldap/server/port', 7389))

		try:
			if admin:
				lo = udm_uldap.getAdminConnection()[0]
			elif machine:
				lo = udm_uldap.getMachineConnection(ldap_master=True)[0]
			else:
				lo = udm_uldap.access(host=ldap_server, port=port, base=self._ucr.get('ldap/base'), binddn=account.binddn, bindpw=account.bindpw, start_tls=2)
		except udm_errors.noObject:
			raise
		except LDAPError, e:
			raise UCSTestSchool_LDAP_ConnectionError('Opening LDAP connection failed: %s' % (e,))

		return lo


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


	def cleanup(self, wait_for_replication=True):
		""" Cleanup all objects created by the UCS@school test environment """
		for ou_name in self._cleanup_ou_names:
			self.cleanup_ou(ou_name, wait_for_replication=False)
		if wait_for_replication:
			utils.wait_for_replication()

	def cleanup_ou(self, ou_name, wait_for_replication=True):
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
		if self._ucr.is_true('ucsschool/ldap/district/enable'):
			oudn = 'ou=%(ou)s,ou=%(district)s,%(basedn)s' % {'ou': ou_name, 'district': ou_name[0:2], 'basedn': self._ucr.get('ldap/base')}
		else:
			oudn = 'ou=%(ou)s,%(basedn)s' % {'ou': ou_name, 'basedn': self._ucr.get('ldap/base')}
		self._remove_udm_object('container/ou', oudn)
		print '*** Purging OU %s and related objects (%s): done' % (ou_name,oudn)
		if wait_for_replication:
			utils.wait_for_replication()


	def create_ou(self, ou_name=None, name_edudc=None, name_admindc=None, displayName='', name_share_file_server=None,
				  use_cli=False, wait_for_replication=True):
		"""
		Creates a new OU with random or specified name. The function may also set a specified
		displayName. If "displayName" is None, a random displayName will be set. If "displayName"
		equals to the empty string (''), the displayName won't be set. "name_edudc" may contain
		the optional name for an educational dc slave. "name_admindc" may contain
		the optional name for an administrative dc slave. If name_share_file_server is set, the
		class share file server and the home share file server will be set.
		If use_cli is set to True, the old CLI interface is used. Otherwise the UCS@school python
		library is used.
		PLEASE NOTE: if name_edudc is set to the hostname of the master, name_edudc will be unset automatically,
					 because it's not allowed to specify the hostname of the master in any situation!

		Return value: (ou_name, ou_dn)
			ou_name: name of the created OU
			ou_dn:   DN of the created OU object
		"""
		# create random display name for OU
		charset = uts.STR_ALPHANUMDOTDASH + uts.STR_ALPHA.upper() + '()[]/,;:_#"+*@<>~ßöäüÖÄÜ$%&!     '
		if displayName is None:
			displayName = uts.random_string(length=random.randint(5, 50), charset=charset)

		# it is not allowed to set the master as name_edudc ==> resetting name_edudc
		if isinstance(name_edudc, str):
			if name_edudc.lower() == self._ucr.get('ldap/master', '').split('.',1)[0].lower():
				print '*** It is not allowed to set the master as name_edudc ==> resetting name_edudc'
				name_edudc = None

		# create random OU name
		if not ou_name:
			ou_name = uts.random_string(length=random.randint(3, 12))

		# remember OU name for cleanup
		self._cleanup_ou_names.add(ou_name)

		if not use_cli:
			kwargs = {'name': ou_name,
					  'dc_name': name_edudc
					  }
			if name_admindc:
				kwargs['dc_name_administrative'] = name_admindc
			if name_share_file_server:
				kwargs['class_share_file_server'] = name_share_file_server
				kwargs['home_share_file_server'] = name_share_file_server
			if displayName:
				kwargs['display_name'] = displayName

			print '*** Creating new OU %r' % (ou_name,)
			lo = self.open_ldap_connection()
			School.invalidate_all_caches()
			School.init_udm_module(lo) # TODO FIXME has to be fixed in ucs-school-lib - should be done automatically
			result = School(**kwargs).create(lo)
			print '*** Result of School(...).create(): %r' % (result,)
		else:
			# build command line
			cmd = [self.PATH_CMD_CREATE_OU]
			if displayName:
				cmd += ['--displayName', displayName]
			cmd += [ou_name]
			if name_edudc:
				cmd += [name_edudc]

			print '*** Calling following command: %r' % cmd
			retval = subprocess.call(cmd)
			if retval:
				utils.fail('create_ou failed with exitcode %s' % retval)

		if wait_for_replication:
			utils.wait_for_replication()

		ou_dn = 'ou=%s,%s' % (ou_name, self.LDAP_BASE)
		return ou_name, ou_dn


	def get_district(self, ou_name):
		try:
			return ou_name[:2]
		except IndexError:
			raise UCSTestSchool_OU_Name_Too_Short('The OU name "%s" is too short for district mode' % ou_name)


	def get_ou_base_dn(self, ou_name):
		"""
		Returns the LDAP DN for the given school OU name (the district mode will be considered).
		"""
		dn = '%(school)s,%(district)s%(basedn)s'
		values = {'school':'ou=%s' % ou_name,
				  'district':'',
				  'basedn': self.LDAP_BASE,
				  }
		if self._ucr.is_true('ucsschool/ldap/district/enable'):
			values['district'] = 'ou=%s,' % self.get_district(ou_name)
		return dn % values


	def get_user_container(self, ou_name, is_teacher=False, is_staff=False):
		"""
		Returns user container for specified user role and ou_name.
		"""
		if is_teacher and is_staff:
			return 'cn=%s,cn=users,%s' % (self.CN_TEACHERS_STAFF, self.get_ou_base_dn(ou_name))
		if is_teacher:
			return 'cn=%s,cn=users,%s' % (self.CN_TEACHERS, self.get_ou_base_dn(ou_name))
		if is_staff:
			return 'cn=%s,cn=users,%s' % (self.CN_STAFF, self.get_ou_base_dn(ou_name))
		return 'cn=%s,cn=users,%s' % (self.CN_STUDENT, self.get_ou_base_dn(ou_name))


	def get_workinggroup_dn(self, ou_name, group_name):
		"""
		Return the DN of the specified working group.
		"""
		return 'cn=%s-%s,cn=schueler,cn=groups,%s' % (ou_name, group_name, self.get_ou_base_dn(ou_name))


	def get_workinggroup_share_dn(self, ou_name, group_name):
		"""
		Return the DN of the share object for the specified working group.
		"""
		return 'cn=%s-%s,cn=shares,%s' % (ou_name, group_name, self.get_ou_base_dn(ou_name))


	def create_user(self, ou_name, username=None, firstname=None, lastname=None, classes=None,
					mailaddress=None, is_teacher=False, is_staff=False, is_active=True, password='univention',
					use_cli=False, wait_for_replication=True):
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

		user_dn = 'uid=%s,%s' % (username, self.get_user_container(ou_name, is_teacher, is_staff))
		if use_cli:
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

			if password is not None:
				self._set_password(user_dn, password)
		else:
			kwargs = {
				'school': ou_name,
				'name': username,
				'firstname': firstname,
				'lastname': lastname,
				'email': mailaddress,
				'password': password,
				'disabled': not(is_active),
				}
			print '*** Creating new user %r' % (username,)
			lo = self.open_ldap_connection()
			User.invalidate_all_caches()
			User.init_udm_module(lo) # TODO FIXME has to be fixed in ucs-school-lib - should be done automatically
			if is_teacher and is_staff:
				result = TeachersAndStaff(**kwargs).create(lo)
			elif is_teacher and not is_staff:
				result = Teacher(**kwargs).create(lo)
			elif not is_teacher and is_staff:
				result = Staff(**kwargs).create(lo)
			else:
				result = Student(**kwargs).create(lo)
			print '*** Result of User(...).create(): %r' % (result,)

		if wait_for_replication:
			utils.wait_for_replication()

		return username, user_dn

	def create_school_admin(self, ou_name):
		position = 'cn=admins,cn=users,%s' % (self.get_ou_base_dn(ou_name))
		groups = ["cn=admins-%s,cn=ouadmins,cn=groups,%s" % (ou_name, self.LDAP_BASE)]
		udm = udm_test.UCSTestUDM()
		dn, school_admin = udm.create_user(position=position, groups=groups)
		return dn, school_admin

	def create_domain_admin(self, ou_name):
		position = 'cn=admins,cn=users,%s' % (self.get_ou_base_dn(ou_name))
		groups = ["cn=Domain Admins,cn=groups,%s" % (self.LDAP_BASE,)]
		udm = udm_test.UCSTestUDM()
		dn, domain_admin = udm.create_user(position=position, groups=groups)
		return dn, domain_admin

	def create_global_user(self):
		position = 'cn=users,%s' % (self.LDAP_BASE,)
		# groups = ["cn=admins-%s,cn=ouadmins,cn=groups,%s" % (ou_name, self.LDAP_BASE)]
		udm = udm_test.UCSTestUDM()
		dn, global_user = udm.create_user(position=position, groups=[])
		return dn, global_user

	def create_computerroom(self, ou_name, name=None, description=None, host_members=[], wait_for_replication=True):
		"""
		Create a room in specified OU with given attributes. If attributes are not specified, random
		values will be used for roomname and description.

		Return value: (room_name, room_dn)
			room_name: name of the created room
			room_dn:   DN of the created room object
		"""
		if not ou_name:
			raise UCSTestSchool_MissingOU('No OU name specified')

		# set default values
		if name is None:
			name = uts.random_name()
		if description is None:
			description = uts.random_string(length=10, numeric=False)

		kwargs = {
			'school': ou_name,
			'name': name,
			'description': description
			}
		print '*** Creating new room %r' % (name,)
		lo = self.open_ldap_connection()
		obj = ComputerRoom(**kwargs)
		result = obj.create(lo)
		print '*** Result of ComputerRoom(...).create(): %r' % (result,)
		udm_obj = obj.get_udm_object(lo)
		udm_obj['hosts'] = host_members
		result = udm_obj.modify()
		print '*** Result of ComputerRoom(...).modify(): %r' % (result,)
		if wait_for_replication:
			utils.wait_for_replication()
		return name, result


class ComputerRoom(BasicGroup):

	def __init__(self, name=None, school=None, **kwargs):
		self.ou = school
		self.name = name
		if 'container' not in kwargs:
			kwargs['container'] = 'cn=raeume,cn=groups,%s' % UCSTestSchool().get_ou_base_dn(self.ou)
		# super(ComputerRoom, self).__init__(name=self.name, school=self.ou, **kwargs)
		super(ComputerRoom, self).__init__(name='%s-%s' % (self.ou,name), school=self.ou, **kwargs)

	def create_without_hooks(self, lo, validate):
		# prepare LDAP: create containers where this basic group lives if necessary
		container_dn = self.get_own_container()[:-len(ucr.get('ldap/base'))-1]
		containers = str2dn(container_dn)
		super_container_dn = ucr.get('ldap/base')
		for container_info in reversed(containers):
			dn_part, cn = container_info[0][0:2]
			if dn_part.lower() == 'ou':
				container = OU(name=cn)
			else:
				container = Container(name=cn, school=self.ou, group_path='1')
			super_container_dn = container.create_in_container(super_container_dn, lo)
		return super(ComputerRoom, self).create_without_hooks(lo, validate)

	def create(self, lo):
		self.create_without_hooks(lo, True)
		return 'cn=%s,%s' % (self.name, self.get_own_container())


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
