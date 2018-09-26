#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2018 Univention GmbH
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

import inspect
from functools import wraps

from univention.management.console.log import MODULE
from univention.management.console.ldap import get_machine_connection, get_admin_connection, get_user_connection


__bind_callback = None


def set_bind_function(bind_callback):
	global __bind_callback
	__bind_callback = bind_callback


def set_credentials(dn, passwd):
	set_bind_function(lambda lo: lo.lo.bind(dn, passwd))


USER_READ = 'ldap_user_read'
USER_WRITE = 'ldap_user_write'
MACHINE_READ = 'ldap_machine_read'
MACHINE_WRITE = 'ldap_machine_write'
ADMIN_WRITE = 'ldap_admin_write'


def LDAP_Connection(*connection_types):
	"""This decorator function provides access to internally cached LDAP connections that can
	be accessed via adding specific keyword arguments to the function.

	The function which uses this decorator may specify the following additional keyword arguments:
	ldap_position: a univention.admin.uldap.position instance valid ldap position.
	ldap_user_read: a read only LDAP connection to the local LDAP server authenticated with the currently used user
	ldap_user_write: a read/write LDAP connection to the master LDAP server authenticated with the currently used user
	ldap_machine_read: a read only LDAP connection to the local LDAP server authenticated with the machine account
	ldap_machine_write: a read/write LDAP connection to the master LDAP server authenticated with the machine account
	ldap_admin_write: a read/write LDAP connection to the master LDAP server authenticated with cn=admin account
	(deprecated!) search_base: a SchoolSearchBase instance which is bound to the school of the user or machine.

	This decorator can only be used after set_bind_function() has been executed.

	example:
	@LDAP_Connection()
	def do_ldap_stuff(arg1, arg2, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		...
		ldap_user_read.searchDn(..., position=ldap_position)
		...
	"""

	if not connection_types:  # TODO: remove. We still need this for backwards compatibility with other broken decorators
		connection_types = (USER_READ,)

	def inner_wrapper(func):
		argspec = inspect.getargspec(func)
		argnames = set(argspec.args) | set(connection_types)
		add_search_base = 'search_base' in argspec.args or argspec.keywords is not None
		add_position = 'ldap_position' in argspec.args or argspec.keywords is not None

		def wrapper_func(*args, **kwargs):
			# set LDAP keyword arguments
			po = None
			if ADMIN_WRITE in argnames:
				kwargs[ADMIN_WRITE], po = get_admin_connection()
			if MACHINE_WRITE in argnames:
				kwargs[MACHINE_WRITE], po = get_machine_connection(write=True)
			if MACHINE_READ in argnames:
				kwargs[MACHINE_READ], po = get_machine_connection(write=False)
			if USER_WRITE in argnames:
				kwargs[USER_WRITE], po = get_user_connection(bind=__bind_callback, write=True)
			if USER_READ in argnames:
				kwargs[USER_READ], po = get_user_connection(bind=__bind_callback, write=False)
			if add_position:
				kwargs['ldap_position'] = po
			if add_search_base:
				MODULE.warn('Using deprecated LDAP_Connection.search_base parameter.')
				from ucsschool.lib.models import School
				from univention.management.console.protocol.message import Message
				if len(args) > 1 and isinstance(args[1], Message) and isinstance(args[1].options, dict) and args[1].options.get('school'):
					school = args[1].options['school']
				elif LDAP_Connection._school is None:
					lo = kwargs.get(USER_READ) or kwargs.get(USER_WRITE) or kwargs.get(MACHINE_READ) or kwargs.get(MACHINE_WRITE) or kwargs.get(ADMIN_WRITE)
					try:
						school = School.from_binddn(lo)[0].name
						MODULE.info('Found school %r as ldap school base' % (school,))
					except IndexError:
						MODULE.warn('All Schools: ERROR, COULD NOT FIND ANY OU!!!')
						school = ''
					LDAP_Connection._school = school
				else:
					school = LDAP_Connection._school
				kwargs['search_base'] = School.get_search_base(school)
			return func(*args, **kwargs)
		return wraps(func)(wrapper_func)
#		def decorated(*args, **kwargs):
#			try:
#				return wrapper_func(*args, **kwargs)
#			except ldap.INVALID_CREDENTIALS:
#				reset_connection_cache()
#				return wrapper_func(*args, **kwargs)
#		return wraps(func)(decorated)
	return inner_wrapper


LDAP_Connection._school = None
