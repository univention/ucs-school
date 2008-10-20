#
# Univention listener module:
#  send wakeup-on-lan packets
#
# Copyright (C) 2004, 2005, 2006 Univention GmbH
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

import listener
import os, re, string, time
import univention.debug

name='sfb-rmm'
description='handle sfb restoremanagement attributes'
filter='(objectClass=univentionWindows)'

__prgWOL = '/usr/bin/wakeonlan'
__prgAT  = '/usr/bin/at'
__prgSFBRMM = '/usr/sbin/sfb-rmm'


def sendWOLPacket(dn, mac):
	global __prgWOL
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: sending WOL packet to %s (%s)' % (mac, dn))
	os.system('%s %s' %(__prgWOL, mac))


def scheduleWOLPacket(dn, mac, hour, minute):
	global __prgAT, __prgWOL
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: scheduling WOL for %s at %02d:%02d (%s)' % (mac, int(hour), int(minute), dn) )
	os.system('echo "/usr/sbin/jitter 59 %s %s" | %s %02d:%02d' % (__prgWOL, mac, __prgAT, int(hour), int(minute)))


def handler(dn, new, old):
	global __prgSFBRMM
#	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: IN dn=%s' % str(dn))
#	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: IN old=%s' % str(old))
#	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: IN new=%s' % str(new))

	if new:
		# do WOL stuff
		if new.has_key('sfbwFlagWinHostReinstall') and new['sfbwFlagWinHostReinstall'] and new['sfbwFlagWinHostReinstall'][0] == '1':
			if new.has_key('sfbwFlagWinHostReinstallUseWOL') and new['sfbwFlagWinHostReinstallUseWOL'] and new['sfbwFlagWinHostReinstallUseWOL'][0] == '1':
				# WOL is enabled
				if new.has_key('macAddress') and new['macAddress']:
					# mac address is set for windows host
					if new.has_key('sfbwFlagWinHostReinstallWOLNow') and new['sfbwFlagWinHostReinstallWOLNow'] and new['sfbwFlagWinHostReinstallWOLNow'][0] == '1':
						# send WOL packet in two minutes
						schedtime = time.time() + 120
						hour = time.localtime( schedtime )[3]
						minute = time.localtime( schedtime )[4]
						scheduleWOLPacket(dn, new['macAddress'][0], hour, minute)

					elif new.has_key('sfbwWinHostReinstallWOLHour') and new['sfbwWinHostReinstallWOLHour'] and new.has_key('sfbwWinHostReinstallWOLMinute') and new['sfbwWinHostReinstallWOLMinute']:
						# send WOL packet at specified time
						scheduleWOLPacket(dn, new['macAddress'][0], new['sfbwWinHostReinstallWOLHour'][0], new['sfbwWinHostReinstallWOLMinute'][0])


		if new.has_key('sfbwFlagWinHostReinstall') and new['sfbwFlagWinHostReinstall'] and new['sfbwFlagWinHostReinstall'][0] == '1':
			# if reinstall attr is present and is set to 1
			if not old or not (old and old.has_key('sfbwFlagWinHostReinstall') and old['sfbwFlagWinHostReinstall'] and old['sfbwFlagWinHostReinstall'][0] == '1'):
				# and ( current object is new (e.g. freshly created) or attr wasn't set or attr was '0' )
				listener.setuid(0)
				try:
					os.system('%s --setpol %s' % (__prgSFBRMM, dn))
				finally:
					listener.unsetuid()


		if not (new.has_key('sfbwFlagWinHostReinstall') and new['sfbwFlagWinHostReinstall'] and new['sfbwFlagWinHostReinstall'][0] == '1'):
			# if reinstall attr is not present or not set to 1
			if not old or not (old and old.has_key('sfbwFlagWinHostReinstall') and old['sfbwFlagWinHostReinstall'] and old['sfbwFlagWinHostReinstall'][0] == '0'):
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'SFB-RMM: GOTCHA')
				# and ( current object is new (e.g. freshly created) or attr wasn't set or attr was '1' )
				listener.setuid(0)
				try:
					os.system('%s --unsetpol %s' % (__prgSFBRMM, dn))
				finally:
					listener.unsetuid()


def initialize():
	pass


def clean():
	pass


def postrun():
	pass

