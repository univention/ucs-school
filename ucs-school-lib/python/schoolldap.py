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

from ldap import LDAPError

from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import Base as UMC_Base

# load UDM modules
udm_modules.update()


class SchoolLDAPConnection(object):
	idcounter = 1
	def __init__(self, ldapserver=None, binddn='',  bindpw='', username=None):
		self.id = SchoolLDAPConnection.idcounter
		SchoolLDAPConnection.idcounter += 1
		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: init' % self.id )

		univention.admin.modules.update()

		self.ldapserver = ldapserver
		self.binddn = binddn
		self.bindpw = bindpw
		self.username = username
		self.co = None
		self.lo = None

		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		self.availableOU = []
		self.ouswitchenabled = False

		self.lo = self.getConnection()

	def getConnection(self):
		if self.lo:
			return self.lo

		if self.ldapserver == None:
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: no ldapserver given - using default' % self.id )
			self.ldapserver = self.configRegistry[ 'ldap/server/name' ]

		self.co = univention.admin.config.config()

		# create authenticated ldap connection
		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: hostname: %s' % (self.id, self.ldapserver) )
		lo = univention.uldap.access( host = self.ldapserver, base = self.configRegistry[ 'ldap/base' ], start_tls = 2 )

		if self.username and not self.binddn:
			# map username to dn with machine account ldap connection
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: using username "%s"' % (self.id, self.username) )
			mc = univention.uldap.getMachineConnection(ldap_master = False)
			result = mc.searchDn( filter = 'uid=%s' % self.username )
			if result:
				self.binddn = result[0]
			else:
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: cannot determine dn of uid "%s"' % (self.id, self.username) )

		if self.binddn:
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: binddn: %s' % (self.id, self.binddn) )
			#lo.close() #FIXME: how to close the connection?

			lo = univention.admin.uldap.access( 
				host = self.ldapserver,
				base = self.configRegistry['ldap/base'],
				binddn = self.binddn,
				bindpw = self.bindpw,
				start_tls = 2 )

		self.lo = lo
		self._init_ou()

		if not self.lo:
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: failed to get ldap connection' % self.id )

		return self.lo


	def switch_ou( self, ou ):
		# FIXME search for OU to get correct dn
		self.searchbaseDepartment = 'ou=%s,%s' % (ou, self.configRegistry[ 'ldap/base' ] )
		self.departmentNumber = ou

		self.searchbaseComputers = 'cn=computers,%s' % self.searchbaseDepartment
		self.searchbaseUsers = "cn=users,%s" % self.searchbaseDepartment
		self.searchbaseExtGroups = "cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbaseRooms = 'cn=raeume,cn=groups,%s' % self.searchbaseDepartment
		self.searchbaseClasses = "cn=klassen,cn=schueler,cn=groups,%s" % self.searchbaseDepartment
		self.searchbasePupils = "cn=schueler,cn=users,%s" % self.searchbaseDepartment
		self.searchbaseTeachers = "cn=lehrer,cn=users,%s" % self.searchbaseDepartment
		self.searchbaseShares = "cn=shares,%s" % self.searchbaseDepartment
		self.searchbasePrinters = "cn=printers,%s" % self.searchbaseDepartment


	def checkConnection(self, ldapserver='', binddn='',  bindpw='', username=None):
		reconnect = False
		if ldapserver and ldapserver != self.ldapserver:
			self.ldapserver = ldapserver
			reconnect = True
		if binddn and binddn != self.binddn:
			self.binddn = binddn
			reconnect = True
		if bindpw and bindpw != self.bindpw:
			self.bindpw = bindpw
			reconnect = True
		if username and username != self.username:
			self.username = username
			reconnect = True

		if reconnect:
			self.lo = None
			self.getConnection()

		if not self.lo:
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: no connection established - trying reconnect' % self.id )
			self.getConnection()

		return (self.lo != None)


	def _init_ou(self):
		self.departmentNumber = None

		self.computermodule = univention.admin.modules.get('computers/computer')
		self.usermodule = univention.admin.modules.get('users/user')
		self.groupmodule = univention.admin.modules.get('groups/group')
		self.sharemodule = univention.admin.modules.get('shares/share')
		self.printermodule = univention.admin.modules.get('shares/printer')
		self.oumodule = univention.admin.modules.get('container/ou')

		# stop here if no ldap connection is present
		if not self.lo:
			return

		self.searchScopeExtGroups = 'one'

		if len(self.availableOU) == 0:
			# OU list override
			oulist = self.configRegistry.get('ucsschool/local/oulist')
			if oulist:
				self.availableOU = [ x.strip() for x in oulist.split(',') ]
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: availableOU overridden by UCR' % self.id)
			else:
				self.availableOU = []
				# get available OUs
				ouresult = univention.admin.modules.lookup(
					self.oumodule, self.co, self.lo,
					scope = 'one', superordinate = None,
					base = self.configRegistry[ 'ldap/base' ])
				for ou in ouresult:
					self.availableOU.append(ou['name'])

			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: availableOU=%s' % (self.id, self.availableOU ) )

			self.switch_ou(self.availableOU[0])

		if self.binddn.find('ou=') > 0:
			self.searchbaseDepartment = self.binddn[self.binddn.find('ou='):]
			self.departmentNumber = self.lo.explodeDn( self.searchbaseDepartment, 1 )[0]

			# cut list down to default OU
			self.availableOU = [ self.departmentNumber ]

			self.switch_ou(self.departmentNumber)

		else:
			if self.binddn:
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: was not able to identify ou of this account - OU select box enabled!' % self.id )
			else:
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: was not able to identify ou of this account - anonymous connection!' % self.id )
			self.ouswitchenabled = True


	def get_group_member_list( self, groupdn, filterbase = None, attrib = 'users' ):
		"""
		Returns a list of dn that are member of specified group <groupdn>.
		Only those DN are returned that are located within subtree <filterbase>.
		By default, the DN of user members are returned. By passing 'hosts' to <attrib>
		only computer members are returned. 
		"""
		memberlist = []

		if not self.checkConnection():
			return memberlist

		if not groupdn:
			return memberlist

		try:
			groupresult = univention.admin.modules.lookup( self.groupmodule, self.co, self.lo,
														   scope = 'sub', superordinate = None,
														   base = groupdn, filter = '')
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) = %s' % (self.id, groupdn, groupresult) )
			for gr in groupresult:
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) gr=%s' % (self.id, groupdn, gr) )
				gr.open()
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) gr["%s"]=%s' % (self.id, groupdn, attrib, gr[attrib]) )
				for memberdn in gr[attrib]:
					if filterbase == None or memberdn.endswith(filterbase):
						memberlist.append( memberdn )
		except Exception, e:
			ud.debug( ud.ADMIN, ud.ERROR, 'SchoolLDAPConnection[%d]: get_group_member_list: lookup failed: %s' % (self.id, e) )

		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: group(%s) memberlist=%s' % (self.id, groupdn, memberlist) )

		memberlist = sorted( memberlist )

		return memberlist


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
_ldap_connection = None
_ldap_position = None
_licenseCheck = 0

class LDAP_ConnectionError( Exception ):
	pass

def LDAP_Connection( func ):
	"""This decorator function provides an open LDAP connection that can
	be accessed via the variable ldap_connection and a valid position
	within the LDAP directory in the variable ldap_position. It reuses
	an already open connection or creates a new one. If the function
	fails with an LDAP error, the decorators tries to reopen the LDAP
	connection and invokes the function again. if it still fails an
	LDAP_ConnectionError is raised.

	The LDAP connection is openede to ldap/server/name with the current 
	user DN or the host DN in case of a local user. This connection is intended
	only for read access. In order to write changes to the LDAP master, an
	additional, temporary connection needs to be opened explicitly.

	When using the decorator the method adds two additional keyword arguments.

	example:
	  @LDAP_Connection
	  def do_ldap_stuff(arg1, arg2, ldap_connection = None, ldap_position = None ):
		  ...
		  ldap_connection.searchDn( ..., position = ldap_position )
		  ...
	"""
	def wrapper_func( *args, **kwargs ):
		global _ldap_connection, _ldap_position, _user_dn, _password, _licenseCheck

		if _ldap_connection is not None:
			# reuse LDAP connection
			MODULE.info( 'Using open LDAP connection for user %s' % _user_dn )
			lo = _ldap_connection
			po = _ldap_position
		else:
			# open a new LDAP connection
			MODULE.info( 'Opening LDAP connection for user %s' % _user_dn )
			try:
				lo = udm_uldap.access( host = ucr.get( 'ldap/server/name' ), base = ucr.get( 'ldap/base' ), binddn = _user_dn, bindpw = _password, start_tls = 2 )

				po = udm_uldap.position( lo.base )
			except udm_errors.noObject, e:
				raise e
			except LDAPError, e:
				raise LDAP_ConnectionError( 'Opening LDAP connection failed: %s' % str( e ) )

		# try to execute the method with the given connection
		# in case of an error, re-open a new LDAP connection and try again
		kwargs[ 'ldap_connection' ] = lo
		kwargs[ 'ldap_position' ] = po
		try:
			ret = func( *args, **kwargs )
			_ldap_connection = lo
			_ldap_position = po
			return ret
		except ( LDAPError, udm_errors.base ), e:
			MODULE.info( 'LDAP operation for user %s has failed' % _user_dn )
			try:
				lo = udm_uldap.access( host = ucr.get( 'ldap/master' ), base = ucr.get( 'ldap/base' ), binddn= _user_dn, bindpw = _password )
				lo.requireLicense()
				po = udm_uldap.position( lo.base )
			except udm_errors.noObject, e:
				raise e
			except ( LDAPError, udm_errors.base ), e:
				raise LDAP_ConnectionError( 'Opening LDAP connection failed: %s' % str( e ) )

			kwargs[ 'ldap_connection' ] = lo
			kwargs[ 'ldap_position' ] = po
			try:
				ret = func( *args, **kwargs )
				_ldap_connection = lo
				_ldap_position = po
				return ret
			except udm_errors.base, e:
				raise LDAP_ConnectionError( str( e ) )

		return []

	return wrapper_func

class SchoolSearchBase(object):
	def __init__( self, ou, dn = None ):
		self._departmentNumber = ou
		if dn:
			self._department = dn
		else:
			# FIXME: search for OU to get correct dn
			self._department = 'ou=%s,%s' % (ou, ucr.get( 'ldap/base' ) )

	@property
	def departmentNumber(self):
		return self._departmentNumber

	@property
	def department(self):
		return self._department

	@property
	def users(self):
		return "cn=users,%s" % self.department
	
	@property
	def extGroups(self):
		return "cn=schueler,cn=groups,%s" % self.department
	
	@property
	def classes(self):
		return "cn=klassen,cn=schueler,cn=groups,%s" % self.department

	@property
	def pupils(self):
		return "cn=schueler,cn=users,%s" % self.department

	@property
	def teachers(self):
		return "cn=lehrer,cn=users,%s" % self.department

	@property
	def classShares(self):
		return "cn=klassen,cn=shares,%s" % self.department

	@property
	def shares(self):
		return "cn=shares,%s" % self.department

class SchoolBaseModule(UMC_Base):
	def __init__(self):
		UMC_Base.__init__(self)
		self.availableOU = []
		self.searchBase = None
		
	def init(self):
		'''Initialize the module. Invoked when ACLs, commands and
		credentials are available'''
		set_credentials( self._user_dn, self._password )
		self._init_ous()

	@LDAP_Connection
	def _init_ous( self, ldap_connection = None, ldap_position = None ):
		'''Initiates information for available OUs from LDAP.
		Call this method after set_credentials() has been executed.'''

		if ldap_connection.binddn.find('ou=') > 0:
			# we got an OU in the user DN -> school teacher or assistent
			# restrict the visibility to current school
			# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
			self.searchBase = SchoolSearchBase(
					ldap_connection.explodeDn( self.searchBase.department, 1 )[0],
					ldap_connection.binddn[ldap_connection.binddn.find('ou='):] )
			MODULE.info('SchoolBaseModule: setting department: %s' % self.searchBase.department)

			# cut list down to default OU
			self.availableOU = [ self.searchBase.departmentNumber ]
		else:
			MODULE.warn( 'SchoolBaseModule: unable to identify ou of this account - showing all OUs!' )
			#self.ouswitchenabled = True

			oulist = ucr.get('ucsschool/local/oulist')
			if oulist:
				# OU list override via UCR variable (it can be necessary to adjust the list of
				# visible schools on specific systems manually)
				self.availableOU = [ x.strip() for x in oulist.split(',') ]
				MODULE.info( 'SchoolBaseModule: availableOU overridden by UCR variable ucsschool/local/oulist')
			else:
				# get a list of available OUs via UDM module container/ou
				ouresult = udm_modules.lookup( 
						'container/ou', None, ldap_connection,
						scope = 'one', superordinate = None,
						base = ucr.get( 'ldap/base' ) )
				self.availableOU = [ ou['name'] for ou in ouresult ]

			# use the first available OU
			if not len(self.availableOU):
				MODULE.warn('SchoolBaseModule: ERROR, COULD NOT FIND ANY OU!!!')
				self.searchBase = SchoolSearchBase('')
				raise EnvironmentError('Could not find any valid ou!')
			else:
				MODULE.info( 'SchoolBaseModule: availableOU=%s' % self.availableOU )
				self.searchBase = SchoolSearchBase(self.availableOU[0])

