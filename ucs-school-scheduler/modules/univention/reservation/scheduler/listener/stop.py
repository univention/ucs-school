#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Univention GmbH
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

import datetime
from subprocess import Popen, PIPE, STDOUT
import traceback
import re
import grp

from univention.reservation.scheduler.listener import AbstractListener

from univention.config_registry import ConfigRegistry
from univention.reservation.dbconnector import Profile, DISTRIBUTIONID
import univention.debug as debug

ucr = ConfigRegistry (write_registry=ConfigRegistry.SCHEDULE)
re_option = re.compile ('@%@option:([a-zA-Z]+)@%@')
re_option_int2bool = re.compile ('@%@option-int2bool(-invert)?:([a-zA-Z]+)@%@')

class SchedulerStopListener (AbstractListener):
	def __init__ (self):
		"""
		Creates a new stop event listener
		"""
		_d = debug.function ('listener.stop.__init__')
		super (SchedulerStopListener, self).__init__ ('Scheduler Stop Listener')

	def _applyOptionStopCmd (self, r, o):
		_d = debug.function ('listener.stop._applyOptionStopCmd')
		if not o.setting:
			debug.debug (debug.MAIN, debug.ERROR, 'W: Option has no setting. id: %d' % o.id)
			return
		s = o.setting
		debug.debug (debug.MAIN, debug.INFO, 'I: Processing setting: %s' % s.name)
		# 1. execute ucrStop
		# replace placeholders
		if s.ucrStop != None and s.ucrStop.strip () != '':
			values = s.ucrStop
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
								debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStop))
								r.setError ('105')
								return
							found = True
							break
					if not found:
						debug.debug (debug.MAIN, debug.ERROR, 'E: unable to retrieve option: %s\n\tNot unsetting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStop))
						r.setError ('105')
						return
				else:
					if o.value != None:
						values = values.replace ('@%%@option:%s@%%@' % name, str (o.value))
					else:
						debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStop))
						r.setError ('105')
						return
			for invert, name in re_option_int2bool.findall (values):
				if name != s.name:
					# find setting that matches this name
					found = False
					options = r.options
					if r.profile:
						options += r.profile.options
					for opt in options:
						if opt.setting and opt.setting.name == name:
							replacement = True
							if opt.value == None or ( str(opt.value).isdigit() and int(str(opt.value)) == 0 ):
								replacement = False

							if invert:
								replacement = not replacement

							replacement = str(replacement).lower()
							values = values.replace('@%%@option-int2bool%s:%s@%%@' % (invert, name), replacement)

							found = True
							break
					if not found:
						debug.debug (debug.MAIN, debug.ERROR, 'E: unable to retrieve option: %s\n\tNot setting UCR variables: %s\n\tStopping further execution of commands.' % (name, s.ucrStop))
						r.setError ('105')
						return
				else:
					replacement = True
					if o.value == None or ( str(o.value).isdigit() and int(str(o.value)) == 0 ):
						replacement = False

					if invert:
						replacement = not replacement

					replacement = str(replacement).lower()
					values = values.replace('@%%@option-int2bool%s:%s@%%@' % (invert, name), replacement)

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
						r.setError ('125-%d' % retcode)
					else:
						r.setError ('115-%d' % retcode)
					return
			except Exception:
				debug.debug (debug.MAIN, debug.ERROR, '%s\nE: UCR command failed: %s' % (traceback.format_exc().replace('%','#'), ['univention-config-registry'] + values))
				if isinstance (o.relative, Profile):
					r.setError ('125-%d' % retcode)
				else:
					r.setError ('115-%d' % retcode)
				return

		# 2. execute cmdStop
		if s.cmdStop != None and s.cmdStop.strip () != '':
			# execute Distribution stop command for iterable reservations only
			# if this was the last iteration! Otherwise don't do anything
			if s.name == DISTRIBUTIONID and not r.wasLastRun():
				debug.debug (debug.MAIN, debug.INFO, 'I: Ignoring cmdStop setting "%s" for reservation "%s" because it was not the last run for this reservation' % (s.name, r.id))
				return

			# replace placeholders
			cmd = s.cmdStop
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
								debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot executing command: %s' % (name, s.cmdStop))
								r.setError ('105')
								return
							found = True
							break
					if not found:
						debug.debug (debug.MAIN, debug.ERROR, 'E: unable to retrieve option: %s\n\tNot executing command: %s' % (name, s.cmdStop))
						r.setError ('105')
						return
				else:
					if o.value != None:
						cmd = cmd.replace ('@%%@option:%s@%%@' % name, str (o.value))
					else:
						debug.debug (debug.MAIN, debug.ERROR, 'E: option %s without value\n\tNot executing command: %s' % (name, s.cmdStop))
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
						r.setError ('126-%d' % retcode)
					else:
						r.setError ('116-%d' % retcode)
					return
			except Exception:
				debug.debug (debug.MAIN, debug.ERROR, '%s\nE: command failed: %s' % (traceback.format_exc().replace('%','#'), s.cmdStop))
				if isinstance (o.relative, Profile):
					r.setError ('126-%d' % retcode)
				else:
					r.setError ('116-%d' % retcode)
				return

	def notify (self, event):
		_d = debug.function ('listener.stop.notify')
		if event.name != 'stop' or event.obj == None:
			return
		for r in event.obj:
			debug.debug (debug.MAIN, debug.INFO, 'I: Processing reservation: %s' % r.name)
			# 1. evaluate reservation settings
			for o in r.options:
				self._applyOptionStopCmd (r, o)
				if r.isError ():
					r.updateStatus ()
					break
			# 2. evaluate profile settings
			if not r.isError () and r.profile:
				p = r.profile
				debug.debug (debug.MAIN, debug.INFO, 'I: Processing profile: %s' % p.name)
				for o in p.options:
					self._applyOptionStopCmd (r, o)
					if r.isError ():
						r.updateStatus ()
						break
			if not r.isError ():
				if r.isIterable():
					if r.iterationEnd:
						# delta between the two dates
						iterationEnd = r.iterationEnd
						if isinstance(iterationEnd, datetime.datetime):
							iterationEnd = iterationEnd.date()
						date = datetime.date.today()
						d = iterationEnd - date
						## figure out whether today is one of these days
						# reservation is not repeated today if this is not equal 0
						# or today is after iterationEnd
						if d.days <= 0:
							r.setDone ()
						elif (d.days / r.iterationDays) > 0:
							r.setWaiting()
						else:
							r.setDone ()
				else:
					r.setDone ()
				r.updateStatus ()
