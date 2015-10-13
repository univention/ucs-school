#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2015 Univention GmbH
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
import univention.admin.uldap as udm_uldap
import univention.admin.uexceptions as udm_errors
from univention.management.console.protocol.message import Message

from univention.lib.i18n import Translation

from functools import wraps
import re
import traceback

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.ldap import get_machine_connection, get_admin_connection, get_user_connection
from univention.management.console.modules import Base
from univention.management.console.protocol.definitions import MODULE_ERR

# load UDM modules
udm_modules.update()

__bind_callback = None
_search_base = None

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
	"""This decorator function provides an open LDAP connection that can
	be accessed via the variable ldap_connection and a valid position
	within the LDAP directory in the variable ldap_position. It reuses
	an already open connection or creates a new one.

	The LDAP connection is opened to ldap/server/name with the current
	user DN or the host DN in case of a local user. This connection is intended
	only for read access. In order to write changes to the LDAP master, an
	additional, temporary connection needs to be opened explicitly.

	Information for available OUs is initiated from LDAP, as well.

	This decorator can only be used after set_bind_function() has been executed.

	When using the decorator the method adds three additional keyword arguments.

	example:
	  @LDAP_Connection(USER_READ, USER_WRITE)
	  def do_ldap_stuff(arg1, arg2, ldap_user_write=None, ldap_user_read=None, ldap_position=None, search_base=None):
		  ...
		  ldap_user_read.searchDn(..., position=ldap_position)
		  ...
	"""

	if connection_types and USER_READ not in connection_types and MACHINE_READ not in connection_types:
		raise AttributeError( 'At least one read-only connection is required' )
	elif not connection_types:
		_connection_types = (USER_READ,)
	else:
		_connection_types = connection_types

	def inner_wrapper(func):
		def wrapper_func(*args, **kwargs):
			# set LDAP keyword arguments
			connections = {}
			if USER_READ in _connection_types:
				connections[USER_READ], po = get_user_connection(bind=__bind_callback, write=False)
			if USER_WRITE in _connection_types:
				connections[USER_WRITE], po = get_user_connection(bind=__bind_callback, write=True)
			if MACHINE_READ in _connection_types:
				connections[MACHINE_READ], po = get_machine_connection(write=False)
			if MACHINE_WRITE in _connection_types:
				connections[MACHINE_WRITE], po = get_machine_connection(write=True)
			if ADMIN_WRITE in _connection_types:
				connections[ADMIN_WRITE], po = get_admin_connection()

			read_connection = connections.get(USER_READ) or connections.get(MACHINE_READ)
			kwargs.update(connections)
			kwargs['ldap_position'] = udm_uldap.position(read_connection.base)

			# set keyword argument for search base
			_init_search_base(read_connection)
			if not kwargs.get('search_base'):
				# search_base is not set manually
				kwargs['search_base'] = _search_base
				if len(args) > 1 and isinstance(args[1], Message):
					# we have a Message instance (i.e. a request), try to set the search_base
					# according to the specified option 'school'
					school = isinstance(args[1].options, dict) and args[1].options.get('school') or None
					if school:
						kwargs['search_base'] = SchoolSearchBase(_search_base.availableSchools, school)

			return func(*args, **kwargs)

		return wraps(func)(wrapper_func)
	return inner_wrapper


@LDAP_Connection(MACHINE_READ)
def get_all_local_searchbases(ldap_machine_read=None, ldap_position=None, search_base=None):
	from ucsschool.lib.models import School
	schools = School.get_all(ldap_machine_read)
	oulist = map(lambda school: school.name, schools)
	if not oulist:
		raise ValueError('LDAP_Connection: ERROR, COULD NOT FIND ANY OU!!!')

	accessible_searchbases = map(lambda school: SchoolSearchBase(oulist, school), oulist)
	return accessible_searchbases


def _init_search_base(ldap_connection, force=False):
	global _search_base

	if _search_base and not force:
		# search base has already been initiated... we are done
		return

	from ucsschool.lib.models import School
	schools = School.from_binddn(ldap_connection)
	school_names = map(lambda school: school.name, schools)
	if not school_names:
		MODULE.warn('All Schools: ERROR, COULD NOT FIND ANY OU!!!')
		_search_base = SchoolSearchBase([''])
	else:
		MODULE.info('All Schools: school_names=%s' % school_names)
		_search_base = SchoolSearchBase(school_names)


class SchoolSearchBase(object):
	"""This class serves a wrapper for all the different search bases (users,
	groups, students, teachers etc.). It is initiated with a particular ou.
	The class is inteded for read access only, instead of switching the
	search base, a new instance can simply be created.
	"""
	def __init__( self, availableSchools, school = None, dn = None, ldapBase = None ):
		if ldapBase:
			self._ldapBase = ldapBase
		else:
			self._ldapBase = ucr.get('ldap/base')

		from ucsschool.lib.models import School
		self._availableSchools = availableSchools
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
	def availableSchools(self):
		return self._availableSchools

	@property
	def allSchoolBases(self):
		availableSchools = self.availableSchools
		for school in availableSchools:
			yield self.__class__(availableSchools, school, None, self._ldapBase)

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

	def isStudent(self, userDN):
		return userDN.endswith(self.students)

	def isTeacher(self, userDN):
		return userDN.endswith(self.teachers) or userDN.endswith(self.teachersAndStaff) or userDN.endswith(self.admins)

	def isStaff(self, userDN):
		return userDN.endswith(self.staff) or userDN.endswith(self.teachersAndStaff)

	def isAdmin(self, userDN):
		return userDN.endswith(self.admins)

	def isExamUser(self, userDN):
		return userDN.endswith(self.examUsers)

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
			# therefore this workaround is a security whole which allows to executed ldap operations as machine account
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
	def schools( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all available school"""
		from ucsschool.lib.models import School
		ret = []
		schools = School.from_binddn(ldap_user_read)
		for school in schools:
			ret.append({'id' : school.name, 'label' : school.display_name})

		# make sure that at least one school OU
		msg = ''
		if not ret:
			request.status = MODULE_ERR
			msg = _('Could not find any school. You have to create a school before continuing. Use the \'Add school\' UMC module to create one.')

		# return list of school OUs
		self.finished(request.id, ret, msg)

	def _groups( self, ldap_connection, school, ldap_base, pattern = None, scope = 'sub' ):
		"""Returns a list of all groups of the given school"""
		# get list of all users matching the given pattern
		ldapFilter = None
		if pattern:
			ldapFilter = LDAP_Filter.forGroups(pattern)
		groupresult = udm_modules.lookup('groups/group', None, ldap_connection, scope = scope, base = ldap_base, filter = ldapFilter)
		name_pattern = re.compile('^%s-' % (re.escape(school)), flags=re.I)
		return [ { 'id' : grp.dn, 'label' : name_pattern.sub('', grp['name']) } for grp in groupresult ]

	@LDAP_Connection()
	def classes( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all classes of the given school"""
		self.required_options( request, 'school' )
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.classes, request.options.get('pattern') ) )

	@LDAP_Connection()
	def workgroups( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all working groups of the given school"""
		self.required_options( request, 'school' )
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.workgroups, request.options.get('pattern'), 'one' ) )

	@LDAP_Connection()
	def groups( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all groups (classes and workgroups) of the given school"""
		self.required_options( request, 'school' )
		# use as base the path for 'workgroups', as it incorporates workgroups and classes
		# when searching with scope 'sub'
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.workgroups, request.options.get('pattern') ) )

	@LDAP_Connection()
	def rooms( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all available school"""
		self.required_options( request, 'school' )
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.rooms, request.options.get('pattern') ) )

	def _users( self, ldap_connection, search_base, group = None, user_type = None, pattern = '' ):
		"""Returns a list of all users given 'pattern', 'school' (search base) and 'group'"""
		# get the correct base
		bases = [ search_base.users ]
		if user_type and user_type.lower() in ('teacher', 'teachers'):
			bases = [ search_base.teachers, search_base.teachersAndStaff, search_base.admins ]
		elif user_type and user_type.lower() in ('student', 'students', 'pupil', 'pupils'):
			bases = [ search_base.students ]

		# open the group
		groupObj = None
		if group not in (None, 'None'):
			groupModule = udm_modules.get('groups/group')
			groupObj = groupModule.object(None, ldap_connection, None, group)
			groupObj.open()

		# query the users
		userresult = []
		if not pattern and groupObj:
			# special case: no filter is given and a group is selected
			# in this case, it is more efficient to get all users from the group directly
			userModule = udm_modules.get('users/user')
			userresult = []
			for ibase in bases:
				for idn in filter( lambda u: u.endswith( ibase ), groupObj['users'] ):
					try:
						userObj = udm_modules.lookup(userModule, None, ldap_connection, scope='base', base=idn)[0]
					except udm_errors.noObject:
						MODULE.process('_users(): skipped foreign OU user %r' % (idn,))
						continue
					try:
						userObj.open()
					except udm_errors.ldapError:
						raise
					except udm_errors.base:
						MODULE.error('get(): failed to open user object: %r\n%s' % (idn, traceback.format_exc()))
					else:
						userresult.append(userObj)
		else:
			# get the LDAP filter
			ldapFilter = LDAP_Filter.forUsers( pattern )

			# search for all users
			for ibase in bases:
				try:
					userresult.extend(udm_modules.lookup( 'users/user', None, ldap_connection,
							scope = 'sub', base = ibase, filter = ldapFilter))
				except udm_errors.noObject:
					# the ldap base does not exists
					pass

			if groupObj:
				# filter users to be members of the specified group
				groupUserDNs = set(groupObj['users'])
				userresult = [ i for i in userresult if i.dn in groupUserDNs ]

		return userresult


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
