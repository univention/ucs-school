#!/usr/bin/python

import inspect
import os
import sys
import notifier
import optparse

script_dir = os.path.abspath( os.path.dirname( inspect.getfile(inspect.currentframe() ) ) )
sys.path.insert( 0, os.path.join( script_dir, 'umc/python/computerroom' ) )

import italc2
import ucsschool.lib.schoolldap as usl

import univention.config_registry as ucr

def show_state():
	FORMAT = '%(name)-15s %(description)-15s %(user)-20s %(ScreenLock)-14s %(InputLock)-13s %(MessageBox)-8s %(DemoServer)-8s %(DemoClient)-8s'
	# clear screen and set position to HOME
	print '\033[2J\033[H'
	# print '##################'
	print FORMAT % { 'name' : 'Name', 'description' : 'Description', 'user' : 'User', 'ScreenLock' : 'Screen locked', 'InputLock' : 'Input locked', 'MessageBox' : 'Message', 'DemoServer' : 'Server', 'DemoClient' : 'Client' }
	print 110*'-'
	for name, comp in m.items():
		info = { 'name' : name, 'description' : comp.description or '<none>', 'user' : comp.user or '<unknown>' }
		info.update( comp.states )
		print FORMAT % info
	return True

if __name__ == '__main__':
	config = ucr.ConfigRegistry()
	config.load()

	notifier.init()

	parser = optparse.OptionParser()
	parser.add_option( '-s', '--school', dest = 'school', default = '711' )
	parser.add_option( '-r', '--room', dest = 'room', default = 'room01' )
	parser.add_option( '-u', '--username', dest = 'username', default = 'Administrator' )
	parser.add_option( '-p', '--password', dest = 'password', default = 'univention' )
	options, args = parser.parse_args()

	usl.set_credentials( 'uid=%s,cn=users,%s' % ( options.username, config.get( 'ldap/base' ) ), options.password )

	m = italc2.ITALC_Manager()
	m.school = options.school
	m.room = options.room

	show_state()
	notifier.timer_add( 1000, show_state )

	notifier.loop()
