#!/usr/bin/python2.4
#
# Univention Management Console
#
# Copyright 2007-2010 Univention GmbH
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

class SchoolLDAPConnection(object):
	idcounter = 1
	def __init__(self, ldapserver=None, binddn='',  bindpw='', username=None):
		self.id = SchoolLDAPConnection.idcounter
		SchoolLDAPConnection.idcounter += 1
		ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: init' % self.id )

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
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: using username "%s"' % (self.id, self.username) )
			result = lo.searchDn( filter = 'uid=%s' % self.username )
			if result:
				self.binddn = result[0]
			else:
				ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: cannot determine dn of uid "%s"' % (self.id, self.username) )

		if self.binddn:
			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: binddn: %s' % (self.id, self.binddn) )
			#lo.close() #FIXME: how to close the connection?

			lo = univention.admin.uldap.access( host = self.ldapserver,
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
				ouresult = univention.admin.modules.lookup( self.oumodule, self.co, self.lo,
															scope = 'one', superordinate = None,
															base = self.configRegistry[ 'ldap/base' ] )
				for ou in ouresult:
					self.availableOU.append(ou['name'])

			ud.debug( ud.ADMIN, ud.INFO, 'SchoolLDAPConnection[%d]: availableOU=%s' % (self.id, self.availableOU ) )

			# TODO FIXME HARDCODED HACK for SFB
			# set departmentNumber and available OU to hardcoded defaults
			if '438' in self.availableOU:
				self.departmentNumber = '438'
				self.switch_ou(self.departmentNumber)
			else:
				self.switch_ou(self.availableOU[0])

		if self.binddn.find('ou=') > 0:
			self.searchbaseDepartment = self.binddn[self.binddn.find('ou='):]
			self.departmentNumber = self.lo.explodeDn( self.searchbaseDepartment, 1 )[0]

			# TODO FIXME HARDCODED HACK for SFB
			# set departmentNumber and available OU to hardcoded defaults
			if '438' in self.availableOU:
				self.departmentNumber = '438'
			else:
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

