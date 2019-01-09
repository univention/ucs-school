# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2019 Univention GmbH
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
Write the passwords of newly created users to a CSV file.
"""

from ucsschool.importer.factory import Factory
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.importer.writer.result_exporter import ResultExporter


class NewUserPasswordCsvExporter(ResultExporter):
	"""
	Export passwords of new users to a CSV file.
	"""
	field_names = ("username", "password", "role", "lastname", "firstname", "schools", "classes")

	def __init__(self, *arg, **kwargs):
		super(NewUserPasswordCsvExporter, self).__init__(*arg, **kwargs)
		self.factory = Factory()
		self.a_user = self.factory.make_import_user([])

	def get_iter(self, user_import):
		"""
		Return only the new users.
		"""
		li = list()
		map(li.extend, user_import.added_users.values())
		li.sort(key=lambda x: int(x['entry_count']) if isinstance(x, dict) else int(x.entry_count))
		return li

	def get_writer(self):
		"""
		Use the user result csv writer.
		"""
		return self.factory.make_user_writer(field_names=self.field_names)

	def serialize(self, user):
		if isinstance(user, ImportUser):
			pass
		elif isinstance(user, dict):
			user = self.a_user.from_dict(user)
		else:
			raise TypeError("Expected ImportUser or dict but got {}. Repr: {}".format(type(user), repr(user)))

		return dict(
			username=user.name,
			password=user.password,
			role=user.role_sting,
			lastname=user.lastname,
			firstname=user.firstname,
			schools=",".join(user.schools),
			classes=user.school_classes_as_str,
		)
