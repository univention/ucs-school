#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Lib
#   Parser for smbstatus
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

import re
import subprocess

import univention.debug as ud

REGEX_LOCKED_FILES = re.compile( r'(?P<pid>[0-9]+)\s+(?P<uid>[0-9]+)\s+(?P<denyMode>[A-Z_]+)\s+(?P<access>[0-9x]+)\s+(?P<rw>[A-Z]+)\s+(?P<oplock>[A-Z_+]+)\s+(?P<sharePath>\S+)\s+(?P<filename>\S+)\s+(?P<time>.*)$' )
REGEX_USERS = re.compile( r'(?P<pid>[0-9]+)\s+(?P<username>\S+)\s+(?P<group>.+\S)\s+(?P<machine>\S+)\s+\(((?P<ipAddress>[0-9a-fA-F.:]+)|ipv4:(?P<ipv4Address>[0-9a-fA-F.:]+)|ipv6:(?P<ipv6Address>[0-9a-fA-F:]+))\)\s+(?P<version>\S+)\s+$' )
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
			smbstatus = subprocess.Popen( [ '/usr/bin/smbstatus' ], shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
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
Samba version 4.2.0rc2-Debian
PID     Username      Group         Machine            Protocol Version       
------------------------------------------------------------------------------
26731     silke5        Domain Users test  10.200.27.155 (ipv4:10.200.27.155:51426) SMB2_10     
25470     d.krause1     Domain Users test  10.200.27.16 (ipv4:10.200.27.16:59306) NT1         
23740     anton5        Domain Users schule  10.200.28.25 (10.200.28.25:57430) NT1         
23741     anton6        Domain Users schule  10.200.28.26 (ipv4:10.200.28.26:57431) SMB2_10     
23558     lehrer1       Domain Users schule  client22     (ipv6:2001:4dd0:ff00:8c42:ff08:0ac8::221) SMB2_10     

Service      pid     machine       Connected at
-------------------------------------------------------
Marktplatz   26731   client22      Tue Nov 18 12:25:44 2014
d.krause1    25470   10.200.27.16  Tue Nov 18 11:49:08 2014
IPC$         25470   10.200.27.16  Tue Nov 18 11:49:08 2014

Locked files:
Pid          Uid        DenyMode   Access      R/W        Oplock           SharePath   Name   Time
--------------------------------------------------------------------------------------------------
23741        2016       DENY_NONE  0x100081    RDONLY     NONE             /home/groups/Marktplatz   .   Wed May 23 10:48:35 2012
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .kde/share/apps/ktp/cache.db   Tue Nov 18 11:49:24 2014
25470        7520       DENY_NONE  0x89        RDONLY     EXCLUSIVE        /home/test/lehrer/d.krause1   .local/share/baloo/file/record.DB   Tue Nov 18 11:53:34 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .local/share/baloo/file/postlist.DB   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .local/share/baloo/file/fileMap.sqlite3-wal   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .config/dconf/user   Tue Nov 18 11:49:09 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .local/share/baloo/file/position.DB   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .local/share/baloo/file/fileMap.sqlite3   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .kde/share/apps/activitymanager/activityranking/database   Tue Nov 18 11:49:18 2014
26731        7464       DENY_NONE  0x100081    RDONLY     NONE             /home/school6/groups/Marktplatz   .   Tue Nov 18 12:25:44 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .local/share/baloo/file/termlist.DB   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .kde/share/apps/activitymanager/resources/database   Tue Nov 18 11:49:18 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .config/dconf/user   Tue Nov 18 11:49:09 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .config/dconf/user   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .config/dconf/user   Tue Nov 18 11:49:33 2014
25470        7520       DENY_NONE  0x89        RDONLY     NONE             /home/test/lehrer/d.krause1   .config/dconf/user   Tue Nov 18 11:49:33 2014
25470        7520       DENY_NONE  0x19b       RDWR       EXCLUSIVE        /home/test/lehrer/d.krause1   .local/share/baloo/file/fileMap.sqlite3-shm   Tue Nov 18 11:49:23 2014
25470        7520       DENY_NONE  0x192       WRONLY     EXCLUSIVE        /home/test/lehrer/d.krause1   .xsession-errors   Tue Nov 18 11:49:08 2014
'''
	status = SMB_Status()
	# status = SMB_Status( testdata = TESTDATA.split( '\n' ) )
	for process in map( str, status ):
		print process
		print
