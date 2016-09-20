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

from univention.admin.hook import simpleHook
import univention.admin.modules
import univention.admin.uexceptions
import univention.admin.localization

translation = univention.admin.localization.translation("univention-admin-hooks-ucsschool_user_options")
_ = translation.translate


option_blacklist = {
	"ucsschoolAdministrator": {"ucsschoolExam", "ucsschoolStudent"},
	"ucsschoolExam": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
	"ucsschoolStaff": {"ucsschoolExam", "ucsschoolStudent"},
	"ucsschoolStudent": {"ucsschoolAdministrator", "ucsschoolStaff", "ucsschoolTeacher"},
	"ucsschoolTeacher": {"ucsschoolExam", "ucsschoolStudent"},
}


class UcsschoolUserOptions(simpleHook):
	type = "UcsschoolUserOptions"

	@staticmethod
	def check_options(module):
		def _option_name(option):
			return univention.admin.modules.get(module.module).options[option].short_description
		for option, invalid_options in option_blacklist.items():
			if option not in module.options:
				continue
			if invalid_options & set(module.options):
				raise univention.admin.uexceptions.invalidOptions(_("%(option)s cannot be activated together with %(illegals)s.") % {
					"option": _option_name(option),
					"illegals": ", ".join(map(_option_name, (invalid_options & set(module.options))))
				})

	def hook_ldap_pre_create(self, module):
		self.check_options(module)

	def hook_ldap_pre_modify(self, module):
		self.check_options(module)
