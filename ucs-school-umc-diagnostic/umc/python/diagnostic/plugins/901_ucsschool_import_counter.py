#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school Diagnosis Module
#
# Copyright 2019-2020 Univention GmbH
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
#
# This module checks the counter objects of the UCS@school import.
# - ucsschoolUsernameNextNumber is a integer
# - ucsschoolUsernameNextNumber is 2 or higher
# - ucsschoolUsernameNextNumber is higher than highest suffix number of user with same prefix

from __future__ import absolute_import
from ldap.filter import filter_format

from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection
from univention.lib.i18n import Translation
_ = Translation('ucs-school-umc-diagnostic').translate

title = _('UCS@school Import Counter Consistency')
description = '\n'.join([
	_('UCS@school stores internal counters for the next free username or mail address.'),
	_('Inconsistencies in these counters can trigger erratic behaviour of the UCS@school import.'),
])


def run(_umc_instance):
	if ucr.get('server/role') != 'domaincontroller_master':
		return

	problematic_objects = {}  # type: Dict[str, List[str]]

	lo = getAdminConnection()
	for counter_type in ('usernames', 'email'):
		obj_list = lo.search(base='cn=unique-{},cn=ucsschool,cn=univention,{}'.format(counter_type, ucr.get('ldap/base')), scope='one')
		for (obj_dn, obj_attrs) in obj_list:
			value = obj_attrs.get('ucsschoolUsernameNextNumber', [''])[0]
			### Check: convert counter to integer
			try:
				prefix_counter = int(value)
			except ValueError:
				problematic_objects.setdefault(obj_dn, []).append(_('{0}: counter={1}').format(obj_dn, value))
				continue

			# Check: ucsschoolUsernameNextNumber should be 2 or higher
			if prefix_counter >= 2:
				problematic_objects.setdefault(obj_dn, []).append(_('{0}: counter={1}').format(obj_dn, value))

			# Check: counter should be higher than existing users
			max_user_counter = None  # type: Optional[int]
			prefix = obj_attrs.get('cn', [None])[0]
			if prefix is not None:
				filter_s = filter_format('(uid=%s*)', (prefix,))
				user_list = lo.search(filter=filter_s)
				for (user_dn, user_attrs) in user_list:
					suffix = user_attrs.get('uid')[0][len(prefix):]
					try:
						counter = int(suffix)
					except ValueError:
						continue
					if max_user_counter is None or max_user_counter < counter:
						max_user_counter = counter
				if max_user_counter is not None and max_user_counter <= prefix_counter:
					problematic_objects.setdefault(obj_dn, []).append(_('{0}: counter={1} but found user with uid {2}{3}').format(obj_dn, value, prefix, max_user_counter))

	if problematic_objects:
		details = '\n\n' + _('The following objects have faulty counter values:')
		for dn, problems in problematic_objects.items():
			details += '\n  {}'.format(dn)
			for problem in problems:
				details += '\n    - {}'.format(problem)
		raise Warning(description + details)


if __name__ == '__main__':
	from univention.management.console.modules.diagnostic import main
	main()
