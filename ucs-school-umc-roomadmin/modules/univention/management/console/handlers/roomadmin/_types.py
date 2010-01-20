#!/usr/bin/python2.4
#
# Univention Management Console
#
# Copyright (C) 2007-2010 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.debug as ud
import univention.config_registry
import univention.uldap

_ = umc.Translation( 'univention.management.console.handlers.roomadmin' ).translate

class Room_SearchKeys( umc.StaticSelection ):
	def __init__( self, required = True ):
		umc.StaticSelection.__init__( self, unicode( _( 'Search Key' ) ), required = required )

	def choices( self ):
		return ( ( 'name', _( 'Room Name' ) ), ( 'description', _( 'Description' ) ) )

umcd.copy( umc.StaticSelection, Room_SearchKeys )

class RoomadminBool( umc.StaticSelection ):
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		choices = []

		choices.append( ( 'enabled', _('granted') ) )
		choices.append( ( 'disabled', _('denied') ) )

		return choices

umcd.copy( umc.StaticSelection, RoomadminBool )

enabled_disabled = RoomadminBool( '' )

class GenericSelection ( umc.StaticSelection ):
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )
		self._choices = {}

	def choices( self ):
		return sorted (map (lambda k, v: (k, v), self._choices.keys (), \
				self._choices.values ()))

	def addChoice (self, key, value):
		self._choices[key] = value

	def clearChoices (self):
		self._choices.clear ()

umcd.copy( umc.StaticSelection, GenericSelection )

date = umc.String( _( 'Date' ) )
ipaddr = umc.String( _( 'IP address' ) )
ipaddrs = umc.String( _( 'IP addresses' ) )
computer = umc.String( _( 'Computer' ) )
room = umc.String( _( 'Room' ) )
roomdn = umc.String( _( 'RoomDN' ) )
user = umc.String( _( 'User' ) )
department = umc.String( _( 'Department' ) )
message = umc.Text( _( 'Message' ) )
description = umc.String( _( 'Description' ), required = False )
hostdnlist = umc.ObjectDNList( _( 'Select room members:' ) )
masterip = GenericSelection (_('Select video master:'))

ou = umc.String( _( 'School' ) )
sfilter = umc.String( '&nbsp;' , required = False )
searchkey = Room_SearchKeys()
