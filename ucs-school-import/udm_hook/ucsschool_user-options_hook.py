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

translation = univention.admin.localization.translation("univention-admin-hooks-ucsschool_user-options_hook")
_ = translation.translate


blacklisted_option_combinations = {
	"ucsschoolAdministrator": {"ucsschoolExam", "ucsschoolStudent"},
	"ucsschoolExam": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
	"ucsschoolStaff": {"ucsschoolExam", "ucsschoolStudent"},
	"ucsschoolStudent": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
	"ucsschoolTeacher": {"ucsschoolExam", "ucsschoolStudent"},
}
option_names = {
	"ucsschoolAdministrator": _("UCS@school Administrator"),
	"ucsschoolExam": _("UCS@school Examuser"),
	"ucsschoolStaff": _("UCS@school staff"),
	"ucsschoolStudent": _("UCS@school student"),
	"ucsschoolTeacher": _("UCS@school teacher")
}
error_msg = _("Illegal combination of options. %(option)s cannot be activated together with %(illegals)s.")


class UcsschoolUserOptionsHook(simpleHook):
	type = "UcsschoolUserOptionsHook"

	@staticmethod
	def check_options(module):
		users_options = set(module.options)
		ucsschool_options = users_options.intersection(set(blacklisted_option_combinations.keys()))
		for option in ucsschool_options:
			illegal_options = blacklisted_option_combinations[option]
			if illegal_options.intersection(users_options):
				msg = error_msg % {
					"option": option_names[option],
					"illegals": ", ".join([option_names[o] for o in illegal_options])
				}
				ud.debug(ud.ADMIN, ud.WARN, msg)
				raise univention.admin.uexceptions.valueError(msg)

	def hook_ldap_pre_create(self, module):
		self.check_options(module)

	def hook_ldap_pre_modify(self, module):
		self.check_options(module)
