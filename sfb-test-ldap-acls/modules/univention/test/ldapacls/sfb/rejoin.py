import univention.test.ldapacls as utl

import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects

class TestModule( utl.TestModule ):
	def __init__( self, **kwargs ):
		utl.TestModule.__init__( self, **kwargs )

	def init( self ):
		# admin
		self.admin_lo = self._connect( self.user[ 'admin' ].dn, 'univention' )
		if not self.admin_lo:
			return False

		self.school_base = "ou=%s,%s" % ( self.school[ 'no' ], utl.ub[ 'ldap/base' ] )
		return True

	def test( self ):
		success = True
		position = univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )

		# set DC password
		dn = "cn=dc%s,cn=dc,cn=server,cn=computers,%s" % ( self.school[ 'no' ], self.school_base )
		dc = univention.admin.objects.get( self.slave_mod, utl.co, self.admin_lo,
										   position = position, dn = dn )
		try:
			dc.open()
		except:
			if self.different_schools:
				return ( [ 'local admin could not re-join the DC slave' ], [] )
			else:
				return ( [], [ 'local admin could not re-join the DC slave' ] )

		dc[ 'password' ] = 'univention-rejoin'
		dc[ 'ip' ] = dc.oldinfo[ 'ip' ]
		dc[ 'mac' ] = dc.oldinfo[ 'mac' ]
		try:
			dc.modify()
			return ( [ 'local admin could re-join the DC slave' ], [] )
		except:
			return ( [], [ 'local admin could not re-join the DC slave' ] )

		return success

	def cleanup( self ):
		position = univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )
		self._change_password( utl.lo, position, 'admin', 'dc', self.school[ 'dc' ].dn,
							   passwd = 'univention', should_fail = self.different_schools,
							   module = self.slave_mod )
		self.admin_lo.lo.lo.unbind()
