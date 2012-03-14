#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Common Python Library
#
# Copyright 2012 Univention GmbH
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

'''This module abstracts the handling of at-jobs, each job is encapsulated by
the class AtJob. Use the method add() in order to add a new command to the
queue of at-jobs. Use the methods list() and load() to get a list of all
registered jobs or to load a specific job given an ID, respectively. The module
uses time stamps in seconds for scheduling jobs.'''

import time
import subprocess
import re

# internal formatting strings and regexps
_regWhiteSpace = re.compile(r'\s+')
_dateTimeFormatRead = '%a %b %d %H:%M:%S %Y'
_dateTimeFormatWrite = '%Y-%m-%d %H:%M'
_timeFormatWrite = '%H:%M'
_dateFormatWrite = '%Y-%m-%d'


def add(cmd, execTime = None):
	'''Add a new command to the job queue given a time (in seconds) at which the
	job will be executed.'''

	# launch the at job directly
	atCmd = ['/usr/bin/at']
	if execTime:
		jobTime = time.strftime(_timeFormatWrite, time.localtime(execTime))
		jobDate = time.strftime(_dateFormatWrite, time.localtime(execTime))
		atCmd.extend([jobTime, jobDate])
	else:
		atCmd.append('now')
	p = subprocess.Popen(atCmd, stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.PIPE)

	# send the job to stdin
	p.stdin.write(cmd)
	p.stdin.close()

	# read the return value
	out = p.stdout.readline()
	p.stdout.close()

	# parse output and return job
	return _parseJob(out)

def list():
	'''Returns a list of all registered jobs.'''
	p = subprocess.Popen('/usr/bin/atq', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	jobs = []
	for line in p.stdout:
		ijob = _parseJob(line)
		if ijob:
			jobs.append(_parseJob(line))
	return jobs

def load(nr):
	'''Load a job given a particular ID. Returns None of job does not exist.'''
	result = [ p for p in list() if p.nr == nr ]
	if len(result):
		return result[0]
	return None

def _parseJob(string):
	'''Internal method to parse output of at-command.'''
	try:
		# parse string
		tmp = _regWhiteSpace.split(string)
		execTime = time.mktime(time.strptime(' '.join(tmp[1:6]), _dateTimeFormatRead))
		isRunning = tmp[6] == '='
		owner = tmp[7]
		nr = int(tmp[0])
	except (IndexError, ValueError), e:
		# parsing failed
		return None
	return AtJob(nr, owner, execTime, isRunning)


class AtJob(object):
	'''This class is an abstract representation of an at-job. Do not initiate
	the class directly, put use the methods provided in this module.'''

	#TODO: it would be nice to be able to register meta information within the job file

	# execTime: in seconds
	def __init__(self, nr, owner, execTime, isRunning):
		self.nr = nr
		self.owner = owner
		self.execTime = execTime
		self.isRunning = isRunning

	def __str__(self):
		t = time.strftime(_dateTimeFormatWrite, time.localtime(self.execTime))
		if self.isRunning:
			t = 'running'
		return 'Job #%d (%s)' % (self.nr, t)

	def __repr__(self):
		return self.__str__()

	def rm(self):
		'''Remove the job from the queue.'''
		p = subprocess.Popen(['/usr/bin/atrm', str(self.nr)], stdout = subprocess.PIPE, stderr = subprocess.PIPE)

