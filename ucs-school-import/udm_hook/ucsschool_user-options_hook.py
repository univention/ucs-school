#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
UCS@school UDM-hook to prevent invalid combinations of user options
"""
# Copyright 2016 Univention GmbH
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

import univention.debug as ud
from univention.admin.hook import simpleHook
import univention.admin.uexceptions
import univention.admin.localization

translation=univention.admin.localization.translation('univention.admin.hooks.d.uscchooloptions')
_=translation.translate


blacklisted_option_additions = {
	"ucsschoolAdministrator": ["ucsschoolExam", "ucsschoolStudent"],
	"ucsschoolExam": ["ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolStudent", "ucsschoolTeacher"],
	"ucsschoolStaff": ["ucsschoolExam", "ucsschoolStudent"],
	"ucsschoolStudent": ["ucsschoolExam", "ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"],
	"ucsschoolTeacher": ["ucsschoolExam", "ucsschoolStudent"],
}

error_msg = _("Illegal combination of options. %(option)s cannot be activated together with %(illegals)s.")


class UcsschoolUserOptionsHook(simpleHook):
	type = "UcsschoolUserOptionsHook"

	def hook_ldap_pre_modify(self, module):
		new_options = set(module.options) - set(module.old_options)
		new_ucsschool_options = set(blacklisted_option_additions.keys()).intersection(new_options)
		for option in new_ucsschool_options:
			illegal_options = blacklisted_option_additions[option]
			if any([opt in illegal_options for opt in module.options]):
				ud.debug(ud.ADMIN, ud.WARN, error_msg % {"option": option, "illegals": ", ".join(illegal_options)})
				raise univention.admin.uexceptions.valueError(error_msg %
					{"option": option, "illegals": ", ".join(illegal_options)})
