#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
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
# This module checks the UCS@school OU objects:
# - only OUs with correct objectclass ("ucsschoolOrganizationalUnit") are checked
# - is ucsschoolRole set?
# - is ucsschoolRole set to "school:school:$OU"?
# - is a displayName set?
# - is a HomeShareFileServer and a ClassShareFileServer set?
# - is a HomeShareFileServer and a ClassShareFileServer (not) set to the DC master in multi/single server environment?

from __future__ import absolute_import
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection
from univention.lib.i18n import Translation
_ = Translation('ucs-school-umc-diagnostic').translate

title = _('UCS@school OU Consistency')
description = '\n'.join([
	_('UCS@school stores information about schools within the LDAP objects. One of these objects is the school OU object.'),
	_('Inconsistencies in these OU object can trigger erratic behaviour of the UCS@school import.'),
])


def run(_umc_instance):
	if ucr.get('server/role') != 'domaincontroller_master':
		return

	problematic_objects = {}  # type: Dict[str, List[str]]

	lo = getAdminConnection()

	ou_list = lo.search(filter='ou=*', base=ucr.get('ldap/base'), scope='one')
	for (ou_dn, ou_attrs) in ou_list:
		if 'ucsschoolOrganizationalUnit' not in ou_attrs.get('objectClass', []):
			continue

		ucsschoolRoles = ou_attrs.get('ucsschoolRole', [])
		if not ucsschoolRoles:
			problematic_objects.setdefault(ou_dn, []).append(_('ucsschoolRole is not set'))
		if not any(x.startswith('school:school:{}'.format(ou_attrs.get('ou')[0])) for x in ucsschoolRoles):
			problematic_objects.setdefault(ou_dn, []).append(_('ucsschoolRole "school:school:{0}" not found').format(ou_attrs.get('ou')[0]))

		if not ou_attrs.get('displayName', [None])[0]:
			problematic_objects.setdefault(ou_dn, []).append(_('displayName is not set'))

		for attr_name in ('ucsschoolHomeShareFileServer', 'ucsschoolClassShareFileServer'):
			value = ou_attrs.get(attr_name, [None])[0]
			if not value:
				problematic_objects.setdefault(ou_dn, []).append(_('{0} is not set').format(attr_name))
			if not lo.search(base=value, scope='base'):
				problematic_objects.setdefault(ou_dn, []).append(_('{0} contains invalid value: {1!r}').format(attr_name, value))
			if ucr.is_true('ucsschool/singlemaster', False) and value != ucr.get('ldap/hostdn'):  # WARNING: this line expects that check is performed on the DC master!
				problematic_objects.setdefault(ou_dn, []).append(_('{0} is not set to master in a UCS@school single server environment').format(attr_name))
			if not ucr.is_true('ucsschool/singlemaster', False) and value == ucr.get('ldap/hostdn'):  # WARNING: this line expects that check is performed on the DC master!
				problematic_objects.setdefault(ou_dn, []).append(_('{0} is set to master in a UCS@school multi server environment').format(attr_name))

	if problematic_objects:
		details = '\n\n' + _('The following problems were found:')
		for dn, problems in problematic_objects.items():
			details += '\n\n  {}'.format(dn)
			for problem in problems:
				details += '\n&nbsp;&nbsp;&nbsp;- {}'.format(problem)
		raise Warning(description + details)


if __name__ == '__main__':
	from univention.management.console.modules.diagnostic import main
	main()
