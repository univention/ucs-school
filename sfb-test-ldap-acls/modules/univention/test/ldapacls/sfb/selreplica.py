import ldap

import univention.test.ldapacls as utl

class TestModule( utl.TestModule ):
	def __init__( self, **kwargs ):
		utl.TestModule.__init__( self, **kwargs )

	def init( self ):
		try:
			host = 'LDAP://' + utl.ub[ 'ldap/master' ]
			self.dc_lo = ldap.ldapobject.SmartLDAPObject( uri = host,
														  who = self.user[ 'dc' ].dn,
														  cred = 'univention', start_tls = 0 )
		except Exception, e:
			utl.critical( 'authentication error: %s' % str( e ) )
			return False

		return True

	def test( self ):
		# try to read accounts from the school
		res = self.dc_lo.search_s( 'ou=%s,%s' % ( self.school[ 'no' ], utl.ub[ 'ldap/base' ] ),
								   ldap.SCOPE_BASE )
		if res:
			return ( [ 'School DC %s can read subtree of school %s' % \
					   ( self.user[ 'no' ], self.school[ 'no' ] ), ], [] )
		else:
			return ( [], [ 'School DC %s can not read subtree of school %s' % \
						   ( self.school[ 'no' ], self.user[ 'no' ] ), ] )

	def cleanup( self ):
		self.dc_lo.unbind()
