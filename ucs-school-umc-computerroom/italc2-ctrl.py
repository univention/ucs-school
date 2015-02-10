#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2015 Univention GmbH
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

def wait4state( computer, signal, value ):
	def _sig_handler( new_value, expected_value ):
		print 'GOT SIGNAL', signal, new_value
		sys.exit( 0 )
		return False
	computer.signal_connect( signal, notifier.Callback( _sig_handler, value ) )
	# def _tick():
	# 	global italcManager, count
	# 	if not value: # ugly hack
	# 		count -= 1
	# 		if not count:
	# 			sys.exit( 0 )
	# 		return True
	# 	if italcManager[ computer ].flagsDict[ state ] == value:
	# 		del italcManager
	# 		print 'EXIT'
	# 		sys.exit( 0 )
	# 	return True
	# notifier.timer_add( 200, _tick )

def when_connected( computer, options ):
	print 'SIGNAL connected'
	global italcManager

	if not italcManager[ options.computer ].connected:
		print 'NOT connected'
		return True

	print 'connected'

	computer = italcManager[ options.computer ]
	if options.action:
		func = getattr( computer._core, options.action )
		func( *args )
	elif options.screen_lock is not None:
		print 'screen', options.screen_lock and 'locked' or 'unlocked'
		computer.lockScreen( options.screen_lock )
		wait4state( computer, 'screen-lock', options.screen_lock )
	elif options.input_lock is not None:
		print 'input', options.screen_lock and 'locked' or 'unlocked'
		computer.lockInput( options.input_lock )
		wait4state( computer, 'input-lock', options.input_lock )
	elif options.message is not None:
		print 'display message', options.message
		computer.message( options.message )
		wait4state( computer, 'MessageBox', True )
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

	italcManager = italc2.ITALC_Manager( options.username, options.password )
	italcManager.school = options.school
	italcManager.room = options.room

	if options.list:
		print '\n'.join( italcManager.keys() )
		sys.exit( 0 )

	italcManager[ options.computer ].signal_connect( 'connected', notifier.Callback( when_connected, options ) )

	notifier.loop()
