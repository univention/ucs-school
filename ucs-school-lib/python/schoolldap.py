#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2013 Univention GmbH
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

import univention.debug as ud
import univention.config_registry
import univention.uldap
import univention.admin.config
import univention.admin.modules

import univention.admin as udm
import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects
import univention.admin.uldap as udm_uldap
import univention.admin.syntax as udm_syntax
import univention.admin.uexceptions as udm_errors
from univention.management.console.protocol.message import Message

from univention.lib.i18n import Translation

from ldap import LDAPError

from functools import wraps
import re

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import Base
from univention.management.console.protocol.definitions import *

# load UDM modules
udm_modules.update()

# current user
_user_dn = None
_password = None

_ = Translation('python-ucs-school').translate

try:
	import univention.admin.license
	GPLversion=False
except:
	GPLversion=True


def set_credentials( dn, passwd ):
	global _user_dn, _password

	# the DN is None if we have a local user (e.g., root)
	if not dn:
		# try to get machine account password
		try:
			_password = open('/etc/machine.secret','r').read().strip()
			_user_dn = ucr.get('ldap/hostdn')
			MODULE.warn( 'Using machine account for local user: %s' % _user_dn )
		except IOError, e:
			_password = None
			_user_dn = None
			MODULE.warn( 'Cannot read /etc/machine.secret: %s' % e)
	else:
		_password = passwd
		_user_dn = dn
		MODULE.info( 'Saved LDAP DN for user %s' % _user_dn )


# decorator for LDAP connections
_ldap_connections = {}
_search_base = None

USER_READ = 'ldap_user_read'
USER_WRITE = 'ldap_user_write'
MACHINE_READ = 'ldap_machine_read'
MACHINE_WRITE = 'ldap_machine_write'
ADMIN_WRITE = 'ldap_admin_write'

class LDAP_ConnectionError( Exception ):
	pass

def open_ldap_connection( binddn, bindpw, ldap_server ):
	'''Opens a new LDAP connection using the given user LDAP DN and
	password. The connection is open to the given server or if None the
	server defined by the UCR variable ldap/server/name is used.'''

	try:
		lo = udm_uldap.access( host = ldap_server, base = ucr.get( 'ldap/base' ), binddn = binddn, bindpw = bindpw, start_tls = 2 )
	except udm_errors.noObject, e:
		raise e
	except LDAPError, e:
		raise LDAP_ConnectionError( 'Opening LDAP connection failed: %s' % str( e ) )

	return lo

def get_ldap_connections( connection_types, force = False ):
	global _ldap_connections, _user_dn, _password

	connections = {}
	read_server = ucr.get( 'ldap/server/name' )
	write_server = ucr.get( 'ldap/master' )

	for conn in connection_types:
		if _ldap_connections.get( conn ) and not force:
			connections[ conn ] = _ldap_connections[ conn ]
			continue
		if conn == USER_READ:
			lo = open_ldap_connection( _user_dn, _password, read_server )
		elif conn == USER_WRITE:
			lo = open_ldap_connection( _user_dn, _password, write_server )
		elif conn == MACHINE_READ:
			lo, pos = udm_uldap.getMachineConnection( ldap_master = False )
		elif conn == MACHINE_WRITE:
			lo, pos = udm_uldap.getMachineConnection( ldap_master = True )
		elif conn == ADMIN_WRITE:
			lo, pos = udm_uldap.getAdminConnection()

		connections[ conn ] = lo
		_ldap_connections[ conn ] = lo

	return connections

def LDAP_Connection( *connection_types ):
	"""This decorator function provides an open LDAP connection that can
	be accessed via the variable ldap_connection and a valid position
	within the LDAP directory in the variable ldap_position. It reuses
	an already open connection or creates a new one. If the function
	fails with an LDAP error, the decorators tries to reopen the LDAP
	connection and invokes the function again. if it still fails an
	LDAP_ConnectionError is raised.

	The LDAP connection is opened to ldap/server/name with the current 
	user DN or the host DN in case of a local user. This connection is intended
	only for read access. In order to write changes to the LDAP master, an
	additional, temporary connection needs to be opened explicitly.

	Information for available OUs is initiated from LDAP, as well.

	This decorator can only be used after set_credentials() has been executed.

	When using the decorator the method adds three additional keyword arguments.

	example:
	  @LDAP_Connection( USER_READ, USER_WRITE )
	  def do_ldap_stuff(arg1, arg2, ldap_user_write = None, ldap_user_read = None, ldap_position = None, search_base = None ):
		  ...
		  ldap_connection.searchDn( ..., position = ldap_position )
		  ...
	"""

	if connection_types and not USER_READ in connection_types and not MACHINE_READ in connection_types:
		raise AttributeError( 'At least one read-only connection is required' )
	elif not connection_types:
		_connection_types = ( USER_READ, )
	else:
		_connection_types = connection_types

	def inner_wrapper( func ):
		def wrapper_func( *args, **kwargs ):
			global _licenseCheck, _search_base

			# set LDAP keyword arguments
			connections = get_ldap_connections( _connection_types )
			read_connection = connections.get( USER_READ ) or connections.get( MACHINE_READ )
			kwargs.update( connections )
			kwargs[ 'ldap_position' ] = udm_uldap.position( read_connection.base )

			# set keyword argument for search base
			_init_search_base( read_connection )
			if not kwargs.get('search_base'):
				# search_base is not set manually
				kwargs['search_base'] = _search_base
				if len(args) > 1 and isinstance(args[1], Message):
					# we have a Message instance (i.e. a request), try to set the search_base
					# according to the specified option 'school'
					school = isinstance( args[1].options, dict ) and args[1].options.get('school') or None
					if school:
						kwargs[ 'search_base' ] = SchoolSearchBase( _search_base.availableSchools, school )

			# try to execute the method with the given connection
			# in case of an error, re-open a new LDAP connection and try again
			try:
				return func( *args, **kwargs )
			except ( LDAPError, udm_errors.base ), e:
				MODULE.info( 'LDAP operation has failed' )
				connections = get_ldap_connections( _connection_types, force = True )

				kwargs.update( connections )
				try:
					return func( *args, **kwargs )
				except udm_errors.base, e:
					raise LDAP_ConnectionError( str( e ) )

			return []

		return wraps( func )( wrapper_func )
	return inner_wrapper

class LicenseError( Exception ):
	pass

@LDAP_Connection(MACHINE_READ, MACHINE_WRITE)
def check_license(ldap_machine_read = None, ldap_machine_write = None, ldap_position = None, search_base = None ):
	"""Checks the license cases and throws exceptions accordingly. The logic is copied from the UDM UMC module."""
	global GPLversion
	ldap_connection = ldap_machine_write

	# license check (see also univention.admin.uldap.access.bind())
	_licenseCheck = 0
	if not GPLversion:
		_licenseCheck = univention.admin.license.init_select(ldap_connection, 'admin')

	# in case of errors, raise an exception with user friendly message
	try:
		if GPLversion:
			return  # don't raise exception here
			#raise udm_errors.licenseGPLversion
		ldap_connection._validateLicense()  # throws more exceptions in case the license could not be found
		if _licenseCheck == 1:
			raise udm_errors.licenseClients
		elif _licenseCheck == 2:
			raise udm_errors.licenseAccounts
		elif _licenseCheck == 3:
			raise udm_errors.licenseDesktops
		elif _licenseCheck == 4:
			raise udm_errors.licenseGroupware
		#elif _licenseCheck == 5:
		#   # Free for personal use edition
		#   raise udm_errors.freeForPersonalUse
	except udm_errors.licenseNotFound:
		raise LicenseError(_('License not found. During this session add and modify are disabled.'))
	except udm_errors.licenseAccounts:
		raise LicenseError(_('You have too many user accounts for your license. During this session add and modify are disabled.'))
	except udm_errors.licenseClients:
		raise LicenseError(_('You have too many client accounts for your license. During this session add and modify are disabled.'))
	except udm_errors.licenseDesktops:
		raise LicenseError(_('You have too many desktop accounts for your license. During this session add and modify are disabled.'))
	except udm_errors.licenseGroupware:
		raise LicenseError(_('You have too many groupware accounts for your license. During this session add and modify are disabled.'))
	except udm_errors.licenseExpired:
		raise LicenseError(_('Your license is expired. During this session add and modify are disabled.'))
	except udm_errors.licenseWrongBaseDn:
		raise LicenseError(_('Your license is not valid for your LDAP-Base. During this session add and modify are disabled.'))
	except udm_errors.licenseInvalid:
		raise LicenseError(_('Your license is not valid. During this session add and modify are disabled.'))
	except udm_errors.licenseDisableModify:
		raise LicenseError(_('Your license does not allow modifications. During this session add and modify are disabled.'))
	except udm_errors.freeForPersonalUse:
		raise LicenseError(_('You are currently using the "Free for personal use" edition of Univention Corporate Server.'))
	except udm_errors.licenseGPLversion:
		raise LicenseError(_('Your license status could not be validated. Thus, you are not eligible to support and maintenance. If you have bought a license, please contact Univention or your Univention partner.'))

def _init_search_base(ldap_connection, force=False):
	global _search_base

	if _search_base and not force:
		# search base has already been initiated... we are done
		return

	# initiate the list of available schools and set the default search base
	if ldap_connection.binddn.find('ou=') > 0:
		# we got an OU in the user DN -> school teacher or assistent
		# restrict the visibility to current school
		# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
		schoolDN = ldap_connection.binddn[ldap_connection.binddn.find('ou='):] 
		school = ldap_connection.explodeDn( schoolDN, 1 )[0],
		_search_base = SchoolSearchBase(school, school, schoolDN)
		MODULE.info('LDAP_Connection: setting schoolDN: %s' % _search_base.schoolDN)
	else:
		MODULE.warn( 'LDAP_Connection: unable to identify ou of this account - showing all OUs!' )
		#_ouswitchenabled = True
		oulist = ucr.get('ucsschool/local/oulist')
		availableSchools = []
		if oulist:
			# OU list override via UCR variable (it can be necessary to adjust the list of
			# visible schools on specific systems manually)
			availableSchools = [ x.strip() for x in oulist.split(',') ]
			MODULE.info( 'LDAP_Connection: availableSchools overridden by UCR variable ucsschool/local/oulist')
		else:
			# get a list of available OUs via UDM module container/ou
			ouresult = udm_modules.lookup( 
					'container/ou', None, ldap_connection,
					scope = 'one', superordinate = None,
					base = ucr.get( 'ldap/base' ) )
			ignore_ous = ucr.get( 'ucsschool/ldap/ignore/ous', 'Domain Controllers' ).split( ',' )
			availableSchools = [ ou['name'] for ou in ouresult if not ou[ 'name' ] in ignore_ous ]

		# use the first available OU as default search base
		if not len(availableSchools):
			MODULE.warn('LDAP_Connection: ERROR, COULD NOT FIND ANY OU!!!')
			_search_base = SchoolSearchBase([''])
		else:
			MODULE.info( 'LDAP_Connection: availableSchools=%s' % availableSchools )
			_search_base = SchoolSearchBase(availableSchools)

class SchoolSearchBase(object):
	"""This class serves as wrapper for all the different search bases (users,
	groups, students, teachers etc.). It is initiate with a particular ou.
	The class is inteded for read access only, instead of switching the a
	search base, a new instance can simply be created.
	"""
	def __init__( self, availableSchools, school = None, dn = None, ldapBase = None ):
		if ldapBase:
			self._ldapBase = ldapBase
		else:
			self._ldapBase = ucr.get('ldap/base')

		self._availableSchools = availableSchools
		self._school = school or availableSchools[0]
		# FIXME: search for OU to get correct dn
		self._schoolDN = dn or 'ou=%s,%s' % (self.school, self._ldapBase )

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

	@staticmethod
	def getOU(dn):
		'''Return the school OU for a given DN.'''
		if dn.find('ou=') < 0:
			# no 'ou=' in the string
			return None
		schoolDN = dn[dn.find('ou='):]
		school = univention.uldap.explodeDn( schoolDN, 1 )[0]
		return school

	@property
	def availableSchools(self):
		return self._availableSchools

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

	def isAdim(self, userDN):
		return userDN.endswith(self.admins)

	def isExamUser(self, userDN):
		return userDN.endswith(self.examUsers)

	def isWorkgroup(self, groupDN):
		# a workgroup cannot lie in a sub directory
		cnPart = groupDN[:-len(self.workgroups)-1]
		return cnPart.find(',') < 0

	def isClass(self, groupDN):
		return groupDN.endswith(self.classes)

	def isRoom(self, groupDN):
		return groupDN.endswith(self.rooms)


class SchoolBaseModule( Base ):
	"""This classe serves as base class for UCS@school UMC modules that need
	LDAP access. It initiates the list of availabe OUs (self.availableSchools) and
	initiates the search bases (self.searchBase). set_credentials() is called
	automatically to allow LDAP connections. In order to integrate this class
	into a module, use the following paradigm:

	class Instance( SchoolBaseModule ):
		def __init__( self ):
			# initiate list of internal variables
			SchoolBaseModule.__init__(self)
			# ... custom code

		def init(self):
			SchoolBaseModule.init(self)
			# ... custom code
	"""
	def init(self):
		'''Initialize the module. Invoked when ACLs, commands and
		credentials are available'''
		set_credentials( self._user_dn, self._password )

	@LDAP_Connection()
	def schools( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all available school"""
		# enforce an update of the list of available schools
		global _search_base
		_init_search_base(ldap_user_read, force = True)
		search_base = _search_base  # copy updated, global SchoolSearchBase instance to local reference

		# make sure that at least one school OU
		msg = ''
		if not search_base.availableSchools[0]:
			request.status = MODULE_ERR
			msg = _('Could not find any school. You have to create a school before continuing. Use the \'Add school\' UMC module to create one.')

		# return list of school OUs
		self.finished(request.id, search_base.availableSchools, msg)

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
					userObj = userModule.object(None, ldap_connection, None, idn)
					userObj.open()
					if userObj:
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
