#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2020 Univention GmbH
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

"""
UCS@school legacy import tool cmdline frontend.
"""

from ..frontend.user_import_cmdline import UserImportCommandLine
from ..utils.utils import nullcontext
from .legacy_user_import_parse_cmdline import LegacyUserImportParseUserImportCmdline
from ucsschool.lib.models.utils import stopped_notifier


class LegacyUserImportCommandLine(UserImportCommandLine):

	def parse_cmdline(self):
		parser = LegacyUserImportParseUserImportCmdline()
		self.args = parser.parse_cmdline()

	@property
	def configuration_files(self):
		"""
		Add legacy user import specific configuration files.

		:return: list of filenames
		:rtype: list(str)
		"""
		res = super(LegacyUserImportCommandLine, self).configuration_files
		res.append("/usr/share/ucs-school-import/configs/user_import_legacy_defaults.json")
		res.append("/var/lib/ucs-school-import/configs/user_import_legacy.json")
		if self.args.conffile:
			res.append(self.args.conffile)
		return res

	async def do_import(self):
		importer = self.factory.make_mass_importer(self.config["dry_run"])
		with nullcontext() if self.config['dry_run'] else stopped_notifier():
			await importer.import_users()
		self.errors = importer.errors
