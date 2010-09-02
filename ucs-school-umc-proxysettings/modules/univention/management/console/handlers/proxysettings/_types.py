#!/usr/bin/python2.4
#
# Univention Management Console Module
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

_ = umc.Translation( 'univention.management.console.handlers.proxysettings' ).translate
OutString = { 'profile' : _('Profile'), 'domain' : _('Domain'), 'url' : _('URL') }

class ProxySettingsSubject( umc.StaticSelection ):
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		lst = []
		for kind in [ 'domain', 'url' ]:
			lst.append( ( kind, OutString[kind] ) )
		return lst

class ProxySettingsColor( umc.StaticSelection ):
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		lst = []
		lst.append( ( 'blacklisted', _('blacklisted') ) )
		lst.append( ( 'whitelisted', _('whitelisted') ) )
		return lst

class ProxySettingsFiltertype( umc.StaticSelection ):
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		lst = []
		lst.append( ( 'whitelist-block', _('whitelist - block others') ) )
		lst.append( ( 'blacklist-pass', _('blacklist - allow others') ) )
		lst.append( ( 'whitelist-blacklist-pass', _('whitelist then blacklist then allow') ) )
		return lst

class ProfileSelection( umc.StaticSelection ):
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )
		self.values = choices

	def choices( self ):
		lst = self.values
		return lst

umcd.copy( umc.StaticSelection, ProxySettingsSubject )
umcd.copy( umc.StaticSelection, ProxySettingsColor )
umcd.copy( umc.StaticSelection, ProxySettingsFiltertype )
umcd.copy( umc.StaticSelection, ProfileSelection )

ou = umc.String( _( 'School' ) )
group = umc.String( _( 'Group' ) )
kind = ProxySettingsSubject( _( 'subject' ) )
color = ProxySettingsColor( _( 'type' ) )
filtertype = ProxySettingsFiltertype( _( 'Profile Filtertype' ) )
filtertype_text = umc.String( _( 'Profile Filtertype' ), may_change = False, required = False )
profile = umc.String( _( 'Profilename' ), regex = '^(?!default$)[a-zA-Z0-9-]+$' )
domain = umc.String( _( 'Domain' ) )
url = umc.String( _( 'URL' ) )
url_domain = umc.String( _( 'URL / Domain' ) )
filter = umc.String( '&nbsp;', required = False )
emptystring = umc.String( '&nbsp;', required = False )

filteritems = umc.MultiDictValue( _( 'Filteritems' ), syntax = { 'urldomain' : url_domain, 'kind' : kind } )
