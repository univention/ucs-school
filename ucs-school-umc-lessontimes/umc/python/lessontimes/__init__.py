#!/usr/bin/python2.6
#
# Univention Management Console
#  Configure the lessons times
#
# Copyright 2012 Univention GmbH
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

from univention.management.console.log import MODULE

from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import SchoolBaseModule
from ucsschool.lib.schoollessons import SchoolLessons

_ = Translation('ucs-school-umc-lessontimes').translate

class Instance(SchoolBaseModule):
	def init (self):
		SchoolBaseModule.init(self)
		self._lessons = SchoolLessons()

	def get(self, request):
		lessons = self._lessons.lessons

		result = []
		for lesson in lessons:
			result.append([lesson.name, str(lesson.begin), str(lesson.end)])

		self.finished(request.id, result)

	def set(self, request):
		# remove all lessons
		for lesson in self._lessons.lessons:
			self._lessons.remove(lesson)

		# add the new lessons
		for lesson in request.options.get('lessons', []):
			self._lessons.add(*lesson)
		self._lessons.save()

		self.finished(request.id, None)
