#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2012 Univention GmbH
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

from ldap import LDAPError

from functools import wraps
import re

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import Base

# load UDM modules
udm_modules.update()

### OLD CODE!!!
# class SchoolLDAPConnection(object):
# 	idcounter = 1
# 	def __init__(self, ldapserver=None, binddn='',  bindpw='', username=None):
# 		self.id = SchoolLDAPConnection.idcounter
# 		SchoolLDAPConnection.idcounter += 1
# 		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: init' % self.id )

# 		univention.admin.modules.update()

# 		self.ldapserver = ldapserver
# 		self.binddn = binddn
# 		self.bindpw = bindpw
# 		self.username = username
# 		self.co = None
# 		self.lo = None

# 		self.configRegistry = univention.config_registry.ConfigRegistry()
# 		self.configRegistry.load()

# 		self.availableSchools = []
# 		self.ouswitchenabled = False

# 		self.lo = self.getConnection()

# 	def getConnection(self):
# 		if self.lo:
# 			return self.lo

# 		if self.ldapserver == None:
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: no ldapserver given - using default' % self.id )
# 			self.ldapserver = self.configRegistry[ 'ldap/server/name' ]

# 		self.co = univention.admin.config.config()

# 		# create authenticated ldap connection
# 		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: hostname: %s' % (self.id, self.ldapserver) )
# 		lo = univention.uldap.access( host = self.ldapserver, base = self.configRegistry[ 'ldap/base' ], start_tls = 2 )

# 		if self.username and not self.binddn:
# 			# map username to dn with machine account ldap connection
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: using username "%s"' % (self.id, self.username) )
# 			mc = univention.uldap.getMachineConnection(ldap_master = False)
# 			result = mc.searchDn( filter = 'uid=%s' % self.username )
# 			if result:
# 				self.binddn = result[0]
# 			else:
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: cannot determine dn of uid "%s"' % (self.id, self.username) )

# 		if self.binddn:
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: binddn: %s' % (self.id, self.binddn) )
# 			#lo.close() #FIXME: how to close the connection?

# 			lo = univention.admin.uldap.access( 
# 				host = self.ldapserver,
# 				base = self.configRegistry['ldap/base'],
# 				binddn = self.binddn,
# 				bindpw = self.bindpw,
# 				start_tls = 2 )

# 		self.lo = lo
# 		self._init_ou()

# 		if not self.lo:
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: failed to get ldap connection' % self.id )

# 		return self.lo


# 	def switch_ou( self, ou ):
# 		# FIXME search for OU to get correct dn
# 		self.searchbaseDepartment = 'ou=%s,%s' % (ou, self.configRegistry[ 'ldap/base' ] )
# 		self.school = ou

# 		self.searchbaseComputers = 'cn=computers,%s' % self.searchbaseDepartment
# 		self.searchbaseUsers = "cn=users,%s" % self.searchbaseDepartment
# 		self.searchbaseExtGroups = "cn=schueler,cn=groups,%s" % self.searchbaseDepartment
# 		self.searchbaseRooms = 'cn=raeume,cn=groups,%s' % self.searchbaseDepartment
# 		self.searchbaseClasses = "cn=klassen,cn=schueler,cn=groups,%s" % self.searchbaseDepartment
# 		self.searchbasePupils = "cn=schueler,cn=users,%s" % self.searchbaseDepartment
# 		self.searchbaseTeachers = "cn=lehrer,cn=users,%s" % self.searchbaseDepartment
# 		self.searchbaseShares = "cn=shares,%s" % self.searchbaseDepartment
# 		self.searchbasePrinters = "cn=printers,%s" % self.searchbaseDepartment


# 	def checkConnection(self, ldapserver='', binddn='',  bindpw='', username=None):
# 		reconnect = False
# 		if ldapserver and ldapserver != self.ldapserver:
# 			self.ldapserver = ldapserver
# 			reconnect = True
# 		if binddn and binddn != self.binddn:
# 			self.binddn = binddn
# 			reconnect = True
# 		if bindpw and bindpw != self.bindpw:
# 			self.bindpw = bindpw
# 			reconnect = True
# 		if username and username != self.username:
# 			self.username = username
# 			reconnect = True

# 		if reconnect:
# 			self.lo = None
# 			self.getConnection()

# 		if not self.lo:
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: no connection established - trying reconnect' % self.id )
# 			self.getConnection()

# 		return (self.lo != None)


# 	def _init_ou(self):
# 		self.school = None

# 		self.computermodule = univention.admin.modules.get('computers/computer')
# 		self.usermodule = univention.admin.modules.get('users/user')
# 		self.groupmodule = univention.admin.modules.get('groups/group')
# 		self.sharemodule = univention.admin.modules.get('shares/share')
# 		self.printermodule = univention.admin.modules.get('shares/printer')
# 		self.oumodule = univention.admin.modules.get('container/ou')

# 		# stop here if no ldap connection is present
# 		if not self.lo:
# 			return

# 		self.searchScopeExtGroups = 'one'

# 		if len(self.availableSchools) == 0:
# 			# OU list override
# 			oulist = self.configRegistry.get('ucsschool/local/oulist')
# 			if oulist:
# 				self.availableSchools = [ x.strip() for x in oulist.split(',') ]
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: availableSchools overridden by UCR' % self.id)
# 			else:
# 				self.availableSchools = []
# 				# get available OUs
# 				ouresult = univention.admin.modules.lookup(
# 					self.oumodule, self.co, self.lo,
# 					scope = 'one', superordinate = None,
# 					base = self.configRegistry[ 'ldap/base' ])
# 				for ou in ouresult:
# 					self.availableSchools.append(ou['name'])

# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: availableSchools=%s' % (self.id, self.availableSchools ) )

# 			self.switch_ou(self.availableSchools[0])

# 		if self.binddn.find('ou=') > 0:
# 			self.searchbaseDepartment = self.binddn[self.binddn.find('ou='):]
# 			self.school = self.lo.explodeDn( self.searchbaseDepartment, 1 )[0]

# 			# cut list down to default OU
# 			self.availableSchools = [ self.school ]

# 			self.switch_ou(self.school)

# 		else:
# 			if self.binddn:
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: was not able to identify ou of this account - OU select box enabled!' % self.id )
# 			else:
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: was not able to identify ou of this account - anonymous connection!' % self.id )
# 			self.ouswitchenabled = True


# 	def get_group_member_list( self, groupdn, filterbase = None, attrib = 'users' ):
# 		"""
# 		Returns a list of dn that are member of specified group <groupdn>.
# 		Only those DN are returned that are located within subtree <filterbase>.
# 		By default, the DN of user members are returned. By passing 'hosts' to <attrib>
# 		only computer members are returned. 
# 		"""
# 		memberlist = []

# 		if not self.checkConnection():
# 			return memberlist

# 		if not groupdn:
# 			return memberlist

# 		try:
# 			groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
# 														   scope = 'sub', superordinate = None,
# 														   base = groupdn, filter = '')
# 			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) = %s' % (self.id, groupdn, groupresult) )
# 			for gr in groupresult:
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) gr=%s' % (self.id, groupdn, gr) )
# 				gr.open()
# 				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) gr["%s"]=%s' % (self.id, groupdn, attrib, gr[attrib]) )
# 				for memberdn in gr[attrib]:
# 					if filterbase == None or memberdn.endswith(filterbase):
# 						memberlist.append( memberdn )
# 		except Exception, e:
# 			ud.debug( ud.ADMIN, ud.ERROR, 'SchoolLDAPConnection[%d]: get_group_member_list: lookup failed: %s' % (self.id, e) )

# 		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) memberlist=%s' % (self.id, groupdn, memberlist) )

# 		memberlist = sorted( memberlist )

# 		return memberlist


# current user
_user_dn = None
_password = None

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
		_user_dn = dn
		_password = passwd
		MODULE.info( 'Saved LDAP DN for user %s' % _user_dn )


# decorator for LDAP connections
_ldap_connections = {}
_search_base = None
_licenseCheck = 0

USER_READ = 'ldap_user_read'
USER_WRITE = 'ldap_user_write'
MACHINE_READ = 'ldap_machine_read'
MACHINE_WRITE = 'ldap_machine_write'

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
		MODULE.info( 'connection type: %s' % conn )
		if _ldap_connections.get( conn ) and not force:
			connections[ conn ] = _ldap_connections[ conn ]
			continue
		if conn == USER_READ:
			lo = open_ldap_connection( _user_dn, _password, read_server )
		elif conn == USER_WRITE:
			lo = open_ldap_connection( _user_dn, _password, write_server )
		elif conn == MACHINE_READ:
			lo = univention.uldap.getMachineConnections( ldap_master = False )
		elif conn == MACHINE_WRITE:
			lo = univention.uldap.getMachineConnections( ldap_master = True )

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
					school = args[1].options.get('school')
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

def _init_search_base(ldap_connection):
	global _search_base

	if _search_base:
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
			raise EnvironmentError('Could not find any valid ou!')
		else:
			MODULE.info( 'LDAP_Connection: availableSchools=%s' % availableSchools )
			_search_base = SchoolSearchBase(availableSchools)

class SchoolSearchBase(object):
	"""This class serves as wrapper for all the different search bases (users,
	groups, pupils, teachers etc.). It is initiate with a particular ou.
	The class is inteded for read access only, instead of switching the a
	search base, a new instance can simply be created.
	"""
	def __init__( self, availableSchools, school = None, dn = None ):
		self._availableSchools = availableSchools
		self._school = school or availableSchools[0]
		# FIXME: search for OU to get correct dn
		self._schoolDN = dn or 'ou=%s,%s' % (self.school, ucr.get( 'ldap/base' ) )

		# prefixes
		self._containerAdmins = ucr.get('ucsschool/ldap/default/container/admins', 'admins')
		self._containerPupils = ucr.get('ucsschool/ldap/default/container/pupils', 'schueler')
		self._containerStaff = ucr.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')
		self._containerTeachers = ucr.get('ucsschool/ldap/default/container/teachers', 'lehrer')
		self._containerClass = ucr.get('ucsschool/ldap/default/container/class', 'klassen')
		self._containerRooms = ucr.get('ucsschool/ldap/default/container/rooms', 'raeume')

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
	def workgroups(self):
		return "cn=%s,cn=groups,%s" % (self._containerPupils, self.schoolDN)

	@property
	def classes(self):
		return "cn=%s,cn=%s,cn=groups,%s" % (self._containerClass, self._containerPupils, self.schoolDN)

	@property
	def pupils(self):
		return "cn=%s,cn=users,%s" % (self._containerPupils, self.schoolDN)

	@property
	def teachers(self):
		return "cn=%s,cn=users,%s" % (self._containerTeachers, self.schoolDN)

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
	def rooms(self):
		return "cn=%s,cn=groups,%s" % (self._containerRooms, self.schoolDN)

	@property
	def computers(self):
		return "cn=computers,%s" % self.schoolDN


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
		self.finished( request.id, search_base.availableSchools )

	def _groups( self, ldap_connection, school, ldap_base ):
		"""Returns a list of all groups of the given school"""
		groupresult = udm_modules.lookup( 'groups/group', None, ldap_connection, scope = 'sub', base = ldap_base )
		return map( lambda grp: { 'id' : grp.dn, 'label' : grp[ 'name' ].replace( '%s-' % school, '' ) }, groupresult )

	@LDAP_Connection()
	def classes( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all classes of the given school"""
		self.required_options( request, 'school' )
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.classes ) )

	@LDAP_Connection()
	def workgroups( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all working groups of the given school"""
		self.required_options( request, 'school' )
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.workgroups ) )

	@LDAP_Connection()
	def rooms( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		"""Returns a list of all available school"""
		self.required_options( request, 'school' )
		MODULE.info('### rooms: school=%s base=%s' % (search_base.school, search_base.rooms))
		self.finished( request.id, self._groups( ldap_user_read, search_base.school, search_base.rooms ) )

	def _users( self, ldap_connection, search_base, group = None, user_type = None, pattern = '' ):
		"""Returns a list of all users given 'pattern', 'school' (search base) and 'group'"""
		# get the correct base
		base = search_base.users
		if user_type and user_type.lower() in ('teacher', 'teachers'):
			base = search_base.teachers
		elif user_type and user_type.lower() in ('pupil', 'pupils'):
			base = search_base.pupils

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
			for idn in groupObj['users']:
				userObj = userModule.object(None, ldap_connection, None, idn)
				userObj.open()
				if userObj:
					userresult.append(userObj)
		else:
			# get the LDAP filter
			ldapFilter = LDAP_Filter.forUsers( pattern )

			# search for all users
			userresult = udm_modules.lookup( 'users/user', None, ldap_connection, 
					scope = 'sub', base = base, filter = ldapFilter)

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
	def forGroups( pattern ):
		return LDAP_Filter.forAll( pattern, ['name', 'description'] )

	@staticmethod
	def forComputers( pattern ):
		return LDAP_Filter.forAll( pattern, ['name', 'description'], ['mac', 'ip'] )

	regWhiteSpaces = re.compile(r'\s+')
	@staticmethod
	def forAll( pattern, subMatch = [], fullMatch = []):
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
			subexpr += [ '(%s=%s)' % ( jattr, iword ) for jattr in subMatch ]

			# append to list of all search expressions
			expressions.append('(|%s)' % ''.join(subexpr))

		return '(&%s)' % ''.join( expressions )

class Display:
	@staticmethod
	def user( udm_object ):
		fullname = udm_object[ 'lastname' ]
		if 'firstname' in udm_object:
			fullname += ', %(firstname)s' % udm_object

		return fullname + ' (%(username)s)' % udm_object
