#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Lib
#   Parser for smbstatus
#
# Copyright 2012-2013 Univention GmbH
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

import re
import subprocess

import univention.debug as ud

REGEX_LOCKED_FILES = re.compile( r'(?P<pid>[0-9]+)\s+(?P<uid>[0-9]+)\s+(?P<denyMode>[A-Z_]+)\s+(?P<access>[0-9x]+)\s+(?P<rw>[A-Z]+)\s+(?P<oplock>[A-Z_+]+)\s+(?P<sharePath>\S+)\s+(?P<filename>\S+)\s+(?P<time>.*)$' )
REGEX_USERS = re.compile( r'(?P<pid>[0-9]+)\s+(?P<username>\S+)\s+(?P<group>.+\S)\s+(?P<machine>\S+)\s+\(((?P<ipAddress>[0-9a-fA-F.:]+)|ipv4:(?P<ipv4Address>[0-9a-fA-F.:]+)|ipv6:(?P<ipv6Address>[0-9a-fA-F:]+))\)$' )
REGEX_SERVICES = re.compile( r'(?P<service>\S+)\s+(?P<pid>[0-9]+)\s+(?P<machine>\S+)\s+(?P<connectedAt>.*)$' )

class SMB_LockedFile( dict ):
	@property
	def filename( self ):
		return self[ 'filename' ]

	@property
	def sharePath( self ):
		return self[ 'sharePath' ]

	def __str__( self ):
		if self.filename == '.':
			return self.sharePath

		return self.filename

class SMB_Process( dict ):
	def __init__( self, args ):
		dict.__init__( self, args )
		self._locked_files = []
		self._services = []

	@property
	def username( self ):
		return self[ 'username' ]

	@property
	def pid( self ):
		return self[ 'pid' ]

	@property
	def machine( self ):
		return self[ 'machine' ]

	@property
	def lockedFiles( self ):
		return self._locked_files

	@property
	def services( self ):
		return self._services

	@property
	def ipv4address( self ):
		return self[ 'ipv4Address' ]

	@property
	def ipv6address( self ):
		return self[ 'ipv6Address' ]

	@property
	def ipaddress( self ):
		return self.get('ipAddress') or self.ipv4address or self.ipv6address

	def update( self, dictionary ):
		if 'sharePath' in dictionary:
			self._locked_files.append( SMB_LockedFile( dictionary ) )
		elif 'service' in dictionary:
			self._services.append( dictionary[ 'service' ] )
		else:
			dict.update( self, dictionary )

	def __str__( self ):
		title = 'Process %(pid)s: User: %(username)s (group: %(group)s)' % self
		files = '  locked files: %s' % ', '.join( map( str, self.lockedFiles ) )
		services = '  services: %s' % ', '.join( self.services )
		return '\n'.join( ( title, files, services ) )

class SMB_Status( list ):
	def __init__( self, testdata = None ):
		list.__init__( self )
		self.parse( testdata )

	def parse( self, testdata = None ):
		while self:
			self.pop()
		if testdata is None:
			smbstatus = subprocess.Popen( [ '/usr/bin/smbstatus' ], shell = False, stdout = subprocess.PIPE )
			data = [ '%s\n' % x for x in smbstatus.communicate()[0].splitlines() ]
		else:
			data = testdata
		regexps = [ REGEX_USERS, REGEX_SERVICES, REGEX_LOCKED_FILES ]
		regex = None
		for line in data:
			if line.startswith( '-----' ):
				regex = regexps.pop( 0 )
			if not line.strip() or regex is None:
				continue
			match = regex.match( line )
			if match is None:
				continue
			serv = SMB_Process( match.groupdict() )
			self.update( serv )

		for process in self[:]:
			if not 'username' in process:
				ud.debug( ud.PARSER, ud.ERROR, 'Invalid SMB process definition' )
				ud.debug( ud.PARSER, ud.INFO, '%s' % ''.join( data ) )
				self.remove( process )

	def update( self, service ):
		for item in self:
			if item.pid == service.pid:
				item.update( service )
				break
		else:
			self.append( service )

if __name__ == '__main__':
	ud.init( '/var/log/univention/smbstatus.log', 0 , 0 )
	ud.set_level( ud.PARSER, 4 )
	TESTDATA = '''
Samba version 4.0.0alpha18-UNKNOWN
PID     Username      Group         Machine                        
-------------------------------------------------------------------
23740     anton5        Domain Users schule  10.200.28.25 (10.200.28.25:57430)
23741     anton6        Domain Users schule  10.200.28.26 (ipv4:10.200.28.26:57431)
23558     lehrer1       Domain Users schule  client22     (ipv6:2001:4dd0:ff00:8c42:ff08:0ac8::221)

Service      pid     machine       Connected at
-------------------------------------------------------
Marktplatz   23558   client22      Wed May 23 10:48:10 2012
sysvol       23558   client22      Wed May 23 10:48:19 2012
Marktplatz   23741   10.200.28.26  Wed May 23 10:48:35 2012

Locked files:
Pid          Uid        DenyMode   Access      R/W        Oplock           SharePath   Name   Time
--------------------------------------------------------------------------------------------------
23741        2016       DENY_NONE  0x100081    RDONLY     NONE             /home/groups/Marktplatz   .   Wed May 23 10:48:35 2012
'''
	status = SMB_Status()
	# status = SMB_Status( testdata = TESTDATA.split( '\n' ) )
	for process in map( str, status ):
		print process
		print
