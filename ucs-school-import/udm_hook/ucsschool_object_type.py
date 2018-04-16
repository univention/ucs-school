#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
UDM hook to add a specific ucsschoolObject object class to each object
"""
# Copyright 2018 Univention GmbH
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
import univention.admin.uexceptions
try:
	# the UDM hook may be distributed in the domain before updating the
	# python-ucs-school package, so we have a static copy here as fallback
	from ucsschool.lib import object_type_to_object_classes
except ImportError:
	object_type_to_object_classes = {
		'administrator_group': ('ucsschoolAdministratorGroup',),
		'administrator_user': ('ucsschoolAdministrator',),
		'class_share': ('ucsschoolClassShare',),
		'computer_room': ('ucsschoolComputerRoom',),
		'exam_student': ('ucsschoolExam',),
		'school_class': ('ucsschoolSchoolClass',),
		'staff': ('ucsschoolStaff',),
		'student': ('ucsschoolStudent',),
		'teacher': ('ucsschoolTeacher',),
		'teacher_and_staff': ('ucsschoolTeacher', 'ucsschoolStaff'),
		'work_group': ('ucsschoolWorkGroup',)
	}


class UcsschoolObjectType(simpleHook):
	type = 'UcsschoolObjectType'
	ucsschool_user_options = {
		'ucsschoolAdministrator', 'ucsschoolExam', 'ucsschoolStaff', 'ucsschoolStudent', 'ucsschoolTeacher'
	}
	top_ocs = {'ucsschoolObject', 'ucsschoolType'}

	def hook_open(self, obj):
		self.old_options = self.ucsschool_user_options.intersection(set(obj.options))

	def hook_ldap_addlist(self, obj, al=None):
		"""
		Add objectClasses if an object has ucsschoolObjectType set.
		"""
		if al is None:
			al = []
		if al and obj.info.get('ucsschoolObjectType'):
			ocs = []
			for ot in obj.info['ucsschoolObjectType']:
				ocs.extend(object_type_to_object_classes[ot])
			for attr, add_val in [it for it in al if it[0] == 'objectClass' and len(it) == 2]:
				for oc in ocs:
					if oc not in add_val:
						add_val.append(oc)
		return al

	def hook_ldap_modlist(self, obj, ml=None):
		"""
		Update ucsschoolObjectType if the options of a user change.
		"""
		if ml is None:
			ml = []

		if 'ucsschoolType' not in obj.oldattr.get('objectClass'):
			# not interested in non-UCS@school users
			return ml

		new_options = self.ucsschool_user_options.intersection(set(obj.options))

		if not new_options:
			raise univention.admin.uexceptions.invalidOptions('It is not allowed to remove all UCS@school options.')

		if self.old_options != new_options:
			# ucsschool options were added/removed
			attr = 'ucsschoolObjectType'
			old_val = obj.info.get('ucsschoolObjectType', [])

			# modify existing entry in ml or append new modification
			changes = [it for it in ml if it[0] == attr]
			if changes:
				# modify entries in ml
				for item in changes:
					if len(item) == 2:
						attr, new_val = item
					else:
						attr, old_val, new_val = item

					ml.remove(item)
					ml.append((attr, old_val, self.options_to_object_type(new_options)))
			else:
				# no change to attr listed in ml
				ml.append((attr, old_val, self.options_to_object_type(new_options)))
		return ml

	@staticmethod
	def options_to_object_type(ocs):  # type: (Iterable[str]) -> List[str]
		res = []
		if 'ucsschoolAdministrator' in ocs:
			res.append('administrator_user')
		if 'ucsschoolStudent' in ocs:
			if 'ucsschoolExam' in ocs:
				res.append('exam_student')
			else:
				res.append('student')
		elif 'ucsschoolTeacher' in ocs:
			if 'ucsschoolStaff' in ocs:
				res.append('teacher_and_staff')
			else:
				res.append('teacher')
		if 'ucsschoolStaff' in ocs and 'ucsschoolTeacher' not in ocs:
			res.append('staff')
		return res
