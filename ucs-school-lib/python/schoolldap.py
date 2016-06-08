#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2016 Univention GmbH
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

import univention.config_registry
import univention.uldap
import univention.admin.config
import univention.admin.modules

import univention.admin.modules as udm_modules
from univention.management.console.protocol.message import Message

from univention.lib.i18n import Translation

from functools import wraps
import re
import inspect
from ldap.filter import escape_filter_chars

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.ldap import get_machine_connection, get_admin_connection, get_user_connection#, reset_cache as reset_connection_cache
from univention.management.console.modules import Base, UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer

# load UDM modules
udm_modules.update()

__bind_callback = None

_ = Translation('python-ucs-school').translate

def set_bind_function(bind_callback):
	global __bind_callback
	__bind_callback = bind_callback

def set_credentials(dn, passwd):
	set_bind_function(lambda lo: lo.lo.bind(dn, passwd))

USER_READ = 'ldap_user_read'
USER_WRITE = 'ldap_user_write'
MACHINE_READ = 'ldap_machine_read'
MACHINE_WRITE = 'ldap_machine_write'
ADMIN_WRITE = 'ldap_admin_write'


def LDAP_Connection(*connection_types):
	"""This decorator function provides access to internally cached LDAP connections that can
	be accessed via adding specific keyword arguments to the function.

	The function which uses this decorator may specify the following additional keyword arguments:
	ldap_position: a univention.admin.uldap.position instance valid ldap position.
	ldap_user_read: a read only LDAP connection to the local LDAP server authenticated with the currently used user
	ldap_user_write: a read/write LDAP connection to the master LDAP server authenticated with the currently used user
	ldap_machine_read: a read only LDAP connection to the local LDAP server authenticated with the machine account
	ldap_machine_write: a read/write LDAP connection to the master LDAP server authenticated with the machine account
	ldap_admin_write: a read/write LDAP connection to the master LDAP server authenticated with cn=admin account
	(deprecated!) search_base: a SchoolSearchBase instance which is bound to the school of the user or machine.

	This decorator can only be used after set_bind_function() has been executed.

	example:
	  @LDAP_Connection()
	  def do_ldap_stuff(arg1, arg2, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		  ...
		  ldap_user_read.searchDn(..., position=ldap_position)
		  ...
	"""

	if not connection_types:  # TODO: remove. We still need this for backwards compatibility with other broken decorators
		connection_types = (USER_READ,)

	def inner_wrapper(func):
		argspec = inspect.getargspec(func)
		argnames = set(argspec.args) | set(connection_types)
		add_search_base = 'search_base' in argspec.args or argspec.keywords is not None
		add_position = 'ldap_position' in argspec.args or argspec.keywords is not None

		def wrapper_func(*args, **kwargs):
			# set LDAP keyword arguments
			po = None
			if ADMIN_WRITE in argnames:
				kwargs[ADMIN_WRITE], po = get_admin_connection()
			if MACHINE_WRITE in argnames:
				kwargs[MACHINE_WRITE], po = get_machine_connection(write=True)
			if MACHINE_READ in argnames:
				kwargs[MACHINE_READ], po = get_machine_connection(write=False)
			if USER_WRITE in argnames:
				kwargs[USER_WRITE], po = get_user_connection(bind=__bind_callback, write=True)
			if USER_READ in argnames:
				kwargs[USER_READ], po = get_user_connection(bind=__bind_callback, write=False)
			if add_position:
				kwargs['ldap_position'] = po
			if add_search_base:
				MODULE.warn('Using deprecated LDAP_Connection.search_base parameter.')
				from ucsschool.lib.models import School
				if len(args) > 1 and isinstance(args[1], Message) and isinstance(args[1].options, dict) and args[1].options.get('school'):
					school = args[1].options['school']
				elif LDAP_Connection._school is None:
					lo = kwargs.get(USER_READ) or kwargs.get(USER_WRITE) or kwargs.get(MACHINE_READ) or kwargs.get(MACHINE_WRITE) or kwargs.get(ADMIN_WRITE)
					try:
						school = School.from_binddn(lo)[0].name
						MODULE.info('Found school %r as ldap school base' % (school,))
					except IndexError:
						MODULE.warn('All Schools: ERROR, COULD NOT FIND ANY OU!!!')
						school = ''
					LDAP_Connection._school = school
				else:
					school = LDAP_Connection._school
				kwargs['search_base'] = School.get_search_base(school)
			return func(*args, **kwargs)
		return wraps(func)(wrapper_func)
#		def decorated(*args, **kwargs):
#			try:
#				return wrapper_func(*args, **kwargs)
#			except ldap.INVALID_CREDENTIALS:
#				reset_connection_cache()
#				return wrapper_func(*args, **kwargs)
#		return wraps(func)(decorated)
	return inner_wrapper
LDAP_Connection._school = None


class SchoolSearchBase(object):
	"""Deprecated utility class that generates DNs of common school containers for a OU"""
	def __init__(self, availableSchools, school=None, dn=None, ldapBase=None):
		self._ldapBase = ldapBase or ucr.get('ldap/base')

		from ucsschool.lib.models import School
		self._school = school or availableSchools[0]
		self._schoolDN = dn or School.cache(self.school).dn

		# prefixes
		self._containerAdmins = ucr.get('ucsschool/ldap/default/container/admins', 'admins')
		self._containerStudents = ucr.get('ucsschool/ldap/default/container/pupils', 'schueler')
		self._containerStaff = ucr.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')
		self._containerTeachersAndStaff = ucr.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
		self._containerTeachers = ucr.get('ucsschool/ldap/default/container/teachers', 'lehrer')
		self._containerClass = ucr.get('ucsschool/ldap/default/container/class', 'klassen')
		self._containerRooms = ucr.get('ucsschool/ldap/default/container/rooms', 'raeume')
		self._examUserContainerName = ucr.get('ucsschool/ldap/default/container/exam', 'examusers')
		self._examGroupNameTemplate = ucr.get('ucsschool/ldap/default/groupname/exam', 'OU%(ou)s-Klassenarbeit')

		self.group_prefix_students = ucr.get('ucsschool/ldap/default/groupprefix/pupils', 'schueler-')
		self.group_prefix_teachers = ucr.get('ucsschool/ldap/default/groupprefix/teachers', 'lehrer-')
		self.group_prefix_admins = ucr.get('ucsschool/ldap/default/groupprefix/admins', 'admins-')
		self.group_prefix_staff = ucr.get('ucsschool/ldap/default/groupprefix/staff', 'mitarbeiter-')

	@classmethod
	def getOU(cls, dn):
		"""Return the school OU for a given DN.

			>>> SchoolSearchBase.getOU('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
			'dc1'
		"""
		school_dn = cls.getOUDN(dn)
		if school_dn:
			return univention.uldap.explodeDn(school_dn, True)[0]

	@classmethod
	def getOUDN(cls, dn):
		"""Return the School OU-DN part for a given DN.

			>>> SchoolSearchBase.getOUDN('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
			'Ou=dc1,oU=dc,dc=foo,dc=bar'
			>>> SchoolSearchBase.getOUDN('ou=dc1,ou=dc,dc=foo,dc=bar')
			'ou=dc1,ou=dc,dc=foo,dc=bar'
		"""
		match = cls._RE_OUDN.search(dn)
		if match:
			return match.group(1)
	_RE_OUDN = re.compile('(?:^|,)(ou=.*)$', re.I)

	@property
	def dhcp(self):
		return "cn=dhcp,%s" % self.schoolDN

	@property
	def policies(self):
		return "cn=policies,%s" % self.schoolDN

	@property
	def networks(self):
		return "cn=networks,%s" % self.schoolDN

	@property
	def school(self):
		return self._school

	@property
	def schoolDN(self):
		return self._schoolDN

	@property
	def users(self):
		return "cn=users,%s" % self.schoolDN

	@property
	def groups(self):
		return "cn=groups,%s" % self.schoolDN

	@property
	def workgroups(self):
		return "cn=%s,cn=groups,%s" % (self._containerStudents, self.schoolDN)

	@property
	def classes(self):
		return "cn=%s,cn=%s,cn=groups,%s" % (self._containerClass, self._containerStudents, self.schoolDN)

	@property
	def rooms(self):
		return "cn=%s,cn=groups,%s" % (self._containerRooms, self.schoolDN)

	@property
	def students(self):
		return "cn=%s,cn=users,%s" % (self._containerStudents, self.schoolDN)

	@property
	def teachers(self):
		return "cn=%s,cn=users,%s" % (self._containerTeachers, self.schoolDN)

	@property
	def teachersAndStaff(self):
		return "cn=%s,cn=users,%s" % (self._containerTeachersAndStaff, self.schoolDN)

	@property
	def staff(self):
		return "cn=%s,cn=users,%s" % (self._containerStaff, self.schoolDN)

	@property
	def admins(self):
		return "cn=%s,cn=users,%s" % (self._containerAdmins, self.schoolDN)

	@property
	def classShares(self):
		return "cn=%s,cn=shares,%s" % (self._containerClass, self.schoolDN)

	@property
	def shares(self):
		return "cn=shares,%s" % self.schoolDN

	@property
	def printers(self):
		return "cn=printers,%s" % self.schoolDN

	@property
	def computers(self):
		return "cn=computers,%s" % self.schoolDN

	@property
	def examUsers(self):
		return "cn=%s,%s" % (self._examUserContainerName, self.schoolDN)

	@property
	def globalGroupContainer(self):
		return "cn=ouadmins,cn=groups,%s" % (self._ldapBase,)

	@property
	def educationalDCGroup(self):
		return "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def educationalMemberGroup(self):
		return "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def administrativeDCGroup(self):
		return "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def administrativeMemberGroup(self):
		return "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def examGroupName(self):
		## replace '%(ou)s' strings in generic exam_group_name
		ucr_value_keywords = { 'ou': self.school }
		return self._examGroupNameTemplate % ucr_value_keywords

	@property
	def examGroup(self):
		return "cn=%s,cn=ucsschool,cn=groups,%s" % (self.examGroupName, self._ldapBase)

	def isWorkgroup(self, groupDN):
		# a workgroup cannot lie in a sub directory
		if not groupDN.endswith(self.workgroups):
			return False
		return len(univention.uldap.explodeDn(groupDN)) - len(univention.uldap.explodeDn(self.workgroups)) == 1

	def isGroup(self, groupDN):
		return groupDN.endswith(self.groups)

	def isClass(self, groupDN):
		return groupDN.endswith(self.classes)

	def isRoom(self, groupDN):
		return groupDN.endswith(self.rooms)


class SchoolBaseModule(Base):
	"""This classe serves as base class for UCS@school UMC modules that need
	LDAP access. It initiates the list of availabe OUs (self.availableSchools) and
	initiates the search bases (self.searchBase). set_bind_function() is called
	automatically to allow LDAP connections. In order to integrate this class
	into a module, use the following paradigm:

	class Instance(SchoolBaseModule):
		def __init__(self):
			# initiate list of internal variables
			SchoolBaseModule.__init__(self)
			# ... custom code

		def init(self):
			SchoolBaseModule.init(self)
			# ... custom code
	"""
	def init(self):
		set_bind_function(self.bind_user_connection)

	def bind_user_connection(self, lo):
		if not self.user_dn:  # ... backwards compatibility
			# the DN is None if we have a local user (e.g., root)
			# FIXME: the statement above is not completely true, user_dn is None also if the UMC server could not detect it (for whatever reason)
			# therefore this workaround is a security whole which allows to execute ldap operations as machine account
			try:  # to get machine account password
				MODULE.warn('Using machine account for local user: %s' % self.username)
				with open('/etc/machine.secret', 'rb') as fd:
					password = fd.read().strip()
				user_dn = ucr.get('ldap/hostdn')
			except IOError as exc:
				password = None
				user_dn = None
				MODULE.warn('Cannot read /etc/machine.secret: %s' % (exc,))
			lo.lo.bind(user_dn, password)
			return
		return super(SchoolBaseModule, self).bind_user_connection(lo)

	@LDAP_Connection()
	def schools(self, request, ldap_user_read=None):
		"""Returns a list of all available school"""
		from ucsschool.lib.models import School
		schools = School.from_binddn(ldap_user_read)
		if not schools:
			raise UMC_Error(_('Could not find any school. You have to create a school before continuing. Use the \'Add school\' UMC module to create one.'))
		self.finished(request.id, [{'id' : school.name, 'label' : school.display_name} for school in schools])

	def _groups(self, ldap_connection, school, ldap_base, pattern=None, scope='sub'):
		"""Returns a list of all groups of the given school"""
		# get list of all users matching the given pattern
		ldapFilter = None
		if pattern:
			ldapFilter = LDAP_Filter.forGroups(pattern)
		groupresult = udm_modules.lookup('groups/group', None, ldap_connection, scope = scope, base = ldap_base, filter = ldapFilter)
		name_pattern = re.compile('^%s-' % (re.escape(school)), flags=re.I)
		return [{'id': grp.dn, 'label': name_pattern.sub('', grp['name'])} for grp in groupresult]

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def classes(self, request, ldap_user_read=None):
		"""Returns a list of all classes of the given school"""
		school = request.options['school']
		from ucsschool.lib.models import SchoolClass
		self.finished(request.id, self._groups(ldap_user_read, school, SchoolClass.get_container(school), request.options['pattern']))

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def workgroups(self, request, ldap_user_read=None):
		"""Returns a list of all working groups of the given school"""
		school = request.options['school']
		from ucsschool.lib.models import WorkGroup
		self.finished(request.id, self._groups(ldap_user_read, school, WorkGroup.get_container(school), request.options['pattern'], 'one'))

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def groups(self, request, ldap_user_read=None):
		"""Returns a list of all groups (classes and workgroups) of the given school"""
		# use as base the path for 'workgroups', as it incorporates workgroups and classes
		# when searching with scope 'sub'
		school = request.options['school']
		from ucsschool.lib.models import WorkGroup
		self.finished(request.id, self._groups(ldap_user_read, school, WorkGroup.get_container(school), request.options['pattern']))

	@sanitize(school=StringSanitizer(required=True), pattern=StringSanitizer(default=''))
	@LDAP_Connection()
	def rooms(self, request, ldap_user_read=None):
		"""Returns a list of all available school"""
		school = request.options['school']
		from ucsschool.lib.models import ComputerRoom
		self.finished(request.id, self._groups(ldap_user_read, school, ComputerRoom.get_container(school), request.options['pattern']))

	def _users(self, ldap_connection, school, group=None, user_type=None, pattern=''):
		"""Returns a list of all users given 'pattern', 'school' (search base) and 'group'"""
		import ucsschool.lib.models
		if not user_type:
			cls = ucsschool.lib.models.User
		elif user_type.lower() in ('teachers', 'teacher'):
			cls = ucsschool.lib.models.Teacher
		elif user_type.lower() in ('student', 'students', 'pupil', 'pupils'):
			cls = ucsschool.lib.models.Student
		else:
			raise TypeError('user_type %r unknown.' % (user_type,))

		# open the group
		groupObj = None
		if group not in (None, 'None'):
			groupModule = udm_modules.get('groups/group')
			groupObj = groupModule.object(None, ldap_connection, None, group)
			groupObj.open()

		users = cls.get_all(ldap_connection, school, LDAP_Filter.forUsers(pattern))
		users = [user.get_udm_object(ldap_connection) for user in users]
		if groupObj:
			# filter users to be members of the specified group
			users = [i for i in users if i.dn in set(groupObj['users'])]
		return users


class LDAP_Filter:

	@staticmethod
	def forUsers( pattern ):
		return LDAP_Filter.forAll( pattern, ['lastname', 'username', 'firstname'] )

	@staticmethod
	def forGroups( pattern, school = None ):
		# school parameter is deprecated
		return LDAP_Filter.forAll( pattern, ['name', 'description'] )

	@staticmethod
	def forComputers( pattern ):
		return LDAP_Filter.forAll( pattern, ['name', 'description'], ['mac', 'ip'] )

	regWhiteSpaces = re.compile(r'\s+')
	@staticmethod
	def forAll( pattern, subMatch = [], fullMatch = [], prefixes = {} ):
		expressions = []
		for iword in LDAP_Filter.regWhiteSpaces.split( pattern or '' ):
			# evaluate the subexpression (search word over different attributes)
			subexpr = []
			# all expressions for a full string match
			iword = escape_filter_chars(iword)
			if iword:
				subexpr += [ '(%s=%s)' % ( jattr, iword ) for jattr in fullMatch ]

			# all expressions for a substring match
			if not iword:
				iword = '*'
			elif iword.find('*') < 0:
				iword = '*%s*' % iword
			subexpr += [ '(%s=%s%s)' % ( jattr, prefixes.get( jattr, '' ), iword ) for jattr in subMatch ]

			# append to list of all search expressions
			expressions.append('(|%s)' % ''.join(subexpr))

		return '(&%s)' % ''.join( expressions )


class Display:
	@staticmethod
	def user( udm_object ):
		fullname = udm_object[ 'lastname' ]
		if 'firstname' in udm_object and udm_object['firstname']:
			fullname += ', %(firstname)s' % udm_object

		return fullname + ' (%(username)s)' % udm_object
