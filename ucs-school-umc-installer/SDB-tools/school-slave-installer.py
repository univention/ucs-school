#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013-2018 Univention GmbH
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

import tempfile
import json
import subprocess
import getpass
import sys
import socket
import time
import traceback
import re
from optparse import OptionParser
from ldap.filter import filter_format
import univention.admin.uldap
import univention.lib.umc

from univention.config_registry import ConfigRegistry
ucr = ConfigRegistry()
ucr.load()

def is_valid_ou_name(name):
	""" check if given OU name is valid """
	return bool(re.match('^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$', name))

def configure_ucsschool(options):  # type: (Any) -> None
	connection = univention.lib.umc.Client(
		hostname=options.hostname,
		username=options.username,
		password=options.password,
		automatic_reauthentication=True)

	params = {
		'setup': options.setup,
		'username': options.username,
		'password': options.password,
		'master': options.master,
		'samba': options.samba,
		'schoolOU': options.ou,
	}

	if options.server_type:
		params['server_type'] = options.server_type

	fd = open('/var/log/univention/ucsschool-slave-installer.log', 'a')
	fd.write('-' * 80 + '\n')
	fd.write(time.ctime() + '\n')
	fd.write('Starting configuration of UCS@school ... this might take a while ...\n')
	fd.write('Specified OU name: %r\n' % (options.ou,))
	print 'Starting configuration of UCS@school (ou=%r) ... this might take a while ...' % (options.ou,)
	sys.stdout.flush()

	result = connection.umc_command('schoolinstaller/install', params).decode_body()
	if options.debug:
		print 'CMD: schoolinstaller/install\nRESPONSE: ' + repr(result)
	fd.write('CMD: schoolinstaller/install\nRESPONSE: %r\n' % (result,))
	if result['status'] != 200 or result.get('errors') or result.get('error'):
		print 'ERROR: Failed to start UCS@school installation!'
		print 'output: %s' % result
		sys.exit(1)

	result = {'finished': False}
	failcount = 0
	last_msg = ''

	def check_failcount(msg):
		if failcount >= 1200:
			fd.write('%s\n' % (msg,))
			print msg
			print '\nERROR: %d failed attempts - comitting suicide' % (failcount, )
			sys.exit(1)

	while not result['finished']:
		try:
			msg_body = connection.umc_command('schoolinstaller/progress').decode_body()
			if options.debug:
				print 'CMD: schoolinstaller/progress\nRESPONSE: ' + repr(msg_body)
			if msg_body['status'] != 200:
				failcount += 1
				check_failcount('schoolinstaller/progress returned with an error:\n%r' % (msg_body,))
				continue
			result = msg_body['result']
			failcount = 0
		except (socket.error, univention.lib.umc.ConnectionError):
			failcount += 1
			check_failcount('TRACEBACK %d in connection.request("schoolinstaller/progress"):\n%s' % (failcount, traceback.format_exc(),))
			time.sleep(1)
		msg = '%(component)s - %(info)s' % result
		if msg != last_msg:
			fd.write('%s\n' % (msg,))
			if options.debug:
				print msg
		last_msg = msg

	if result['errors']:
		print 'ERROR: installation failed!'
		for i, error in enumerate(result['errors'], start=1):
			print 'ERROR %d:\n%s' % (i, error)
		sys.exit(1)
	print 'UCS@school successfully configured.'

	print 'Restarting UMC ...'
	msg_body = connection.umc_command('lib/server/restart').decode_body()
	fd.write('CMD: lib/server/restart\nRESPONSE: %r\n' % (msg_body,))
	if options.debug:
		print 'CMD: lib/server/restart\nRESPONSE: %r' % (msg_body,)
	if msg_body['status'] != 200 or msg_body['error'] or not msg_body['result']:
		print 'ERROR: Failed to restart UMC'
		print 'OUTPUT: %s' % (msg_body,)
	print 'UMC successfully restarted.'

def install_app(options):  # type: (Any) -> None
	fd = open('/var/log/univention/ucsschool-slave-installer.log', 'a')
	fd.write('-' * 80 + '\n')
	fd.write(time.ctime() + '\n')

	print 'Checking installation status of app "UCS@school" ...'
	proc = subprocess.Popen(
		['univention-app', 'info', '--as-json'],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE)
	stdout, stderr = proc.communicate()
	if proc.returncode:
		fatal(1, 'ERROR: univention-app returned with exitcode %r\nSTDOUT:\n%s\nSTDERR:\n%s' % (
			proc.returncode, stdout, stderr))
	app_data = json.loads(stdout)
	fd.write('OUTPUT: %r\n' % (app_data,))
	installed_apps = [x.split('=', 1)[0] for x in app_data.get('installed', [])]
	if 'ucsschool' in installed_apps:
		fd.write('The app UCS@school is already installed.\n')
		fd.flush()
		print 'The app UCS@school is already installed.'
	else:
		fd.write('The app UCS@school is currently not installed. Installing app ... this might take a while ...\n')
		print 'The app UCS@school is currently not installed. Installing app ... this might take a while ...'
		sys.stdout.flush()
		fd.flush()

		with tempfile.NamedTemporaryFile() as tmpfn:
			tmpfn.write(options.password)
			cmd = ['univention-app', 'install', 'ucsschool', '--username', options.username, '--pwdfile', tmpfn.name]
			fd.write('CMD: %s\n' % (' '.join(cmd),))
			proc = subprocess.Popen(
				cmd,
				stdout=fd,
				stderr=fd)
			returncode = proc.wait()

		if returncode:
			print '\nERROR: installation of UCS@school via univention-app failed with exitcode %r' % (returncode, )
			sys.exit(1)
		print 'UCS@school app successfully installed.'
		fd.write('UCS@school app successfully installed.\n')
		fd.flush()


def fatal(exitcode, msg):
	with open('/var/log/univention/ucsschool-slave-installer.log', 'a') as fd:
		print >>sys.stderr, msg
		print >>fd, msg
	sys.exit(exitcode)


def main():  # type: () -> None
	parser = OptionParser()
	parser.add_option(
		'-q', '--non-interactive', dest='noninteractive', default=False,
		action='store_true', help='Do not ask for missing config options but simply fail')
	parser.add_option(
		'-H', '--host', dest='hostname', default=None,
		help='host to connect to', metavar='HOST')
	parser.add_option(
		'-u', '--user', dest='username',
		help='username', metavar='UID', default=None)
	parser.add_option(
		'-p', '--password', dest='password',
		help='password', metavar='PASSWORD')
	parser.add_option(
		'-o', '--ou', dest='ou',
		help='ou name of the school', metavar='OU')
	parser.add_option(
		'-m', '--master-host', dest='master', default=ucr['ldap/master'],
		help='on a slave the master host needs to be specified', metavar='HOST')
	parser.add_option(
		'-d', '--debug', dest='debug', default=False,
		action='store_true', help='show some debug output')
	# DISABLED FOR NOW - THE FIRST VERSION ONLY SUPPORTS "EDU-SLAVES"
	# 	parser.add_option(
	# 		'-E', '--educational-server-name', dest='name_edu_server',
	# 		help='name of the educational server', metavar='NAME_EDU_SLAVE')
	# 	parser.add_option(
	# 		'-e', '--educational-server', dest='server_type',
	# 		action='store_const', const='educational',
	# 		help='install a dc slave in educational network (DEFAULT)')
	# 	parser.add_option(
	# 		'-a', '--administrative-server', dest='server_type',
	# 		action='store_const', const='administrative',
	# 		help='install a dc slave in administrative network')

	(options, _) = parser.parse_args()

	# hardcoded settings
	options.server_type = 'educational'
	options.setup = 'multiserver'
	options.samba = '4'

	if ucr['server/role'] != 'domaincontroller_slave':
		parser.error('This script may only be called on UCS system with the role "domaincontroller_slave"!')

	if options.noninteractive:
		if not options.username or not options.password:
			parser.error('Please specify username (-u) and password (-p)!')

		if not options.ou:
			parser.error('Please specify a school OU (-o)!')

		if not is_valid_ou_name(options.ou):
			print '%r is not a valid OU name!' % (options.ou,)

	else:
		if not options.username:
			print 'Please enter the username of a user who is able to join UCS@school systems.'
			options.username = raw_input('Username: ')
		if not options.password:
			print 'Please enter the password for user "%s".' % (options.username,)
			options.password = getpass.getpass('Password: ')
		if not options.ou:
			while True:
				print 'Please enter the school name (school OU name) this system shall be responsible for.'
				options.ou = raw_input('OU: ')
				if not is_valid_ou_name(options.ou):
					print 'This is not a valid OU name!'
				else:
					break

		# test credentials
		try:
			lo = univention.admin.uldap.getMachineConnection()[0]
			filter_s = filter_format('(uid=%s)', (options.username,))
			binddn = lo.search(filter=filter_s)[0][0]
			print 'Connecting as %s to LDAP...' % (binddn, )
			lo = univention.admin.uldap.access(
				host=options.master,
				port=int(ucr.get('ldap/master/port', '7389')),
				base=ucr.get('ldap/base'),
				binddn=binddn,
				bindpw=options.password)
		except IndexError:
			fatal(4, "ERROR: user %s does not exist" % (options.username, ))
		except univention.admin.uexceptions.authFail:
			fatal(5, 'ERROR: username or password is incorrect')

		filter_s = filter_format('(ou=%s)', (options.ou,))
		ou_results = lo.search(filter=filter_s, base=ucr.get('ldap/base'), scope='one')
		if ou_results:
			ou_attrs = ou_results[0][1]
			if 'ucsschoolOrganizationalUnit' not in ou_attrs.get('objectClass'):
				fatal(6, 'ERROR: the given OU exists, but is no UCS@school OU')
		else:
			answer = ''
			while answer.lower().strip() not in ('y', 'n'):
				answer = raw_input('The school OU "%s" does not exist yet. Create this school OU [yn]? ' % (options.ou,))
			if answer == 'n':
				print 'The OU shall not be created by this script. Stopping here.'
				sys.exit(7)
			print 'The OU "%s" will be created during installation.' % (options.ou,)

	print
	print 'During package installation and configuration, a detailed log'
	print 'is written to the following files:'
	print '- /var/log/univention/ucsschool-slave-installer.log'
	print '- /var/log/univention/management-console-module-schoolinstaller.log'
	print
	install_app(options)
	configure_ucsschool(options)


if __name__ == '__main__':
	main()
	sys.exit(0)
