# -*- coding: utf-8 -*-
#
# Univention Directory Listener Module Pupilgroups
#  listener module: pupilgroups
#
# Copyright 2008-2012 Univention GmbH
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

__package__=''		# workaround for PEP 366
import listener
import univention.config_registry
import univention.debug
import re

name='pupilgroups'
description='Map pupil group lists to UCR'
filter="(objectClass=univentionGroup)"
attributes=['memberUid']

dnPattern=re.compile('cn=schueler,cn=groups,ou=[^,]+,dc=', re.I)
keyPattern='proxy/filter/usergroup/%s'

def initialize():
	pass

def handler(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'pupilgroups: dn: %s' % dn)
	configRegistry = univention.config_registry.ConfigRegistry()
	configRegistry.load()
	ignore_users = set([ x.strip() for x in re.split('[, ]+', configRegistry.get('proxy/filter/ignore/users','')) if x.strip() ])
	protected_groups = set([ x.strip() for x in re.split('[, ]+', configRegistry.get('proxy/filter/protected/groups','')) if x.strip() ])
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'pupilgroups: ignore_users=%s' % str(ignore_users))
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'pupilgroups: ignore_users=%s' % str(protected_groups))
	listener.setuid(0)
	try:
		if dnPattern.search(dn):
			if new and new.has_key('memberUid'):
				grp=new['cn'][0].replace(' ','_')
				key=keyPattern % grp
				# remove ignore_users from list of members
				result_members = set(new['memberUid'])
				if not grp in protected_groups:
					result_members -= ignore_users
				keyval = '%s=%s' % (key, ','.join(result_members))
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'pupilgroups: %s' % keyval)
				univention.config_registry.handler_set( [ keyval.encode() ] )
			elif old:	# old lost its last memberUid OR old was removed
				key = keyPattern % old['cn'][0].replace(' ','_')
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'pupilgroups: %s' % key)
				univention.config_registry.handler_unset( [ key.encode() ] )
	finally:
		listener.unsetuid()

def postrun():
	pass
