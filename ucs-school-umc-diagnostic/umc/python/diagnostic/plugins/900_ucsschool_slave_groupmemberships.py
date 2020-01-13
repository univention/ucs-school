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
# Checks if the domaincontroller slave and memberserver objects are members
# of both groups:
#   DC-Edukativnetz + OU-$OU-DC-Edukativnetz
# or
#   DC-Verwaltungsnetz + OU-$OU-DC-Verwaltungsnetz
# or
#   Member-Edukativnetz + OU-$OU-Member-Edukativnetz
# or
#   Member-Verwaltungsnetz + OU-$OU-Member-Verwaltungsnetz
#
# WARNING: is is not (yet) checked if the group memberships match to the ucsschoolRole attribute!

from ldap.filter import filter_format

from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning
from univention.uldap import getAdminConnection
from univention.lib.i18n import Translation
_ = Translation('univention-management-console-module-diagnostic').translate

title = _('UCS@school Group Memberships of DC Slaves')
description = '\n'.join([
	_('UCS@school Domaincontroller Slave objects rely on the membership within certain UCS@school LDAP groups.'),
	_('Inconsistencies in these group memberships can trigger erratic behaviour of UCS@school.'),
])

def run(_umc_instance):
	if ucr.get('server/role') != 'domaincontroller_master':
		return

	problematic_objects = {}  # type: Dict[str, List[str]]

	lo = getAdminConnection()
	obj_list = lo.search(filter='(|(univentionObjectType=computers/domaincontroller_slave)(univentionObjectType=computers/memberserver))')
	for (obj_dn, obj_attrs) in obj_list:
		result = {
			'slave': {
				'edu': {
					'global_grp': False,
					'ou_grp': False,
				},
				'admin': {
					'global_grp': False,
					'ou_grp': False,
				},
			},
			'memberserver': {
				'edu': {
					'global_grp': False,
					'ou_grp': False,
				},
				'admin': {
					'global_grp': False,
					'ou_grp': False,
				},
			},
		}
		filter_s = filter_format('(&(objectClass=univentionGroup)(uniqueMember=%s))', (obj_dn,))
		grp_dn_list = lo.searchDn(filter=filter_s)
		for grp_dn in grp_dn_list:
			# check global groups
			if grp_dn == 'cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')):
				result['slave']['edu']['global_grp'] = True
			elif grp_dn == 'cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')):
				result['memberserver']['edu']['global_grp'] = True
			elif grp_dn == 'cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')):
				result['slave']['admin']['global_grp'] = True
			elif grp_dn == 'cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')):
				result['memberserver']['admin']['global_grp'] = True
			# check OU specific school groups
			if not grp_dn.startswith('cn=OU'):
				continue
			if grp_dn.endswith('-DC-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base'))):
				result['slave']['edu']['ou_grp'] = True
			elif grp_dn.endswith('-Member-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base'))):
				result['memberserver']['edu']['ou_grp'] = True
			elif grp_dn.endswith('-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base'))):
				result['slave']['admin']['ou_grp'] = True
			elif grp_dn.endswith('-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base'))):
				result['memberserver']['admin']['ou_grp'] = True

		# check for inconsistencies
		for hosttype in ('slave', 'memberserver'):
			for schooltype in ('edu', 'admin'):
				if result[hosttype][schooltype]['global_grp'] != result[hosttype][schooltype]['ou_grp']:
					problematic_objects.setdefault(obj_dn, []).append(
						_('Host object is member in global %s group but not in OU specific %s group (or the other way around)') % (schooltype, hosttype))
			if any(list(result[hosttype]['edu'].values()) + list(result[hosttype]['admin'].values())):
				if any(result[hosttype]['edu'].values()) == any(result[hosttype]['admin'].values()):
					problematic_objects.setdefault(obj_dn, []).append(
						_('Host object is member in edu groups AND in admin groups which is not allowed'))
		if obj_attrs.get('univentionObjectType', [''])[0] == 'computers/domaincontroller_slave':
			if any(list(result['memberserver']['edu'].values()) + list(result['memberserver']['admin'].values())):
				problematic_objects.setdefault(obj_dn, []).append(_('Slave object is member in memberserver groups'))
		else:
			if any(list(result['slave']['edu'].values()) + list(result['slave']['admin'].values())):
				problematic_objects.setdefault(obj_dn, []).append(_('Memberserver object is member in slave groups'))

	if problematic_objects:
		details = '\n\n' + _('The following objects have faulty group memberships:')
		for dn, problems in problematic_objects.items():
			details += '\n  {}'.format(dn)
			for problem in problems:
				details += '\n    - {}'.format(problem)
		raise Warning(description + details)


if __name__ == '__main__':
	from univention.management.console.modules.diagnostic import main
	main()
