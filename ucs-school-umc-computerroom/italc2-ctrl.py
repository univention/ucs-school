#!/usr/bin/python

import inspect
import os
import sys
import notifier
import notifier.signals
import optparse

script_dir = os.path.abspath( os.path.dirname( inspect.getfile(inspect.currentframe() ) ) )
sys.path.insert( 0, os.path.join( script_dir, 'umc/python/computerroom' ) )

import italc2
import ucsschool.lib.schoolldap as usl
import univention.config_registry as ucr

italcManager = None

count = 5

def wait4state( computer, state, value ):
	def _tick():
		global italcManager, count
		if not value: # ugly hack
			count -= 1
			if not count:
				sys.exit( 0 )
			return True
		# print italcManager[ computer ].states, computer, state, value
		if italcManager[ computer ].states[ state ] == value:
			del italcManager
			print 'EXIT'
			sys.exit( 0 )
		return True
	notifier.timer_add( 200, _tick )

def when_connected( computer, options ):
	print 'SIGNAL connected'
	global italcManager

	if not italcManager[ options.computer ].connected:
		print 'NOT connected'
		return True

	print 'connected'

	if options.action:
		func = getattr( italcManager[ options.computer ]._core, options.action )
		func( *args )
	elif options.screen_lock is not None:
		print 'screen', options.screen_lock and 'locked' or 'unlocked'
		italcManager[ options.computer ].lockScreen( options.screen_lock )
		wait4state( options.computer, 'ScreenLock', options.screen_lock )
	elif options.input_lock is not None:
		print 'input', options.screen_lock and 'locked' or 'unlocked'
		italcManager[ options.computer ].lockInput( options.input_lock )
		wait4state( options.computer, 'InputLock', options.input_lock )
	elif options.message is not None:
		print 'display message', options.message
		italcManager[ options.computer ].message( options.message )
		wait4state( options.computer, 'MessageBox', True )
	else:
		print >>sys.stderr, 'Unknown action'
		sys.exit( 1 )

if __name__ == '__main__':
	config = ucr.ConfigRegistry()
	config.load()

	notifier.init()

	parser = optparse.OptionParser()
	parser.add_option( '-o', '--school', dest = 'school', default = '711' )
	parser.add_option( '-r', '--room', dest = 'room', default = 'room01' )
	parser.add_option( '-c', '--computer', dest = 'computer', default = None )
	parser.add_option( '-l', '--list', dest = 'list', action = 'store_true', default = False )
	parser.add_option( '-a', '--action', dest = 'action', default = None )
	parser.add_option( '-s', '--screen-lock', dest = 'screen_lock', action = 'store_true', default = None )
	parser.add_option( '-S', '--screen-unlock', dest = 'screen_lock', action = 'store_false', default = None )
	parser.add_option( '-i', '--input-lock', dest = 'input_lock', action = 'store_true', default = None )
	parser.add_option( '-I', '--input-unlock', dest = 'input_lock', action = 'store_false', default = None )
	parser.add_option( '-m', '--message', dest = 'message', action = 'store', default = None )

	parser.add_option( '-u', '--username', dest = 'username', default = 'Administrator' )
	parser.add_option( '-p', '--password', dest = 'password', default = 'univention' )
	options, args = parser.parse_args()

	usl.set_credentials( 'uid=%s,cn=users,%s' % ( options.username, config.get( 'ldap/base' ) ), options.password )

	italcManager = italc2.ITALC_Manager()
	italcManager.school = options.school
	italcManager.room = options.room

	if options.list:
		print '\n'.join( italcManager.keys() )
		sys.exit( 0 )

	italcManager[ options.computer ].signal_connect( 'connected', notifier.Callback( when_connected, options ) )

	notifier.loop()
