# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
ImportUser subclass for import using legacy CSV format.
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


from ucsschool.importer.models.import_user import ImportStaff, ImportStudent, ImportTeacher,\
	ImportTeachersAndStaff, ImportUser
from ucsschool.importer.exceptions import UnkownAction


class LegacyImportUser(ImportUser):
	def make_disabled(self):
		"""
		Handled in LegacyCsvReader.handle_input(). Overwriting here, so
		changes in ImportUser do not change behavior of LegacyImportUser.
		"""
		pass

	def make_classes(self):
		"""
		Remove school name prefix from class names.
		"""
		super(LegacyImportUser, self).make_classes()
		if isinstance(self, ImportStaff):
			return
		prefix_len = len("{}-".format(self.school))
		# FIXME when/if self.school_class becomes a list instead of a string
		self.school_class = ",".join([c[prefix_len:] for c in self.school_class.split(",")])

	def run_checks(self, check_username=False):
		"""
		Action must already be configured in CSV.
		"""
		super(LegacyImportUser, self).run_checks()

		if self.action and self.action not in ["A", "D", "M"]:
			raise UnkownAction("Unknown action '{}'.".format(self.action))


class LegacyImportStudent(LegacyImportUser, ImportStudent):
	pass


class LegacyImportStaff(LegacyImportUser, ImportStaff):
	pass


class LegacyImportTeacher(LegacyImportUser, ImportTeacher):
	pass


class LegacyImportTeachersAndStaff(LegacyImportUser, ImportTeachersAndStaff):
	pass
