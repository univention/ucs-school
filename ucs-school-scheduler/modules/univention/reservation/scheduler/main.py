#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2010 Univention GmbH
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

import os
import signal
import sys
import time
import traceback

import univention.debug as debug
from univention.config_registry import ConfigRegistry

from univention.reservation.dbconnector import connect as dbconnect, disconnect as dbdisconnect
from univention.reservation.scheduler.listener.start import SchedulerStartListener
from univention.reservation.scheduler.listener.stop import SchedulerStopListener
from univention.reservation.scheduler.notifier.polldb import PollDB
import univention.reservation.scheduler


def daemon ():
	try:
		pid = os.fork()
	except OSError, e:
		print 'Daemon Mode Error: %s' % e.strerror

	if (pid == 0):
		os.setsid()
		signal.signal(signal.SIGHUP, signal.SIG_IGN)
		try:
			pid = os.fork()
		except OSError, e:
			print 'Daemon Mode Error: %s' % e.strerror
		if (pid == 0):
			os.chdir("/")
			os.umask(0)
		else:
			pf=open('/var/run/ucs-school-scheduler', 'w+')
			pf.write(str(pid))
			pf.close()
			os._exit(0)
	else:
		os._exit(0)

	try:
		maxfd = os.sysconf("SC_OPEN_MAX")
	except (AttributeError, ValueError):
		maxfd = 256       # default maximum

	for fd in range(0, maxfd):
		try:
			os.close(fd)
		except OSError:   # ERROR (ignore)
			pass

	os.open("/dev/null", os.O_RDONLY)
	os.open("/dev/null", os.O_RDWR)

def connect ():
	daemon()
	univention.reservation.scheduler.init_debug ()
	_d = debug.function ('scheduler.main.connect')

	ucr = ConfigRegistry ()
	ucr.load ()

	# default values
	INTERVAL   = int (ucr.get ('scheduler/interval', 20)) # scan interval in seconds
	HOST       = ucr.get ('scheduler/sql/server', 'localhost')
	PORT       = int (ucr.get ('scheduler/sql/port', 3306))
	BACKEND    = ucr.get ('scheduler/sql/backend', 'mysql')
	USER       = 'reservation'
	DB         = 'reservation'
	PASSWORD = ''
	try:
		f = open ('/etc/reservation-sql.secret', 'r')
		PASSWORD = f.read ()
		if len (PASSWORD) > 0 and PASSWORD[-1] == '\n':
			PASSWORD = PASSWORD[:-1]
		f.close ()
	except Exception:
		print 'Unable to retrieve password from /etc/reservation-sql.secret!'
		univention.reservation.scheduler.close_debug ()
		sys.exit (1)
	CONNECTION = dbconnect (host=HOST, port=PORT, user=USER, passwd=PASSWORD, db=DB)

	polldb = PollDB.get ()
	start = SchedulerStartListener ()
	stop = SchedulerStopListener ()
	polldb.register (start)
	polldb.register (stop)

	while True:
		try:
			polldb.poll (CONNECTION)
		except Exception:
			debug.debug (debug.MAIN, debug.ERROR, '%s\nF: poll failed.' % traceback.format_exc().replace('%','#'))
			dbdisconnect ()
			CONNECTION = dbconnect (host=HOST, port=PORT, user=USER, passwd=PASSWORD, db=DB)
		time.sleep (INTERVAL)

def main():
	while True:
		try:
			connect()
			debug.debug (debug.MAIN, debug.DEBUG, 'D: Connected.')
		except:
			debug.debug (debug.MAIN, debug.ERROR, '%s\nE: Connect failed.' % traceback.format_exc().replace('%','#'))
			time.sleep(30)

	univention.reservation.scheduler.close_debug ()

if __name__ == "__main__":
	main()
