# -*- coding: utf-8 -*-
#
# UCS@school lib
#  module: UCS@school specific roles
#
# Copyright 2014-2021 Univention GmbH
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


class UcsschoolRoleStringError(Exception):
    pass


class UnknownRole(UcsschoolRoleStringError):
    pass


class UnknownContextType(UcsschoolRoleStringError):
    pass


class InvalidUcsschoolRoleString(UcsschoolRoleStringError):
    pass


role_pupil = "pupil"  # attention: there is also "role_student"
role_teacher = "teacher"
role_staff = "staff"

supported_roles = (role_pupil, role_teacher, role_staff)  # note: pupil SHOULD come first here for checks

role_computer_room = "computer_room"
role_dc_backup = "dc_backup"
role_dc_master = "dc_master"
role_dc_slave = "dc_slave"
role_dc_slave_admin = "dc_slave_admin"
role_dc_slave_edu = "dc_slave_edu"
role_teacher_computer = "teacher_computer"
role_win_computer = "win_computer"
role_mac_computer = "mac_computer"
role_ip_computer = "ip_computer"
role_linux_computer = "linux_computer"
role_ubuntu_computer = "ubuntu_computer"
role_exam_user = "exam_user"
role_marketplace_share = "marketplace_share"
role_memberserver = "memberserver"
role_memberserver_admin = "memberserver_admin"
role_memberserver_edu = "memberserver_edu"
role_school = "school"
role_school_admin = "school_admin"
role_school_admin_group = "school_admin_group"
role_school_domain_group = "school_domain_group"
role_school_teacher_group = "school_teacher_group"
role_school_staff_group = "school_staff_group"
role_school_student_group = "school_student_group"
role_school_class = "school_class"
role_school_class_share = "school_class_share"
role_single_master = "single_master"
role_student = "student"  # attention: there is also "role_pupil"
role_workgroup = "workgroup"
role_workgroup_share = "workgroup_share"
role_computer_room_backend_veyon = "veyon-backend"

all_roles = (
    role_pupil,
    role_teacher,
    role_staff,
    role_computer_room,
    role_dc_backup,
    role_dc_master,
    role_dc_slave,
    role_dc_slave_admin,
    role_dc_slave_edu,
    role_exam_user,
    role_marketplace_share,
    role_memberserver,
    role_memberserver_admin,
    role_memberserver_edu,
    role_school,
    role_school_admin,
    role_school_admin_group,
    role_school_class,
    role_school_class_share,
    role_single_master,
    role_student,
    role_workgroup,
    role_workgroup_share,
    role_school_domain_group,
    role_school_teacher_group,
    role_school_staff_group,
    role_school_student_group,
    role_ip_computer,
    role_linux_computer,
    role_mac_computer,
    role_ubuntu_computer,
    role_win_computer,
    role_teacher_computer,
    role_computer_room_backend_veyon,
)

context_type_school = "school"
context_type_exam = "exam"

all_context_types = (context_type_school, context_type_exam)


def create_ucsschool_role_string(
    role, context, context_type="school", school=""
):  # type: (str, str, str, str) -> str
    """
    This function takes a role, a context_type and a context to create a valid ucsschoolRole string.
    :param role: The role
    :param context: The context
    :param context_type: The context type
    :param school: Old variable name for context. DEPRECATED! TODO: Should be removed in 4.4v5
    :return: The valid ucsschoolRole string
    """
    if role not in all_roles:
        raise UnknownRole("Unknown role {!r}.".format(role))
    if school:
        context = school
    return "{}:{}:{}".format(role, context_type, context)


def get_role_info(ucsschool_role_string):
    """
    This function separates the individual elements of an ucsschool role string.
    Raises InvalidUcsschoolRoleString if the string provided is no valid role string.
    Raises UnknownRole if the role is unknown.
    Raises UnknownContextType if the context type is unknown.
    :param ucsschool_role_string: The role string to separate
    :return: (role, context_type, context)
    """
    try:
        role, context_type, context = ucsschool_role_string.split(":")
    except ValueError:
        raise InvalidUcsschoolRoleString(
            "Invalid UCS@school role string: {!r}.".format(ucsschool_role_string)
        )
    if role not in all_roles:
        raise UnknownRole(
            "The role string {!r} includes the unknown role {!r}.".format(ucsschool_role_string, role)
        )
    if context_type not in all_context_types:
        raise UnknownContextType(
            "The role string {!r} includes the unknown context type {!r}.".format(
                ucsschool_role_string, context_type
            )
        )
    return role, context_type, context
