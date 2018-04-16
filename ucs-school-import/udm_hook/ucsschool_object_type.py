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


# this should be in ucsschool.lib.schoolldap, but I'm having trouble importing it
object_type_to_object_classes = {
	'administrator_group': ('ucsschoolAdministratorGroup',),  # only if 'ucsschoolAdministratorGroup' in module.options
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


# TODO: need a listener module for administrator_group/ucsschoolAdministratorGroup,
# because the udm-hook doesn't react to changes of options


class UcsschoolObjectType(simpleHook):
	type = "UcsschoolObjectType"

	def hook_ldap_addlist(self, obj, al=None):
		if al is None:
			al = []
		if obj.info.get('ucsschoolObjectType') and not 'objectClass' in [a[0] for a in al]:
			al, _ml = self.add_object_class(obj, al, None)
		return al

	def hook_ldap_modlist(self, obj, ml=[]):
		if obj.info.get('ucsschoolObjectType') and obj.info.get('ucsschoolObjectType') != obj.oldinfo.get('ucsschoolObjectType'):
			_al, ml = self.add_object_class(obj, None, ml)
		return ml

	def add_object_class(self, obj, al, ml):
		oc_add_list = None
		if al:
			for attr, add_val in [it for it in al if it[0] == 'objectClass' and len(it) == 2]:
				oc_add_list = add_val
		elif ml:
			for attr, old_val, new_val in [it for it in ml if it[0] == 'objectClass' and len(it) == 3]:
				oc_add_list = new_val
		if oc_add_list:
			for oc in object_type_to_object_classes[obj.info['ucsschoolObjectType']]:
				if oc not in oc_add_list:
					oc_add_list.append(oc)
		return al, ml
