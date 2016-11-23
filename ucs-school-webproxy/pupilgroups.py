# -*- coding: utf-8 -*-
#
# Univention Directory Listener Module Pupilgroups
#  listener module: pupilgroups
#
# Copyright 2008-2016 Univention GmbH
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

from __future__ import absolute_import

import ldap
import listener

import univention.debug
import univention.admin.uldap
import univention.config_registry

from ucsschool.lib.models import School
from univention.config_registry.frontend import ucr_update

name = 'pupilgroups'
description = 'Map pupil group lists to UCR'
filter = "(objectClass=univentionGroup)"
attributes = ['memberUid']

all_local_schools = None
lo = None
keyPattern = 'proxy/filter/usergroup/%s'


def initialize():
	pass


def prerun():
	global all_local_schools, lo
	listener.setuid(0)
	try:
		lo, po = univention.admin.uldap.getMachineConnection(ldap_master=False)
		all_local_schools = [school.dn for school in School.get_all(lo)]
	except ldap.LDAPError:
		all_local_schools = None
		return
	finally:
		listener.unsetuid()


def handler(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.PROCESS, 'pupilgroups: dn: %s' % dn)
	configRegistry = univention.config_registry.ConfigRegistry()
	configRegistry.load()
	if all_local_schools is None:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'pupilgroups: Could not detect local schools')
	elif not any(dn.lower().endswith(',cn=groups,%s' % school.lower()) for school in all_local_schools):
		return  # the object doesn't belong to this school

	changes = {}
	if new and new.get('memberUid'):
		changes[keyPattern % new['cn'][0]] = ','.join(new.get('memberUid', []))
	elif old:  # old lost its last memberUid OR old was removed
		changes[keyPattern % old['cn'][0]] = None
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'pupilgroups: %r' % (changes,))

	listener.setuid(0)
	try:
		ucr_update(configRegistry, changes)
	finally:
		listener.unsetuid()


def postrun():
	global lo
	lo = None  # close LDAP connection
