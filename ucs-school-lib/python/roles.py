#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school lib
#  module: UCS@school specific roles
#
# Copyright 2014-2018 Univention GmbH
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


class UnknownRole(Exception):
	pass


role_pupil = 'pupil'  # attention: there is also "role_student"
role_teacher = 'teacher'
role_staff = 'staff'

supported_roles = (role_pupil, role_teacher, role_staff)  # note: pupil SHOULD come first here for checks

role_computer_room = 'computer_room'
role_dc_backup = 'dc_backup'
role_dc_master = 'dc_master'
role_dc_slave = 'dc_slave'
role_dc_slave_admin = 'dc_slave_admin'
role_dc_slave_edu = 'dc_slave_edu'
role_dc_slave_edu_secondary = 'dc_slave_edu_secondary'
role_exam_user = 'exam_user'
role_memberserver = 'memberserver'
role_memberserver_admin = 'memberserver_admin'
role_memberserver_edu = 'memberserver_edu'
role_school = 'school'
role_school_admin = 'school_admin'
role_school_admin_group = 'school_admin_group'
role_school_class = 'school_class'
role_school_class_share = 'school_class_share'
role_single_master = 'single_master'
role_student = 'student'  # attention: there is also "role_pupil"
role_workgroup = 'workgroup'
role_workgroup_share = 'workgroup_share'

all_roles = (
	role_pupil, role_teacher, role_staff, role_computer_room, role_dc_backup, role_dc_master, role_dc_slave,
	role_dc_slave_admin, role_dc_slave_edu, role_dc_slave_edu_secondary, role_exam_user, role_memberserver,
	role_memberserver_admin, role_memberserver_edu, role_school, role_school_admin, role_school_admin_group,
	role_school_class, role_school_class_share, role_single_master, role_student, role_workgroup, role_workgroup_share,
)


def create_ucsschool_role_string(role, school):
	if role not in all_roles:
		raise UnknownRole('Unknown role {!r}.'.format(role))
	return '{}:school:{}'.format(role, school)
