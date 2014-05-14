#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014 Univention GmbH
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

from random import choice
import logging
from logging import StreamHandler, Logger
from logging.handlers import MemoryHandler
from contextlib import contextmanager
import subprocess

from psutil import process_iter

from univention.lib.policy_result import policy_result
from univention.lib.i18n import Translation
from univention.config_registry import ConfigRegistry

from univention.management.console.log import MODULE

# "global" translation for ucsschool.lib.models
_ = Translation('python-ucs-school').translate

# "global" ucr for ucsschool.lib.models
ucr = ConfigRegistry()
ucr.load()

logger = Logger(logging.DEBUG)

_module_logger_added = False

class ModuleLogger(object):
	def handle(self, record):
		if record.levelno <= logging.DEBUG:
			MODULE.info(record.msg)
		elif record.levelno <= logging.INFO:
			MODULE.process(record.msg)
		elif record.levelno <= logging.WARN:
			MODULE.warn(record.msg)
		else:
			MODULE.error(record.msg)

def add_stream_logger_to_schoollib(level=logging.DEBUG):
	stream_handler = StreamHandler()
	stream_handler.setLevel(level)
	logger.addHandler(stream_handler)
	return stream_handler

def add_module_logger_to_schoollib():
	global _module_logger_added
	if _module_logger_added:
		MODULE.info('add_module_logger_to_schoollib() should only be called once! Skipping...')
		return
	module_logger = ModuleLogger()
	memory_handler = MemoryHandler(-1, flushLevel=logging.DEBUG, target=module_logger)
	memory_handler.setLevel(logging.DEBUG)
	logger.addHandler(memory_handler)
	_module_logger_added = True
	return memory_handler

_pw_length_cache = {}
def create_passwd(length=8, dn=None):
	if dn:
		# get dn pw policy
		if not _pw_length_cache.get(dn):
			try:
				results, policies = policy_result(dn)
				_pw_length_cache[dn] = int(results.get('univentionPWLength', ['8'])[0])
			except Exception:
				pass
		length = _pw_length_cache.get(dn, length)

		# get ou pw policy
		ou = 'ou=' + dn[dn.find('ou=') + 3:]
		if not _pw_length_cache.get(ou):
			try:
				results, policies = policy_result(ou)
				_pw_length_cache[ou] = int(results.get('univentionPWLength', ['8'])[0])
			except Exception:
				pass
		length = _pw_length_cache.get(ou, length)

	chars = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!"$%&/()=?'
	return ''.join(choice(chars) for x in range(length))

def flatten(list_of_lists):
	# return [item for sublist in list_of_lists for item in sublist]
	# => does not work well for strings in list
	ret = []
	for sublist in list_of_lists:
		if isinstance(sublist, (list, tuple)):
			ret.extend(flatten(sublist))
		else:
			ret.append(sublist)
	return ret

@contextmanager
def stopped_notifier():
	def _run(args):
		process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		if stdout:
			logger.info(stdout)
		if stderr:
			logger.error(stderr)
		return process.returncode == 0

	notifier_running = False
	logger.warn('Stopping notifier')
	for process in process_iter():
		if process.name == 'univention-directory-notifier':
			notifier_running = True
			break
	if not notifier_running:
		logger.warn('Notifier is not running! Skipping')
	else:
		if _run(['sv', 'down', 'univention-directory-notifier']):
			logger.info('Notifier stopped')
		else:
			logger.error('Failed to stop notifier... Will try to start it in the end nonetheless')
	try:
		yield
	finally:
		logger.warn('Starting notifier')
		if not notifier_running:
			logger.warn('Notifier was not running! Skipping')
		else:
			if _run(['sv', 'up', 'univention-directory-notifier']):
				logger.info('Notifier started')
			else:
				logger.error('Failed to start notifier... Bad news! Better run "sv up univention-directory-notifier" manually!')

