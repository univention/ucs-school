#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 Univention GmbH
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

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from subprocess import Popen, PIPE, STDOUT
import traceback
import re
import grp

from univention.reservation.scheduler.listener import AbstractListener

from univention.config_registry import ConfigRegistry
from univention.reservation.dbconnector import Profile
import univention.debug as debug

ucr = ConfigRegistry (write_registry=ConfigRegistry.SCHEDULE)
re_option = re.compile ('@%@option:([a-zA-Z]+)@%@')

class SchedulerStartListener (AbstractListener):
	def __init__ (self):
		"""
		Creates a new start event listener
		"""
		_d = debug.function ('listener.start.__init__')
		super (SchedulerStartListener, self).__init__ ('Scheduler Start Listener')
	
	def _applyOptionStartCmd (self, r, o):
		_d = debug.function ('listener.start._applyOptionStartCmd')
		if not o.setting:
			debug.debug (debug.MAIN, debug.WARN, 'W: Option has no setting. id: %d' % o.id)
			return
		s = o.setting
		debug.debug (debug.MAIN, debug.INFO, 'I: Processing setting: %s' % s.name)
		# 1. execute ucrStart
		if s.ucrStart != None and s.ucrStart.strip () != '':
			# replace placeholders
			values = s.ucrStart
			if r.id != None:
				values = values.replace ('@%@reservationid@%@', str (int (r.id)))
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation without id')
				r.setError ('105')
				return
			if r.usergroup != None:
				try:
					groupname = grp.getgrgid (int (r.usergroup))[0]
					values = values.replace ('@%@usergroup@%@', groupname)
				except KeyError:
					debug.debug (debug.MAIN, debug.ERROR, 'W: cannot get groupname for: %d' % r.usergroup)
					r.setError ('105')
					return
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation has no usergroup: %d' % r.id)
				r.setError ('105')
				return
			if r.hostgroup != None:
				try:
					groupname = grp.getgrgid (int (r.hostgroup))[0]
					values = values.replace ('@%@hostgroup@%@', groupname)
				except KeyError:
					debug.debug (debug.MAIN, debug.ERROR, 'W: cannot get groupname for: %d' % r.hostgroup)
					r.setError ('105')
					return
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation has no hostgroup: %d' % r.id)
				r.setError ('105')
				return
			for name in re_option.findall (values):
				if name != s.name:
					# find setting that matches this name
					found = False
					options = r.options
					if r.profile:
						options += r.profile.options
					for opt in options:
						if opt.setting and opt.setting.name == name:
							if opt.value != None:
								values = values.replace ('@%%@option:%s@%%@' % name, str (opt.value))
							else:
								debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStart))
								r.setError ('105')
								return
							found = True
							break
					if not found:
						debug.debug (debug.MAIN, debug.ERROR, 'E: unable to retrieve option: %s\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStart))
						r.setError ('105')
						return
				else:
					if o.value != None:
						values = values.replace ('@%%@option:%s@%%@' % name, str (o.value))
					else:
						debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStart))
						r.setError ('105')
						return
			retcode = 0
			try:
				# FIXME: values.split () does not work with spaces in the value!
				values = values.split ()
				# add bases setting
				values.insert (1, '--schedule')
				p = Popen (['univention-config-registry'] + values, stdout=PIPE, stderr=STDOUT)
				retcode = p.wait ()
				debug.debug (debug.MAIN, debug.INFO, p.communicate ()[0])
				if retcode != 0:
					debug.debug (debug.MAIN, debug.ERROR, 'E: UCR command "%s" exited with return code: %d' % (['univention-config-registry'] + values, retcode))
					if isinstance (o.relative, Profile):
						r.setError ('120-%d' % retcode)
					else:
						r.setError ('110-%d' % retcode)
					return
			except Exception:
				debug.debug (debug.MAIN, debug.ERROR, '%s\nE: UCR command failed: %s' % (traceback.format_exc().replace('%','#'), ['univention-config-registry'] + values))
				if isinstance (o.relative, Profile):
					r.setError ('120-%d' % retcode)
				else:
					r.setError ('110-%d' % retcode)
				return

		# 2. execute cmdStart
		if s.cmdStart != None and s.cmdStart.strip () != '':
			# replace placeholders
			cmd = s.cmdStart
			if r.id != None:
				cmd = cmd.replace ('@%@reservationid@%@', str (int (r.id)))
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation without id')
				r.setError ('105')
				return
			if r.usergroup != None:
				try:
					groupname = grp.getgrgid (int (r.usergroup))[0]
					cmd = cmd.replace ('@%@usergroup@%@', groupname)
				except KeyError:
					debug.debug (debug.MAIN, debug.ERROR, 'W: cannot resolve groupname for: %d' % r.usergroup)
					r.setError ('105')
					return
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation has no usergroup: %d' % r.id)
				r.setError ('105')
				return
			if r.hostgroup != None:
				try:
					groupname = grp.getgrgid (int (r.hostgroup))[0]
					cmd = cmd.replace ('@%@hostgroup@%@', groupname)
				except KeyError:
					debug.debug (debug.MAIN, debug.ERROR, 'W: cannot resolve groupname for: %d' % r.hostgroup)
					r.setError ('105')
					return
			else:
				debug.debug (debug.MAIN, debug.ERROR, 'W: Reservation has no hostgroup: %d' % r.id)
				r.setError ('105')
				return
			for name in re_option.findall (cmd):
				if name != s.name:
					# find setting that matches this name
					found = False
					options = r.options
					if r.profile:
						options += r.profile.options
					for opt in options:
						if opt.setting and opt.setting.name == name:
							if opt.value != None:
								cmd = cmd.replace ('@%%@option:%s@%%@' % name, str (opt.value))
							else:
								debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot executing command: %s' % (name, s.cmdStart))
								r.setError ('105')
								return
							found = True
							break
					if not found:
						debug.debug (debug.MAIN, debug.ERROR, 'E: unable to retrieve option: %s\n\tNot executing command: %s' % (name, s.cmdStart))
						r.setError ('105')
						return
				else:
					if o.value != None:
						cmd = cmd.replace ('@%%@option:%s@%%@' % name, str (o.value))
					else:
						debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot executing command: %s' % (name, s.cmdStart))
						r.setError ('105')
						return
			retcode = 0
			try:
				# FIXME: if the path of the command contains blanks the following
				# will result in an error!
				p = Popen (cmd.split (), stdout=PIPE, stderr=STDOUT)
				retcode = p.wait ()
				debug.debug (debug.MAIN, debug.INFO, p.communicate ()[0])
				if retcode != 0:
					debug.debug (debug.MAIN, debug.ERROR, 'E: command "%s" exited with return code: %d' % (cmd, retcode))
					if isinstance (o.relative, Profile):
						r.setError ('121-%d' % retcode)
					else:
						r.setError ('111-%d' % retcode)
					return
			except Exception:
				debug.debug (debug.MAIN, debug.ERROR, '%s\nE: command failed: %s' % (traceback.format_exc().replace('%','#'), s.cmdStart))
				if isinstance (o.relative, Profile):
					r.setError ('121-%d' % retcode)
				else:
					r.setError ('111-%d' % retcode)
				return

	def notify (self, event):
		_d = debug.function ('listener.start.notify')
		if event.name != 'start' or event.obj == None:
			return
		for r in event.obj:
			debug.debug (debug.MAIN, debug.INFO, 'I: Processing reservation: %s' % r.name)
			# 1. evaluate reservation settings
			for o in r.options:
				self._applyOptionStartCmd (r, o)
				if r.isError ():
					r.updateStatus ()
					break
			# 2. evaluate profile settings
			if not r.isError () and r.profile:
				p = r.profile
				debug.debug (debug.MAIN, debug.INFO, 'I: Processing profile: %s' % p.name)
				for o in p.options:
					self._applyOptionStartCmd (r, o)
					if r.isError ():
						r.updateStatus ()
						break
			if not r.isError ():
				r.setActive ()
				r.updateStatus ()
