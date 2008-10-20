import re
import os
import sys
import logging
from optparse import Option

import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects
import univention.admin.config

import univention.config_registry

ub = univention.config_registry.ConfigRegistry()
ub.load()

lo = None
co = None
admin = None
password = None
options = None

_modules = {}

_logger = logging.getLogger( 'univention-test' )
_handler = logging.StreamHandler( sys.stderr )
_handler.setFormatter( logging.Formatter( '%(name)s: %(message)s' ) )
_logger.addHandler( _handler )
_log_level_map = { 0 : logging.CRITICAL,
				   1 : logging.ERROR,
				   2 : logging.WARN,
				   3 : logging.INFO,
				   4 : logging.DEBUG }

debug = _logger.debug
info = _logger.info
warn = _logger.warn
important = _logger.warn
error = _logger.error
critical = _logger.critical
exception = _logger.exception

def get_options():
	global _modules

	opts = [ Option( '-v', action = 'count', dest = 'verbosity', default = 0,
					 help = 'set verbosity level. repeat this option to increase the level' ),
			 Option( '-c', '--cleanup', action = 'store_true', dest = 'cleanup_only',
					 default = False, help = 'cleanup test environment' ),
			 Option( '-n', '--no-cleanup', action = 'store_true', dest = 'no_cleanup',
					 default = False, help = 'do not run the cleanup after testing' ) ]
	for name, module in _modules.items():
		if hasattr( module, 'get_options' ):
			tmp = module.get_options()
			opts.extend( tmp )

	return opts

def set_options( opts ):
	global options
	options = opts

def init():
	global admin, password

	admin = 'cn=admin,' + ub[ 'ldap/base' ]
	secretFile = open( '/etc/ldap.secret' , 'r' )
	pwdLine = secretFile.readline()
	password = re.sub( '\n', '', pwdLine )

	basedir = os.path.split( __file__ )[ 0 ]
	for item in os.listdir( basedir ):
		module = os.path.join( basedir, item )
		if os.path.isdir( module ):
			init = os.path.join( module, '__init__.pyo' )
			if os.path.isfile( init ):
				try:
					m = __import__( 'univention/test/ldapacls/' + item )
				except Exception, e:
					import traceback
					critical( "Exception occured: loading module '%s' failed: %s\n%s" % \
							  ( item, str( e ), traceback.format_exc() ) )
					continue
				info( 'loaded module %s successfully' % item )
				_modules[ item ] = m

def prepare():
	global lo, co, ub, _modules, _logger, admin, password, options

	_logger.setLevel( _log_level_map[ options.verbosity ] )

	try:
		co=univention.admin.config.config()
		lo = univention.admin.uldap.access( host = ub[ 'ldap/master' ],
											base = ub[ 'ldap/base' ],
											binddn = admin,
											bindpw = password )
	except Exception, e:
		critical( 'authentication error: %s' % str( e ) )
		return False

	if options.cleanup_only:
		return True
	for name, module in _modules.items():
		test = module.init()

def run():
	global _modules, options

	if options.cleanup_only:
		return True
	for name, module in _modules.items():
		try:
			test = module.run()
		except:
			import traceback
			print traceback.format_exc()
			return False
	return True

def cleanup():
	global options

	if options.no_cleanup:
		return True

	for name, module in _modules.items():
		module.cleanup()

	return True

class TestModule( object ):
	def __init__( self, **kwargs ):
		global ub, lo
		for key, value in kwargs.items():
			self.__setattr__( key, value )
		position = univention.admin.uldap.position( ub[ 'ldap/base' ] )
		self.user_mod = univention.admin.modules.get( 'users/user' )
		univention.admin.modules.init( lo, position, self.user_mod )
		self.group_mod = univention.admin.modules.get( 'groups/group' )
		univention.admin.modules.init( lo, position, self.group_mod )
		self.win_mod = univention.admin.modules.get( 'computers/windows' )
		univention.admin.modules.init( lo, position, self.win_mod )
		self.slave_mod = univention.admin.modules.get( 'computers/domaincontroller_slave' )
		univention.admin.modules.init( lo, position, self.slave_mod )
		self.mb_mod = univention.admin.modules.get( 'computers/memberserver' )
		univention.admin.modules.init( lo, position, self.mb_mod )

	def init( self ):
		return True

	def test( self ):
		return []

	def cleanup( self ):
		return True

	def _connect( self, dn, passwd ):
		global ub
		try:
			lo = univention.admin.uldap.access( host = ub[ 'ldap/master' ],
												base = ub[ 'ldap/base' ],
												binddn = dn, bindpw = passwd )
		except:
			lo = None
			critical( 'Authenticated LDAP connection failed for: %s' % dn )
		return lo

	def _change_password( self, lo, position, who, whom, whom_dn, passwd = 'univention3',
						   should_fail = False, module = None ):
		global co
		msg = None
		if not module:
			module = self.user_mod
		obj = univention.admin.objects.get( module, co, lo, position = position, dn = whom_dn )
		try:
			obj.open()
			obj[ 'password' ] = passwd
			if module == self.user_mod:
				obj[ 'overridePWHistory' ] = '1'
			obj.modify()
			msg = '%s changed %s\'s password' % ( who, whom )
		except:
			if should_fail:
				msg = '%s could not change %s\'s password' % ( who, whom )
				return ( True, msg )
			else:
				msg = '%s could not change %s\'s password' % ( who, whom )
				return ( False, msg )

		return ( True, msg )
