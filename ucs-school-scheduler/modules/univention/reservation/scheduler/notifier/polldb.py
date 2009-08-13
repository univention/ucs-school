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

from univention.reservation.dbconnector import Vacation, Reservation, RESERVATION_TABLE, WAITING, DONE, ERROR
from univention.reservation.scheduler.listener import AbstractListener
from univention.config_registry import ConfigRegistry
from univention.reservation.scheduler.notifier import AbstractEvent, StartEvent, StopEvent

import univention.debug as debug

import datetime
import traceback

ucr = ConfigRegistry ()
ucr.load ()

# Helper class
class Singleton (object):
	__single = None
	def __init__ (self):
		if Singleton.__single:
			raise Warning ('Singleton is already initialized')
		Singleton.__single = self
# Helper class END

# Helper functions
def filterIterations (date, reservation):
	"""
	@param	in	reservation		Reservation object
	@return	None if the reservation is not iterated today otherwise the
			reservation object is returned
	"""
	_d = debug.function ('notifier.polldb.filterIterations')
	if reservation == None:
		return None
	## this reservation is not iterated at all
	if reservation.iterationDays == None \
			or reservation.iterationDays == 0:
		## today is the last/only day where reservation is executed
		if (reservation.iterationEnd != None \
				and reservation.iterationEnd.date () == date) \
				or (reservation.startTime != None \
				and reservation.startTime.date () == date):
			return reservation
		return None
	## figure out on which days the reservation will be repeated
	# if iterationEnd == None it will be repeated till the end of days
	if reservation.iterationEnd:
		# delta between the two dates
		d = reservation.iterationEnd.date () - date
		## figure out whether today is one of these days
		# reservation is not repeated today if this is not equal 0
		# or today is after iterationEnd
		if d.days < 0 \
			or d.days % reservation.iterationDays != 0:
			return None
	## figure out whether this reservation is repeated during vacation time
	if reservation.iterateInVacations:
		return reservation
	## figure out whether today are vacations
	elif len (Vacation.getByDate (date)) > 0:
		# the current reservation is not repeated during vacation time
		return None
	# there are no vacations today
	return reservation

def getStartable (connection):
	"""
	Helper function that retrieves startable Reservations for the current
	datetime
	"""
	_d = debug.function ('notifier.polldb.getStartable')
	startable = []
	dt = datetime.datetime.now ()
	cursor = connection.cursor ()
	# The following select statement must select certain errors because not all
	# reservations with errors are stoppable!!
	# ITERATIONS: disabled for the moment
	#cursor.execute ("SELECT reservationID FROM %s WHERE TIME (startTime) <= TIME (%%s) AND TIME (endTime) > TIME (%%s) AND (status = %%s OR status = %%s OR status RLIKE '^%s 1(05|15|16|25|26)-[0-9]+$')" % (RESERVATION_TABLE, ERROR), (dt, dt, WAITING, DONE))
	cursor.execute ("SELECT reservationID FROM %s WHERE startTime <= %%s AND endTime > %%s AND status = %%s" % RESERVATION_TABLE, (dt, dt, WAITING))
	for res in cursor.fetchall ():
		try:
			startable.append (Reservation.get (res[0]))
			# ITERATIONS: disabled for the moment
			#r = filterIterations (dt.date (), Reservation.get (res[0]))
			#if r:
			#	startable.append (r)
		except Exception:
			debug.debug (debug.MAIN, debug.ERROR, '%s\nE: Reservation does not exist. ID: %s' % (traceback.format_exc().replace('%','#'), res[0]))
	cursor.close ()
	return startable

def getStoppable (connection):
	"""
	Helper function that retrieves stoppable Reservations for the current
	datetime
	"""
	_d = debug.function ('notifier.polldb.getStoppable')
	stoppable = []
	dt = datetime.datetime.now ()
	cursor = connection.cursor ()
	# WARNING: iterationEnd and iterationDays are not respected! This function
	# catches everything that's running and restores a sane state
	# The following select statement must select certain errors because not all
	# reservations with errors are stoppable!!
	# ITERATIONS: disabled for the moment
	#cursor.execute ("SELECT reservationID FROM %s WHERE TIME (endTime) < TIME (%%s) AND (status <> %%s AND status <> %%s OR status RLIKE '^%s 1(05|10|11|20|21)-[0-9]+$')" % (RESERVATION_TABLE, ERROR), (dt, WAITING, DONE))
	cursor.execute ("SELECT reservationID FROM %s WHERE endTime < %%s AND (status <> %%s AND status <> %%s)" % RESERVATION_TABLE, (dt, WAITING, DONE))
	for res in cursor.fetchall ():
		try:
			stoppable.append (Reservation.get (res[0]))
		except Exception:
			debug.debug (debug.MAIN, debug.ERROR, '%s\nE: Reservation does not exist. ID: %s' % (traceback.format_exc().replace('%','#'), res[0]))
	cursor.close ()
	return stoppable
# Helper functions END

class PollDB (Singleton):
	"""
	univention-scheduler notifier. This class polls the reservation database on
	a regular basis (UCR scheduler/interval) and retrieves reservations that
	need action.
	"""
	def __init__ (self):
		_d = debug.function ('scheduler.notifier.polldb.PollDB.__init__')
		super (PollDB, self).__init__ ()
		self._listeners = []

	@classmethod
	def get (cls):
		"""
		Get an instance of PollDB
		"""
		_d = debug.function ('notifier.polldb.PollDB.get')
		if hasattr (PollDB, '__single'):
			return PollDB.__single
		else:
			return PollDB ()

	def poll (self, connection):
		"""
		Poll database an notify listeners
		"""
		# according to the specification first the reservations must be stopped
		# and than started
		_d = debug.function ('notifier.polldb.PollDB.poll')
		self._notify_listeners (StopEvent (getStoppable (connection)))
		self._notify_listeners (StartEvent (getStartable (connection)))

	def _notify_listeners (self, event):
		_d = debug.function ('notifier.polldb.PollDB._notify_listeners')
		if not isinstance (event, AbstractEvent):
			raise ValueError ('event object must be of class AbstractEvent but it is: %s' % repr (event))
		for l in self._listeners:
			if isinstance (l, AbstractListener):
				try:
					l.notify (event)
				except Exception:
					debug.debug (debug.MAIN, debug.ERROR, '%s\nE: Notifier failed' % (traceback.format_exc().replace('%','#'), ))

	def register (self, listener):
		"""
		Register listener
		"""
		_d = debug.function ('notifier.polldb.PollDB.register')
		if isinstance (listener, AbstractListener) \
				and self._listeners.count (listener) == 0:
			self._listeners.append (listener)
			return listener
		raise ValueError ('listener object must be of class AbstractListener but it is: %s' % repr (listener))

	def unregister (self, listener):
		"""
		Unregister listener
		"""
		_d = debug.function ('notifier.polldb.PollDB.unregister')
		if self._listeners.count (listener) > 0:
			self._listeners.remove (listener)
			return listener
		return None
