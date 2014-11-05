#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2014 Univention GmbH
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
import PyQt4.Qt as qt
import notifier
import optparse

script_dir = os.path.abspath( os.path.dirname( inspect.getfile(inspect.currentframe() ) ) )
sys.path.insert( 0, os.path.join( script_dir, 'umc/python/computerroom' ) )

import italc2
import ucsschool.lib.schoolldap as usl

import univention.config_registry as ucr
from univention.management.console.log import log_init, log_set_level

def show_state( options ):
	FORMAT = '%(name)-15s %(user)-25s %(ScreenLock)-14s %(InputLock)-13s %(MessageBox)-8s %(DemoServer)-8s %(DemoClient)-8s %(Flags)5s'
	# clear screen and set position to HOME
	if not options.logmode:
		print '\033[2J\033[H'
	else:
		print '##################'
	print FORMAT % { 'name' : 'Name', 'description' : 'Description', 'user' : 'User', 'ScreenLock' : 'Screen locked', 'InputLock' : 'Input locked', 'MessageBox' : 'Message', 'DemoServer' : 'Server', 'DemoClient' : 'Client', 'Flags' : 'Flags' }
	print 120*'-'
	for name, comp in m.items():
		info = { 'name' : name, 'description' : comp.description or '<none>', 'user' : comp.user.current is None and '<unknown>' or comp.user.current }
		info.update( comp.flagsDict )
		info[ 'Flags' ] = comp.flags.current is None and '<not set>' or comp.flags.current
		print FORMAT % info
	return True

if __name__ == '__main__':
	config = ucr.ConfigRegistry()
	config.load()

	qApp = qt.QCoreApplication( sys.argv )
	notifier.init( notifier.QT )

	parser = optparse.OptionParser()
	parser.add_option( '-s', '--school', dest = 'school', default = '711' )
	parser.add_option( '-r', '--room', dest = 'room', default = 'room01' )
	parser.add_option( '-l', '--log-mode', dest = 'logmode', default = False, action = 'store_true' )
	parser.add_option( '-o', '--log-only', dest = 'logonly', default = False, action = 'store_true' )
	parser.add_option( '-d', '--debug', dest = 'debug', default = 1 )
	parser.add_option( '-u', '--username', dest = 'username', default = 'Administrator' )
	parser.add_option( '-p', '--password', dest = 'password', default = 'univention' )
	options, args = parser.parse_args()

	if options.logmode:
		log_init( '/dev/stderr' )
		log_set_level( int( options.debug ) )
	else:
		log_init( 'italc2-monitor' )
		log_set_level( int( options.debug ) )

	usl.set_credentials( 'uid=%s,cn=users,%s' % ( options.username, config.get( 'ldap/base' ) ), options.password )

	m = italc2.ITALC_Manager( options.username, options.password )
	m.school = options.school
	m.room = options.room

	if not options.logmode and not options.logonly:
		show_state( options )
		print 'starting timer'
		timer = notifier.timer_add( 2000, notifier.Callback( show_state, options ) )

	notifier.loop()

